'use client';

import { useEffect, useRef, useState } from 'react';

interface VideoPreviewProps {
  outputUrl: string | null;
  htmlOutputUrl: string | null;
  // When true, the MP4 is the placeholder dummy clip (real render engine
  // unavailable). Prefer the HTML preview and show a warning instead of
  // playing the "TV no-signal" sample video. Decided by the caller, which has
  // the RenderJob context; this component stays generic.
  isPlaceholder?: boolean;
  // 可选：与外部播放头（如编辑器时间轴）联动。传入 currentTime 时，外部拖动播放头
  // 会 seek 视频；视频播放/拖动时通过 onTimeUpdate 回写播放头。
  currentTime?: number;
  onTimeUpdate?: (t: number) => void;
}

// Injected into the generated HTML before rendering it in an <iframe>. The
// source HTML is authored for HyperFrames to sample frame-by-frame: scenes use
// a sceneFade animation that ends at opacity 0 with animation-fill-mode
// "forwards". Opened directly in a browser, the animation has long finished
// and every scene sits at opacity 0, so the preview looks black. We keep the
// animations running, force scenes visible, loop the whole timeline, and scale
// the fixed-size stage to fit.
const PREVIEW_PATCH =
  '<style>' +
  '.scene{opacity:1!important;animation-fill-mode:both!important}' +
  'html,body{width:100%;height:100%;margin:0;background:#0f0f1a}' +
  '#stage{transform-origin:top left}' +
  '</style>' +
  '<script>' +
  'function __fit(){var s=document.getElementById("stage");if(!s)return;' +
  'var sw=s.offsetWidth||1080,sh=s.offsetHeight||1920;' +
  'var cw=document.documentElement.clientWidth,ch=document.documentElement.clientHeight;' +
  'var k=Math.min(cw/sw,ch/sh);s.style.transform="scale("+k+")";}' +
  'function __replay(){document.getAnimations().forEach(function(a){try{a.cancel();a.play();}catch(e){}});}' +
  'function __startLoop(){__fit();__replay();var maxDur=0;document.querySelectorAll(".scene").forEach(function(el){var st=getComputedStyle(el).animationDuration||"0s";var d=parseFloat(st)||0;maxDur=Math.max(maxDur,d*1000);});var loopMs=Math.max(maxDur,2000)+300;setInterval(__replay,loopMs);}' +
  'if(document.readyState==="complete"){setTimeout(__startLoop,50);}else{window.addEventListener("load",function(){setTimeout(__startLoop,100);});}' +
  'window.addEventListener("resize",__fit);' +
  '</script></head>';

function patchHtml(html: string): string {
  if (/<\/head>/i.test(html)) {
    return html.replace(/<\/head>/i, PREVIEW_PATCH);
  }
  return PREVIEW_PATCH + html;
}

function HtmlPreview({ url }: { url: string }) {
  const [srcDoc, setSrcDoc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [replayKey, setReplayKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setSrcDoc(null);
    setFailed(false);
    fetch(url, { credentials: 'include' })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((html) => {
        if (!cancelled) setSrcDoc(patchHtml(html));
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [url, replayKey]);

  if (failed) {
    return (
      <div className="w-full flex-1 flex items-center justify-center text-content-tertiary text-xs">
        HTML 预览加载失败
      </div>
    );
  }

  if (!srcDoc) {
    return (
      <div className="w-full flex-1 flex items-center justify-center text-content-tertiary text-xs">
        加载 HTML 预览…
      </div>
    );
  }

  return (
    <div className="w-full flex-1 flex flex-col min-h-0">
      <div className="relative w-full flex-1 min-h-0 rounded-lg overflow-hidden bg-black">
        <iframe
          key={replayKey}
          srcDoc={srcDoc}
          className="absolute inset-0 w-full h-full border-0"
          title="HTML preview"
          sandbox="allow-scripts"
        />
        <button
          type="button"
          onClick={() => setReplayKey((k) => k + 1)}
          className="absolute bottom-3 right-3 px-3 py-1.5 text-xs rounded-md bg-black/70 backdrop-blur border border-white/20 text-white hover:bg-white/20 transition-colors"
          title="重新播放"
        >
          重新播放 ↻
        </button>
      </div>
      <p className="mt-2 text-xs text-content-tertiary text-center">
        HTML 预览已启用自动循环；如画面卡住可点击重新播放。
      </p>
    </div>
  );
}

export function VideoPreview({
  outputUrl,
  htmlOutputUrl,
  isPlaceholder = false,
  currentTime,
  onTimeUpdate,
}: VideoPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  // 外部播放头（编辑器时间轴）变化时，seek 视频到对应时间；用阈值避免与正常播放
  // 的 timeupdate 互相“打架”。
  useEffect(() => {
    const v = videoRef.current;
    if (!v || currentTime == null) return;
    if (Math.abs(v.currentTime - currentTime) > 0.25) {
      v.currentTime = Math.max(0, currentTime);
    }
  }, [currentTime]);
  // When the MP4 is just the placeholder (real render engine unavailable on
  // this platform), prefer the HTML preview so the user does not stare at the
  // "TV no-signal" dummy clip and think the render is still running.
  if (isPlaceholder && htmlOutputUrl) {
    return (
      <div className="w-full h-full flex flex-col">
        <div className="mb-2 px-3 py-2 rounded-md bg-warning/10 border border-warning/30 text-xs text-warning">
          真实渲染引擎在当前环境不可用，输出 MP4 为占位文件；以下为 HTML 动画预览。
        </div>
        <div className="text-sm text-content-secondary mb-2 px-1">HTML 预览</div>
        <HtmlPreview url={htmlOutputUrl} />
      </div>
    );
  }

  if (isPlaceholder) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-center px-6 bg-background-surface border border-border-subtle rounded-lg">
        <p className="text-sm font-medium text-warning">真实视频未生成</p>
        <p className="text-xs mt-2 text-content-tertiary max-w-xs">
          渲染引擎在当前环境不可用（Chromium 无法合成），仅生成了占位视频。请检查 renderer 的浏览器配置。
        </p>
      </div>
    );
  }

  if (outputUrl) {
    return (
      <div className="w-full h-full flex flex-col">
        <div className="text-sm text-content-secondary mb-2 px-1">成片预览</div>
        <video
          ref={videoRef}
          src={outputUrl}
          controls
          loop
          playsInline
          onTimeUpdate={(e) => onTimeUpdate?.(e.currentTarget.currentTime)}
          className="w-full rounded-lg bg-black"
          style={{ maxHeight: 'calc(100% - 28px)' }}
        />
        <a
          href={outputUrl}
          download
          className="mt-3 inline-flex items-center justify-center px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          下载 MP4
        </a>
      </div>
    );
  }

  if (htmlOutputUrl) {
    return (
      <div className="w-full h-full flex flex-col">
        <div className="text-sm text-content-secondary mb-2 px-1">HTML 预览</div>
        <HtmlPreview url={htmlOutputUrl} />
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center text-content-tertiary text-sm">
      暂无预览
    </div>
  );
}
