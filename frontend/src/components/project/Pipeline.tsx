'use client';

import { clsx } from 'clsx';
import { Check, Loader2, Circle } from 'lucide-react';
import { PipelineStep } from '@/lib/types';

interface PipelineProps {
  steps: PipelineStep[];
  currentStepIndex: number;
  currentDescription?: string;
}

export function Pipeline({ steps, currentStepIndex, currentDescription }: PipelineProps) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between relative">
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-background-elevated -translate-y-1/2 -z-10" />
        <div
          className="absolute top-1/2 left-0 h-0.5 bg-gradient-to-r from-success to-brand-500 -translate-y-1/2 -z-10 transition-all duration-500"
          style={{
            width: `${Math.max(0, Math.min(100, (currentStepIndex / (steps.length - 1)) * 100))}%`,
          }}
        />
        {steps.map((step, idx) => {
          const done = idx < currentStepIndex;
          const active = idx === currentStepIndex;
          const Icon = done ? Check : active ? Loader2 : Circle;

          return (
            <div key={step.id} className="flex flex-col items-center gap-2 w-24">
              <div
                className={clsx(
                  'w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all duration-300',
                  done && 'border-success bg-background-surface text-success',
                  active && 'border-brand-500 bg-brand-900/30 text-brand-400 shadow-[0_0_16px_rgba(14,165,233,0.25)]',
                  !done && !active && 'border-border-default bg-background-surface text-text-tertiary'
                )}
              >
                <Icon className={clsx('w-4 h-4', active && 'animate-spin')} />
              </div>
              <span
                className={clsx(
                  'text-xs text-center',
                  done && 'text-success',
                  active && 'text-brand-400',
                  !done && !active && 'text-text-tertiary'
                )}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
      {currentDescription && (
        <div className="mt-4 bg-background-elevated border border-border-subtle rounded-lg p-3 flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
          <span className="text-sm text-text-secondary">{currentDescription}</span>
        </div>
      )}
    </div>
  );
}
