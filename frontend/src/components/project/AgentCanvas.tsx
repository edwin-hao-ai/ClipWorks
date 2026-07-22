'use client';

import { useEffect, useState } from 'react';
import { AgentState, Project, RenderJob, Scene } from '@/lib/types';
import { clsx } from 'clsx';
import { PreviewPlayer } from './PreviewPlayer';
import { StoryboardStrip } from './StoryboardStrip';
import { API_URL } from '@/lib/api';
import {
  Lightbulb,
  FileText,
  Images,
  Clapperboard,
  Sparkles,
  Film,
  Check,
  Loader2,
  Bot,
} from 'lucide-react';

const STEPS = [
  { id: 'understand', label: '理解需求', icon: Lightbulb, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
  { id: 'script', label: '编写脚本', icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
  { id: 'assets', label: '素材规划', icon: Images, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
  { id: 'scenes', label: '场景分镜', icon: Clapperboard, color: 'text-pink-400', bg: 'bg-pink-500/10', border: 'border-pink-500/20' },
  { id: 'effects', label: '动效设计', icon: Sparkles, color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20' },
  { id: 'render', label: '渲染成片', icon: Film, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
];

interface AgentCanvasProps {
  agentState?: AgentState;
  project?: Project;
  latestJob?: RenderJob | null;
  scenes?: Scene[];
  selectedSceneId?: string | null;
  onSelectScene?: (id: string) => void;
  format?: '16:9' | '9:16' | '1:1';
}

// Static previews (video / HTML iframe) must go through the same-origin
// Next.js rewrite. Pointing an <iframe> at http://localhost:8000 directly
// is cross-origin and can be blocked, leaving a black preview box.
function toSameOriginUrl(url?: string | null) {
  if (!url) return null;
  const prefix = `${API_URL}/api/static/`;
  if (url.startsWith(prefix)) return url.slice(API_URL.length);
  if (url.startsWith('/api/static/')) return url;
  return url;
}

export function AgentCanvas({
  agentState,
  project,
  latestJob,
  scenes = [],
  selectedSceneId,
  onSelectScene,
  format = '16:9',
}: AgentCanvasProps) {
  const [currentScene, setCurrentScene] = useState(0);

  useEffect(() => {
    if (selectedSceneId) {
      const idx = scenes.findIndex((s) => s.id === selectedSceneId);
      if (idx >= 0) setCurrentScene(idx);
    }
  }, [selectedSceneId, scenes]);

  // Project mode: preview + storyboard for the three-column workspace.
  if (project) {
    const outputUrl = toSameOriginUrl(latestJob?.output_url ?? project.latest_output_url);
    const htmlOutputUrl = toSameOriginUrl(latestJob?.html_output_url);
    const isPlaceholder =
      !!latestJob?.output_url && latestJob.output_url.includes('/sample.mp4');
    const hasOutput = outputUrl || htmlOutputUrl;

    return (
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-brand-400" />
            <h2 className="text-sm font-semibold text-content-secondary">预览 & 故事板</h2>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center bg-black/40 p-6">
          {hasOutput ? (
            <div className="w-full h-full max-w-3xl max-h-full bg-black rounded-lg overflow-hidden">
              <PreviewPlayer
                outputUrl={outputUrl}
                htmlOutputUrl={htmlOutputUrl}
                format={format}
                isPlaceholder={isPlaceholder}
              />
            </div>
          ) : (
            <div
              className="relative bg-black rounded-2xl overflow-hidden shadow-2xl"
              style={{ width: 270, height: 480 }}
            >
              <div className="absolute inset-0 flex flex-col items-center justify-center text-white text-center p-4">
                <div className="text-xl font-bold mb-2">镜 {currentScene + 1}</div>
                <div className="text-sm opacity-80">
                  {scenes[currentScene]?.text_content || scenes[currentScene]?.name || '预览区域'}
                </div>
              </div>
              <div className="absolute bottom-4 left-4 right-4 h-1 bg-white/20 rounded">
                <div
                  className="h-full bg-brand-400 rounded"
                  style={{ width: `${((currentScene + 1) / Math.max(1, scenes.length)) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>

        <StoryboardStrip
          scenes={scenes}
          currentIndex={currentScene}
          onSelect={(idx) => {
            setCurrentScene(idx);
            if (scenes[idx]?.id) {
              onSelectScene?.(scenes[idx].id);
            }
          }}
        />
      </div>
    );
  }

  // Dashboard mode: Vibe creation artifact timeline.
  const rawStep = (agentState?.step || 'understand') as string;
  // Legacy wizard projects default to step 'idle' before the first vibe stream.
  const step = rawStep === 'idle' ? 'understand' : rawStep;
  const payload = (agentState?.payload || {}) as Record<string, unknown>;
  const generatingStep = (agentState?.generating_step || step) as string;

  // Vibe sessions store artifacts under payload.*; legacy planning projects keep
  // them at the top level of agent_state.
  const legacy = agentState as Partial<AgentState> & Record<string, unknown> | undefined;
  const script = payload.script ?? legacy?.script;
  const assets = payload.assets ?? legacy?.assets;
  const scenesData = payload.scenes ?? legacy?.scenes;
  const effects = payload.effects ?? legacy?.effects;
  const understand = payload.understand ?? legacy?.understand;
  const render = payload.render ?? legacy?.render;

  const currentIndex = STEPS.findIndex((s) => s.id === step);

  const hasAnyPayload = understand || script || assets || scenesData || effects || render;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-brand-400" />
          <h2 className="text-sm font-semibold text-content-secondary">创作看板</h2>
        </div>
        <span className="text-xs text-content-tertiary">
          {currentIndex >= 0 ? `步骤 ${currentIndex + 1}/${STEPS.length}` : '准备中'}
        </span>
      </div>

      {/* Empty / welcome state */}
      {!hasAnyPayload && step === 'understand' && (
        <div className="bg-background-surface border border-border-subtle rounded-xl p-6 text-center">
          <div className="w-12 h-12 rounded-full bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-6 h-6 text-brand-400" />
          </div>
          <h3 className="text-base font-semibold text-content-primary mb-2">
            让 AI 导演帮你做视频
          </h3>
          <p className="text-sm text-content-secondary mb-4 max-w-sm mx-auto">
            描述你想做的视频主题、风格或目标，AI 会自动完成理解、脚本、素材、场景、动效，直到渲染成片。
          </p>
          <div className="flex flex-wrap justify-center gap-2 text-xs text-content-tertiary">
            <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">全自动工作流</span>
            <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">随时修改</span>
            <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">实时预览</span>
          </div>
        </div>
      )}

      {!hasAnyPayload && step !== 'understand' && (
        <div className="bg-background-surface border border-border-subtle rounded-xl p-6 text-center">
          <p className="text-sm text-content-secondary">等待输入…</p>
          <p className="text-xs text-content-tertiary mt-1">当前步骤：{step}</p>
        </div>
      )}

      {/* Step timeline */}
      <div className="flex-1 overflow-y-auto pr-1 -mr-1">
        <div className="relative pl-6 space-y-4">
          {/* Vertical line */}
          <div className="absolute left-[11px] top-2 bottom-2 w-px bg-border-subtle" />

          {STEPS.map((s, idx) => {
            const isCurrent = s.id === step || s.id === generatingStep;
            const isPast = idx < currentIndex;
            const isCompleted = isPast || (s.id === 'render' && step === 'done');
            const data = getStepData(s.id, {
              understand: understand as Record<string, unknown> | undefined,
              script: script as Record<string, unknown> | undefined,
              assets: assets as { needed?: unknown[] } | undefined,
              scenes: scenesData as { scenes?: unknown[] } | undefined,
              effects: effects as { effects?: unknown[] } | undefined,
              render: render as { job_id?: string } | undefined,
            });
            const isWorking = isCurrent && !isCompleted && step !== 'done';
            const Icon = s.icon;

            return (
              <div key={s.id} className="relative">
                {/* Dot / check */}
                <div
                  className={clsx(
                    'absolute -left-6 top-0.5 w-6 h-6 rounded-full border-2 flex items-center justify-center z-10 transition-colors',
                    isCompleted
                      ? 'bg-brand-500 border-brand-500 text-content-inverse'
                      : isCurrent
                      ? 'bg-background-surface border-brand-400 text-brand-400'
                      : 'bg-background-surface border-border-subtle text-content-tertiary'
                  )}
                >
                  {isCompleted ? (
                    <Check className="w-3.5 h-3.5" />
                  ) : isWorking ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Icon className="w-3 h-3" />
                  )}
                </div>

                {/* Card */}
                <div
                  className={clsx(
                    'rounded-xl border transition-all',
                    isCurrent
                      ? 'bg-background-surface border-brand-500/30 shadow-[0_0_24px_rgba(14,165,233,0.12)]'
                      : isCompleted
                      ? 'bg-background-surface/60 border-border-subtle'
                      : 'bg-background-surface/40 border-border-subtle/60 opacity-70'
                  )}
                >
                  <div className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={clsx('text-xs font-medium', s.color)}>{s.label}</span>
                      {isWorking && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
                          进行中
                        </span>
                      )}
                    </div>
                    {data ? (
                      <div className="text-sm text-content-secondary">{data}</div>
                    ) : (
                      <p className="text-xs text-content-tertiary">等待完成…</p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function getStepData(
  stepId: string,
  data: {
    understand?: Record<string, unknown>;
    script?: Record<string, unknown>;
    assets?: { needed?: unknown[] };
    scenes?: { scenes?: unknown[] };
    effects?: { effects?: unknown[] };
    render?: { job_id?: string };
  }
): React.ReactNode {
  switch (stepId) {
    case 'understand': {
      const u = data.understand;
      if (!u) return null;
      const summary = typeof u.summary === 'string' ? u.summary : '';
      const format = typeof u.format === 'string' ? u.format : '';
      const duration = typeof u.duration === 'number' ? `${u.duration} 秒` : '';
      const style = typeof u.style === 'string' ? u.style : '';
      const audience = typeof u.audience === 'string' ? u.audience : '';
      const meta = [format, duration, audience, style].filter(Boolean);
      return (
        <div className="space-y-2">
          {summary && <p className="font-medium text-content-primary">{summary}</p>}
          {meta.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {meta.map((m) => (
                <span
                  key={m}
                  className="px-2 py-0.5 rounded-full bg-background-elevated border border-border-subtle text-[10px] text-content-secondary"
                >
                  {m}
                </span>
              ))}
            </div>
          )}
        </div>
      );
    }
    case 'script': {
      const s = data.script;
      if (!s) return null;
      const title = typeof s.title === 'string' ? s.title : '';
      const hook = typeof s.hook === 'string' ? s.hook : '';
      const arc = typeof s.narrative_arc === 'string' ? s.narrative_arc : '';
      return (
        <div className="space-y-1">
          {title && <h4 className="font-medium text-content-primary">{title}</h4>}
          {hook && <p className="text-content-secondary">{hook}</p>}
          {arc && <p className="text-xs text-content-tertiary">{arc}</p>}
        </div>
      );
    }
    case 'assets': {
      const needed = data.assets?.needed;
      if (!Array.isArray(needed) || needed.length === 0) return null;
      return (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-content-primary">素材清单</p>
          <ul className="space-y-1">
            {needed.map((item, idx) => {
              const desc =
                typeof item === 'string'
                  ? item
                  : typeof item === 'object' && item !== null
                  ? (item as { description?: string }).description || String(item)
                  : String(item);
              return (
                <li key={idx} className="text-xs text-content-secondary flex items-start gap-1.5">
                  <span className="w-1 h-1 rounded-full bg-brand-400 mt-1.5 shrink-0" />
                  {desc}
                </li>
              );
            })}
          </ul>
        </div>
      );
    }
    case 'scenes': {
      const sceneList = data.scenes?.scenes;
      if (!Array.isArray(sceneList) || sceneList.length === 0) return null;
      return (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-content-primary">场景规划</p>
          <ul className="space-y-1">
            {sceneList.map((scene, idx) => {
              const text =
                typeof scene === 'object' && scene !== null
                  ? (scene as { description?: string; text?: string }).description ||
                    (scene as { description?: string; text?: string }).text ||
                    String(scene)
                  : String(scene);
              return (
                <li key={idx} className="text-xs text-content-secondary flex items-start gap-1.5">
                  <span className="w-4 h-4 rounded bg-brand-500/10 text-[9px] flex items-center justify-center text-brand-400 shrink-0">
                    {idx + 1}
                  </span>
                  {text}
                </li>
              );
            })}
          </ul>
        </div>
      );
    }
    case 'effects': {
      const effectsList = data.effects?.effects;
      if (!Array.isArray(effectsList)) return null;
      return (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-content-primary">动效设计</p>
          {effectsList.length === 0 ? (
            <p className="text-xs text-content-tertiary">使用默认动效</p>
          ) : (
            <ul className="space-y-1">
              {effectsList.map((fx, idx) => {
                const style =
                  typeof fx === 'object' && fx !== null
                    ? (fx as { visual_style?: string }).visual_style || String(fx)
                    : String(fx);
                const keywords =
                  typeof fx === 'object' && fx !== null
                    ? (fx as { animation_keywords?: string[] }).animation_keywords
                    : undefined;
                return (
                  <li key={idx} className="text-xs text-content-secondary flex items-start gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-cyan-400 mt-1.5 shrink-0" />
                    {style}
                    {keywords && keywords.length > 0 && (
                      <span className="text-content-tertiary ml-1">({keywords.join(', ')})</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      );
    }
    case 'render': {
      const jobId = data.render?.job_id;
      if (!jobId) return null;
      return (
        <div className="space-y-1">
          <p className="text-xs font-medium text-content-primary">渲染</p>
          <p className="text-xs text-content-secondary">渲染任务已创建：{jobId}</p>
        </div>
      );
    }
    default:
      return null;
  }
}
