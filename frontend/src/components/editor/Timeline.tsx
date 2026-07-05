'use client';

import { useState } from 'react';
import { Composition } from '@/lib/types';
import { Playhead } from './Playhead';
import { Track } from './Track';
import { ZoomIn, ZoomOut, Clock } from 'lucide-react';

interface Props {
  composition: Composition;
}

export function Timeline({ composition }: Props) {
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedClipId, setSelectedClipId] = useState<string>();

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
            <button className="p-1.5 rounded-md text-content-tertiary hover:bg-background-hover hover:text-content-primary transition-colors">
              <ZoomOut className="w-4 h-4" />
            </button>
            <button className="p-1.5 rounded-md text-content-tertiary hover:bg-background-hover hover:text-content-primary transition-colors">
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      <div className="overflow-x-auto">
        <Playhead
          currentTime={currentTime}
          duration={composition.duration}
          onSeek={setCurrentTime}
        />
        <div className="min-w-[400px]">
          {composition.tracks.map((track) => (
            <Track
              key={track.id}
              track={track}
              selectedClipId={selectedClipId}
              onSelectClip={setSelectedClipId}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
