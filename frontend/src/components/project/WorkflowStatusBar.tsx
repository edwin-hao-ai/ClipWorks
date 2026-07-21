'use client';

import { clsx } from 'clsx';

const STEPS = [
  { id: 'understand', label: '理解' },
  { id: 'script', label: '脚本' },
  { id: 'assets', label: '素材' },
  { id: 'scenes', label: '场景' },
  { id: 'effects', label: '动效' },
  { id: 'render', label: '渲染' },
];

export function WorkflowStatusBar({ currentStep }: { currentStep?: string }) {
  const currentIndex = STEPS.findIndex((s) => s.id === currentStep);
  return (
    <nav aria-label="创作进度" className="flex items-center gap-1 text-xs">
      {STEPS.map((step, idx) => {
        const reached = idx <= currentIndex;
        const active = step.id === currentStep;
        return (
          <div key={step.id} className="flex items-center gap-1">
            <span
              aria-current={active ? 'step' : undefined}
              className={clsx(
                'px-2 py-1 rounded-full transition-colors',
                active
                  ? 'bg-brand-500/20 text-brand-400 font-medium'
                  : reached
                  ? 'text-content-secondary'
                  : 'text-content-tertiary'
              )}
            >
              {step.label}
            </span>
            {idx < STEPS.length - 1 && (
              <span className={clsx('w-4 h-px', reached ? 'bg-brand-500/40' : 'bg-border-subtle')} />
            )}
          </div>
        );
      })}
    </nav>
  );
}
