'use client';

import { AgentAssetPlan } from '@/lib/types';

export interface AssetsPanelProps {
  value?: AgentAssetPlan | null;
  onChange: (assets: AgentAssetPlan) => void;
}

export function AssetsPanel({ value }: AssetsPanelProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-content-primary">素材</h2>
      <p className="text-sm text-content-secondary">
        共 {value?.needed.length ?? 0} 项素材需求（后续任务实现编辑）。
      </p>
    </div>
  );
}
