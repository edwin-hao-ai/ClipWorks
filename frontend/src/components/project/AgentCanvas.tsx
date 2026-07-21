'use client';

import { AgentState } from '@/lib/types';

export function AgentCanvas({ agentState }: { agentState?: AgentState }) {
  const step = agentState?.step || 'understand';
  const payload = agentState?.payload || {};

  if (step === 'understand') {
    const u = payload.understand;
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">需求理解</h3>
        <p className="text-content-primary text-lg mb-4">{u?.summary || '等待输入…'}</p>
        <div className="flex flex-wrap gap-2 text-xs">
          {u?.format && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.format}</span>}
          {u?.duration && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.duration} 秒</span>}
          {u?.audience && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.audience}</span>}
          {u?.style && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.style}</span>}
        </div>
      </div>
    );
  }

  if (step === 'script') {
    const s = payload.script;
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">脚本</h3>
        <h4 className="text-xl font-bold text-content-primary mb-2">{s?.title || '未命名'}</h4>
        <p className="text-brand-400 mb-4">{s?.hook || ''}</p>
        <p className="text-content-secondary text-sm whitespace-pre-line">{s?.narrative_arc || ''}</p>
      </div>
    );
  }

  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-5 text-content-tertiary">
      当前步骤：{step}
    </div>
  );
}
