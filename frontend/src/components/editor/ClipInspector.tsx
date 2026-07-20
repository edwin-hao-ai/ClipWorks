'use client';

import { Clip, Track } from '@/lib/types';
import { Trash2 } from 'lucide-react';

interface Props {
  clip: Clip;
  trackType: Track['type'];
  onChange: (patch: Partial<Clip>) => void;
  onDelete: () => void;
}

const typeLabels: Record<Track['type'], string> = {
  video: '视频',
  image: '图片',
  audio: '音频',
  text: '文本',
  overlay: '叠层',
};

function parseSeconds(value: string, fallback: number): number {
  const n = parseFloat(value);
  return Number.isFinite(n) ? n : fallback;
}

export function ClipInspector({ clip, trackType, onChange, onDelete }: Props) {
  const showText = trackType === 'text' || trackType === 'overlay';

  return (
    <div className="bg-background-surface border border-border-subtle rounded-md px-4 py-3 flex flex-wrap items-end gap-4">
      <div className="flex flex-col gap-1">
        <span className="text-[11px] text-content-tertiary">片段属性</span>
        <span className="text-sm font-medium text-content-primary">{typeLabels[trackType]}片段</span>
      </div>

      {showText && (
        <label className="flex flex-col gap-1 min-w-[200px] flex-1">
          <span className="text-[11px] text-content-tertiary">文本内容</span>
          <input
            type="text"
            value={clip.text_content || ''}
            onChange={(e) => onChange({ text_content: e.target.value })}
            placeholder="输入文本…"
            className="bg-background-base border border-border-subtle rounded-md px-2 py-1.5 text-sm text-content-primary outline-none focus:border-brand-500"
          />
        </label>
      )}

      <label className="flex flex-col gap-1 w-28">
        <span className="text-[11px] text-content-tertiary">开始 (秒)</span>
        <input
          type="number"
          min={0}
          step={0.1}
          value={clip.start_time}
          onChange={(e) => onChange({ start_time: Math.max(0, parseSeconds(e.target.value, 0)) })}
          className="bg-background-base border border-border-subtle rounded-md px-2 py-1.5 text-sm text-content-primary font-mono outline-none focus:border-brand-500"
        />
      </label>

      <label className="flex flex-col gap-1 w-28">
        <span className="text-[11px] text-content-tertiary">时长 (秒)</span>
        <input
          type="number"
          min={0.1}
          step={0.1}
          value={clip.duration}
          onChange={(e) => onChange({ duration: Math.max(0.1, parseSeconds(e.target.value, 0.1)) })}
          className="bg-background-base border border-border-subtle rounded-md px-2 py-1.5 text-sm text-content-primary font-mono outline-none focus:border-brand-500"
        />
      </label>

      <button
        type="button"
        onClick={onDelete}
        className="ml-auto flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-error hover:bg-error/10 transition-colors"
      >
        <Trash2 className="w-3.5 h-3.5" /> 删除片段
      </button>
    </div>
  );
}
