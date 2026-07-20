'use client';

import { useState } from 'react';
import { Clip, Composition } from '@/lib/types';
import { Playhead } from './Playhead';
import { Track } from './Track';
import { ZoomIn, ZoomOut, Clock } from 'lucide-react';

interface Props {
  composition: Composition;
  selectedClipId?: string;
  onSelectClip: (clipId?: string) => void;
  onAddClip: (trackId: string) => void;
  onChangeClip?: (clipId: string, patch: Partial<Clip>) => void;
  currentTime: number;
  onSeek: (t: number) => void;
}

const ZOOM_LEVELS = [12, 24, 48];

export function Timeline({ composition, selectedClipId, onSelectClip, onAddClip, onChangeClip, currentTime, onSeek }: Props) {
  const [zoomIndex, setZoomIndex] = useState(1);
  const pixelsPerSecond = ZOOM_LEVELS[zoomIndex];

  return (
    <div className="bg-background-surface border border-border-subtle rounded-md overflow-hidden flex flex-col">
      <div className="px-4 py-3 border-b border-border-subtle flex justify-between items-center">
        <h3 className="font-semibold text-content-primary">时间线</h3>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-xs text-content-tertiary bg-background-elevated rounded-md px-2 py-1">
            <Clock className="w-3.5 h-3.5" />
            <span className="font-mono">{currentTime.toFixed(1)}s / {composition.duration}s</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              title="缩小"
              disabled={zoomIndex === 0}
              onClick={() => setZoomIndex((i) => Math.max(0, i - 1))}
              className="p-1.5 rounded-md text-content-tertiary hover:bg-background-hover hover:text-content-primary transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-[11px] font-mono text-content-tertiary w-12 text-center select-none">
              {pixelsPerSecond}px/s
            </span>
            <button
              type="button"
              title="放大"
              disabled={zoomIndex === ZOOM_LEVELS.length - 1}
              onClick={() => setZoomIndex((i) => Math.min(ZOOM_LEVELS.length - 1, i + 1))}
              className="p-1.5 rounded-md text-content-tertiary hover:bg-background-hover hover:text-content-primary transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      <div className="overflow-x-auto">
        <Playhead
          currentTime={currentTime}
          duration={composition.duration}
          pixelsPerSecond={pixelsPerSecond}
          onSeek={onSeek}
        />
        <div className="min-w-[400px]">
          {composition.tracks.map((track) => (
            <Track
              key={track.id}
              track={track}
              pixelsPerSecond={pixelsPerSecond}
              selectedClipId={selectedClipId}
              onSelectClip={(clipId) => onSelectClip(clipId)}
              onAddClip={onAddClip}
              onChangeClip={onChangeClip}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
