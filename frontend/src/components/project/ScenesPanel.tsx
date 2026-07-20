'use client';

import { AgentScenePlan } from '@/lib/types';

export interface ScenesPanelProps {
  value?: AgentScenePlan | null;
  onChange: (scenes: AgentScenePlan) => void;
}

export function ScenesPanel({ value }: ScenesPanelProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-content-primary">场景</h2>
      <p className="text-sm text-content-secondary">
        共 {value?.scenes.length ?? 0} 个场景（后续任务实现编辑）。
      </p>
    </div>
  );
}
