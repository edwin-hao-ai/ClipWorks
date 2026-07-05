'use client';

import { SceneCard } from './SceneCard';
import { Scene } from '@/lib/types';
import { Film } from 'lucide-react';

interface SceneCardsProps {
  scenes: Scene[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
}

export function SceneCards({ scenes, selectedId, onSelect }: SceneCardsProps) {
  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-4 flex flex-col h-[280px]">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <Film className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-semibold">场景卡片</span>
        </div>
        <span className="text-xs text-content-tertiary">点卡片修改</span>
      </div>
      {scenes.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-content-tertiary text-sm">
          <Film className="w-8 h-8 mb-2 opacity-50" />
          <p>生成后场景会出现在这里</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {scenes.map((scene) => (
            <SceneCard
              key={scene.id}
              scene={scene}
              isSelected={scene.id === selectedId}
              onClick={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
