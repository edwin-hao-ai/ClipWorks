'use client';

import { AgentPlan } from '@/lib/types';

interface PlanApprovalProps {
  plan: AgentPlan;
  onApprove: () => void;
  onReject: () => void;
  loading?: boolean;
}

export function PlanApproval({ plan, onApprove, onReject, loading }: PlanApprovalProps) {
  return (
    <div className="bg-success/10 border border-success/30 rounded-xl p-4">
      <div className="flex justify-between items-center mb-3">
        <span className="font-semibold text-success">方案已就绪 · 待确认</span>
        <span className="text-xs text-content-tertiary">{plan.format} · {plan.duration}s · {plan.scenes.length} 镜</span>
      </div>
      <div className="space-y-2 mb-4">
        {plan.scenes.map((s, idx) => (
          <div key={idx} className="bg-background-base rounded p-2 text-sm border border-border-subtle">
            <span className="font-medium">镜 {idx + 1}</span>
            <span className="text-content-tertiary ml-2">({s.start}s–{s.start + s.duration}s)</span>
            <p className="text-content-secondary mt-1">{s.description}</p>
            {s.text && <p className="text-brand-400 mt-1">“{s.text}”</p>}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={onApprove} disabled={loading} className="flex-1 px-3 py-2 rounded bg-brand-600 text-white text-sm">确认生成</button>
        <button onClick={onReject} disabled={loading} className="flex-1 px-3 py-2 rounded bg-background-elevated text-content-secondary text-sm">再改改</button>
      </div>
    </div>
  );
}
