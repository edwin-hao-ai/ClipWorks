'use client';

import { Scene } from '@/lib/types';
import { SceneCard } from './SceneCard';

interface SceneCardsProps {
  scenes: Scene[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}

export function SceneCards({ scenes, selectedId, onSelect }: SceneCardsProps) {
  if (scenes.length === 0) {
    return (
      <div className="bg-background-surface border border-border-subtle rounded-md p-5">
        <h3 className="font-semibold text-content-primary mb-2">场景</h3>
        <p className="text-sm text-content-secondary">暂无场景</p>
      </div>
    );
  }

  return (
    <div className="bg-background-surface border border-border-subtle rounded-md p-5 flex flex-col gap-3 min-h-0 overflow-hidden">
      <h3 className="font-semibold text-content-primary shrink-0">场景</h3>
      <div className="flex flex-col gap-2 overflow-y-auto pr-1">
        {scenes.map((scene) => (
          <SceneCard
            key={scene.id}
            scene={scene}
            isSelected={scene.id === selectedId}
            onClick={onSelect}
          />
        ))}
      </div>
    </div>
  );
}
