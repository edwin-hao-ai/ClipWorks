'use client';

import { clsx } from 'clsx';
import { Check, Loader2 } from 'lucide-react';

const STEPS = [
  { id: 'understand', label: '理解' },
  { id: 'script', label: '脚本' },
  { id: 'assets', label: '素材' },
  { id: 'scenes', label: '场景' },
  { id: 'effects', label: '动效' },
  { id: 'render', label: '渲染' },
];

export function WorkflowStatusBar({ currentStep }: { currentStep?: string }) {
  const normalizedStep = currentStep === 'idle' ? 'understand' : currentStep;
  const currentIndex = STEPS.findIndex((s) => s.id === normalizedStep);

  return (
    <nav aria-label="创作进度" className="flex items-center gap-1 text-xs">
      {STEPS.map((step, idx) => {
        const reached = idx <= currentIndex;
        const active = step.id === currentStep;
        const completed = reached && !active;

        return (
          <div key={step.id} className="flex items-center">
            <div
              className={clsx(
                'flex items-center gap-1.5 px-2 py-1 rounded-full transition-colors',
                active
                  ? 'bg-brand-500/15 text-brand-400 font-medium ring-1 ring-brand-500/30'
                  : completed
                  ? 'text-content-secondary'
                  : 'text-content-tertiary'
              )}
            >
              <span
                className={clsx(
                  'w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-semibold',
                  active
                    ? 'bg-brand-500 text-content-inverse'
                    : completed
                    ? 'bg-brand-500/20 text-brand-400'
                    : 'bg-background-elevated border border-border-subtle'
                )}
              >
                {completed ? (
                  <Check className="w-3 h-3" />
                ) : active ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  idx + 1
                )}
              </span>
              <span aria-current={active ? 'step' : undefined}>{step.label}</span>
            </div>
            {idx < STEPS.length - 1 && (
              <span
                className={clsx(
                  'w-4 h-px mx-1',
                  completed ? 'bg-brand-500/40' : 'bg-border-subtle'
                )}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
