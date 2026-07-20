'use client';

import { AgentEffectPlan, AgentScenePlan } from '@/lib/types';

export interface EffectsPanelProps {
  value?: AgentEffectPlan | null;
  scenes?: AgentScenePlan | null;
  onChange: (effects: AgentEffectPlan) => void;
}

export function EffectsPanel({ value, scenes }: EffectsPanelProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-content-primary">动效</h2>
      <p className="text-sm text-content-secondary">
        共 {value?.effects.length ?? 0} 个动效，基于 {scenes?.scenes.length ?? 0} 个场景（后续任务实现编辑）。
      </p>
    </div>
  );
}
