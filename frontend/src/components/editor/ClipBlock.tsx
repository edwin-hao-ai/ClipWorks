'use client';

import { useRef, useState } from 'react';
import { Clip } from '@/lib/types';

interface Props {
  clip: Clip;
  pixelsPerSecond: number;
  onSelect: (clip: Clip) => void;
  onChange?: (patch: Partial<Clip>) => void;
  selected: boolean;
  trackType?: string;
}

const MIN_DURATION = 0.1;
const CLICK_THRESHOLD = 3;

// 片段颜色跟随轨道类型（设计系统 §2.4 时间线五色编码），
// 让用户一眼区分画面/字幕/角标/音频，而不是所有片段都是品牌蓝。
const clipColors: Record<string, string> = {
  video: 'bg-timeline-video/90 hover:bg-timeline-video',
  image: 'bg-timeline-image/90 hover:bg-timeline-image',
  audio: 'bg-timeline-audio/90 hover:bg-timeline-audio',
  text: 'bg-timeline-text/90 hover:bg-timeline-text',
  overlay: 'bg-timeline-overlay/90 hover:bg-timeline-overlay',
};

const round1 = (v: number) => Math.round(v * 10) / 10;

type DragMode = 'move' | 'trim-l' | 'trim-r';

interface DragState {
  mode: DragMode;
  startX: number;
  start: number;
  dur: number;
  moved: number;
  lastDx: number;
}

// 拖拽期间只在本地更新视觉（left/width），松手时一次性提交 onChange。
// 这样一次拖拽只产生一个历史点（撤销干净），也给外层防重叠一个唯一的提交点。
export function ClipBlock({ clip, pixelsPerSecond, onSelect, onChange, selected, trackType }: Props) {
  const [preview, setPreview] = useState<{ start: number; dur: number } | null>(null);
  const drag = useRef<DragState | null>(null);

  const colorClass = clipColors[trackType ?? 'video'] ?? clipColors.video;

  const start = preview ? preview.start : clip.start_time;
  const dur = preview ? preview.dur : clip.duration;
  const left = start * pixelsPerSecond;
  const width = Math.max(dur * pixelsPerSecond, 6);

  const compute = (d: DragState, dx: number): { start: number; dur: number } => {
    const dSec = dx / pixelsPerSecond;
    if (d.mode === 'move') {
      return { start: round1(Math.max(0, d.start + dSec)), dur: d.dur };
    }
    if (d.mode === 'trim-r') {
      return { start: d.start, dur: round1(Math.max(MIN_DURATION, d.dur + dSec)) };
    }
    // 左边缘：保持右边界不变，同时调整起点与时长
    const maxStart = d.start + d.dur - MIN_DURATION;
    const newStart = round1(Math.max(0, Math.min(maxStart, d.start + dSec)));
    return { start: newStart, dur: round1(d.dur - (newStart - d.start)) };
  };

  const begin = (mode: DragMode, e: React.PointerEvent) => {
    if (!onChange) return;
    e.preventDefault();
    e.stopPropagation();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    drag.current = { mode, startX: e.clientX, start: clip.start_time, dur: clip.duration, moved: 0, lastDx: 0 };
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d || !onChange) return;
    const dx = e.clientX - d.startX;
    d.lastDx = dx;
    d.moved = Math.max(d.moved, Math.abs(dx));
    const p = compute(d, dx);
    setPreview({ start: p.start, dur: p.dur });
  };

  const finish = (e: React.PointerEvent, commit: boolean) => {
    const d = drag.current;
    drag.current = null;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    setPreview(null);
    if (!d) return;
    // 没有真正拖动时，按点击处理：选中片段
    if (d.moved < CLICK_THRESHOLD) {
      onSelect(clip);
      return;
    }
    if (commit && onChange) {
      const p = compute(d, d.lastDx);
      const patch: Partial<Clip> = {};
      if (p.start !== clip.start_time) patch.start_time = p.start;
      if (p.dur !== clip.duration) patch.duration = p.dur;
      if (Object.keys(patch).length > 0) onChange(patch);
    }
  };

  return (
    <div
      className={`absolute top-1.5 h-9 rounded text-xs flex items-center px-2 overflow-visible select-none transition-shadow touch-none text-white ${colorClass} ${
        selected ? 'ring-2 ring-white/80 shadow-md' : ''
      } ${onChange ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer'}`}
      style={{ left, width }}
      onPointerDown={(e) => begin('move', e)}
      onPointerMove={onPointerMove}
      onPointerUp={(e) => finish(e, true)}
      onPointerCancel={(e) => finish(e, false)}
    >
      {onChange && (
        <div
          className="absolute left-0 top-0 h-full w-[7px] cursor-ew-resize rounded-l hover:bg-white/30"
          onPointerDown={(e) => begin('trim-l', e)}
        />
      )}
      <span className="truncate font-medium pointer-events-none">{clip.text_content || '片段'}</span>
      {onChange && (
        <div
          className="absolute right-0 top-0 h-full w-[7px] cursor-ew-resize rounded-r hover:bg-white/30"
          onPointerDown={(e) => begin('trim-r', e)}
        />
      )}
    </div>
  );
}
