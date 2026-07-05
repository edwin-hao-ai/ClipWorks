'use client';

import { useRef, useState } from 'react';
import { Play, Pause, Film } from 'lucide-react';

interface PreviewPlayerProps {
  videoUrl?: string;
  format?: '16:9' | '9:16' | '1:1';
}

const FORMAT_RATIO: Record<string, string> = {
  '16:9': 'aspect-video',
  '9:16': 'aspect-[9/16]',
  '1:1': 'aspect-square',
};

export function PreviewPlayer({ videoUrl, format = '16:9' }: PreviewPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [playing, setPlaying] = useState(false);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (playing) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
    setPlaying(!playing);
  };

  if (!videoUrl) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-white bg-black">
        <div className="relative mb-4">
          <div className="absolute inset-0 bg-brand-500/20 blur-xl rounded-full" />
          <div className="relative w-16 h-16 rounded-full bg-background-elevated/80 border border-border-default flex items-center justify-center">
            <Film className="w-7 h-7 text-content-tertiary" />
          </div>
        </div>
        <p className="text-content-secondary font-medium">视频将在这里预览</p>
        <p className="text-content-tertiary text-sm mt-1">点击「开始生成」后，成片会出现在此处</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-black relative">
      <div className={`relative ${FORMAT_RATIO[format] || 'aspect-video'} max-h-full max-w-full`}>
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain rounded-lg"
          controls={false}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          poster="/api/static/placeholder.png"
        />
        <button
          onClick={togglePlay}
          className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 hover:opacity-100 transition-opacity"
          aria-label={playing ? '暂停' : '播放'}
        >
          <div className="w-14 h-14 rounded-full bg-brand-600/90 flex items-center justify-center backdrop-blur">
            {playing ? <Pause className="w-6 h-6 text-white" /> : <Play className="w-6 h-6 text-white ml-1" />}
          </div>
        </button>
      </div>
    </div>
  );
}
