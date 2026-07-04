'use client';

import { Clip } from '@/lib/types';

interface Props {
  clip: Clip;
  onUpdate: (clip: Clip) => void;
  onSelect: (clip: Clip) => void;
  selected: boolean;
}

export const PIXELS_PER_SECOND = 24;

export function ClipBlock({ clip, onUpdate, onSelect, selected }: Props) {
  const left = clip.start_time * PIXELS_PER_SECOND;
  const width = Math.max(clip.duration * PIXELS_PER_SECOND, 6);

  return (
    <div
      className={`absolute top-1.5 h-9 rounded text-xs flex items-center px-2 overflow-hidden cursor-pointer select-none transition-shadow ${
        selected
          ? 'ring-2 ring-brand-400 bg-brand-900/60 text-brand-100 shadow-md'
          : 'bg-brand-600/80 text-content-inverse hover:bg-brand-500'
      }`}
      style={{ left, width }}
      onClick={() => onSelect(clip)}
    >
      <span className="truncate font-medium">{clip.text_content || '片段'}</span>
    </div>
  );
}
