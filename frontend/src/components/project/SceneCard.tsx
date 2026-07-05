'use client';

import { clsx } from 'clsx';
import { Pencil } from 'lucide-react';
import { Scene } from '@/lib/types';

interface SceneCardProps {
  scene: Scene;
  isSelected?: boolean;
  onClick?: (id: string) => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function SceneCard({ scene, isSelected = false, onClick }: SceneCardProps) {
  const start = formatTime(scene.start_time);
  const end = formatTime(scene.start_time + scene.duration);

  return (
    <div
      tabIndex={0}
      onClick={() => onClick?.(scene.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.(scene.id);
        }
      }}
      className={clsx(
        'group flex items-center gap-3 p-2 rounded-lg border cursor-pointer transition-all duration-200',
        isSelected
          ? 'bg-brand-900/20 border-brand-500/60 shadow-[0_0_16px_rgba(14,165,233,0.15)]'
          : 'bg-background-elevated border-border-subtle hover:border-border-default hover:-translate-y-0.5'
      )}
    >
      <div
        className={clsx(
          'w-20 h-12 rounded-md shrink-0 flex items-center justify-center text-xs font-medium text-white/90',
          scene.index % 4 === 0 && 'bg-gradient-to-br from-blue-600/70 to-purple-600/70',
          scene.index % 4 === 1 && 'bg-gradient-to-br from-pink-600/70 to-orange-600/70',
          scene.index % 4 === 2 && 'bg-gradient-to-br from-emerald-600/70 to-teal-600/70',
          scene.index % 4 === 3 && 'bg-gradient-to-br from-amber-600/70 to-red-600/70'
        )}
      >
        {scene.thumbnail ? (
          <img src={scene.thumbnail} alt={scene.name} className="w-full h-full object-cover rounded-md" />
        ) : (
          `场景 ${scene.index + 1}`
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-content-primary truncate">{scene.name}</div>
        <div className="text-xs text-text-secondary mt-0.5">
          {start} - {end}
        </div>
        {scene.text_content && (
          <div className="text-xs text-text-tertiary truncate mt-0.5">{scene.text_content}</div>
        )}
      </div>
      <button
        className={clsx(
          'p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity',
          isSelected ? 'text-brand-400 hover:bg-brand-900/40' : 'text-text-tertiary hover:text-content-primary hover:bg-background-hover'
        )}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.(scene.id);
        }}
        aria-label="编辑场景"
      >
        <Pencil className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
