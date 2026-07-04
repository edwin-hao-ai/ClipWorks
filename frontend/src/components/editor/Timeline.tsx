'use client';

import { useState } from 'react';
import { Composition, Clip } from '@/lib/types';
import { Playhead } from './Playhead';
import { Track } from './Track';

interface Props {
  composition: Composition;
}

export function Timeline({ composition }: Props) {
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedClipId, setSelectedClipId] = useState<string>();

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 flex justify-between items-center">
        <h3 className="font-semibold text-slate-900">时间线</h3>
        <span className="text-xs text-slate-500">{currentTime.toFixed(1)}s / {composition.duration}s</span>
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
              onUpdateClip={(clip: Clip) => console.log('update clip', clip)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
