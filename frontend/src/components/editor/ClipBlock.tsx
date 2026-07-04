'use client';

import { useState } from 'react';
import { Clip } from '@/lib/types';

interface Props {
  clip: Clip;
  onUpdate: (clip: Clip) => void;
  onSelect: (clip: Clip) => void;
  selected: boolean;
}

const PIXELS_PER_SECOND = 20;

export function ClipBlock({ clip, onUpdate, onSelect, selected }: Props) {
  const [resizing, setResizing] = useState(false);
  const left = clip.start_time * PIXELS_PER_SECOND;
  const width = Math.max(clip.duration * PIXELS_PER_SECOND, 4);

  return (
    <div
      className={`absolute top-1 h-10 rounded-md text-xs flex items-center px-2 overflow-hidden cursor-pointer select-none ${
        selected ? 'ring-2 ring-brand-500 bg-brand-100 text-brand-900' : 'bg-blue-100 text-blue-900'
      }`}
      style={{ left, width }}
      onClick={() => onSelect(clip)}
    >
      {clip.text_content || '片段'}
      <div
        className="absolute right-0 top-0 bottom-0 w-2 cursor-e-resize"
        onMouseDown={() => setResizing(true)}
      />
    </div>
  );
}
