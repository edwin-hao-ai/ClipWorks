'use client';

import { Scene } from '@/lib/types';

interface StoryboardStripProps {
  scenes: Scene[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export function StoryboardStrip({ scenes, currentIndex, onSelect }: StoryboardStripProps) {
  return (
    <div className="h-36 bg-background-surface border-t border-border-subtle p-3 overflow-x-auto">
      <div className="flex gap-3 min-w-max">
        {scenes.map((s, idx) => (
          <button
            key={s.id || idx}
            onClick={() => onSelect(idx)}
            className={`w-28 h-24 rounded-lg border flex flex-col justify-center items-center p-2 text-xs transition-colors ${
              idx === currentIndex
                ? 'border-brand-500 bg-brand-900/20 text-content-primary'
                : 'border-border-subtle bg-background-elevated text-content-secondary'
            }`}
          >
            <span className="font-medium">镜 {idx + 1}</span>
            <span className="text-content-tertiary mt-1">{s.start_time}s–{s.start_time + s.duration}s</span>
            <span className="truncate w-full text-center mt-1">{s.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
