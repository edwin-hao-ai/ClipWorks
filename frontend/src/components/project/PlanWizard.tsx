'use client';

import { useState } from 'react';
import { clsx } from 'clsx';
import { Project } from '@/lib/types';
import { ScriptPanel } from './ScriptPanel';
import { AssetsPanel } from './AssetsPanel';
import { ScenesPanel } from './ScenesPanel';
import { EffectsPanel } from './EffectsPanel';
import { Button } from '@/components/ui/Button';

const STEPS = [
  { id: 'script', label: '脚本' },
  { id: 'assets', label: '素材' },
  { id: 'scenes', label: '场景' },
  { id: 'effects', label: '动效' },
] as const;

export interface PlanWizardProps {
  project: Project;
  onStateChange: (state: NonNullable<Project['agent_state']>) => void;
  onApprove: () => void;
  generating: boolean;
}

export function PlanWizard({ project, onStateChange, onApprove, generating }: PlanWizardProps) {
  const state = project.agent_state || { step: 'idle' };
  const [activeTab, setActiveTab] = useState<string>(
    STEPS.find((s) => s.id === state.step)?.id ?? 'script'
  );

  const currentStepIndex = STEPS.findIndex((s) => s.id === state.step);
  const activeIndex = STEPS.findIndex((s) => s.id === activeTab);

  const updateSection = <K extends keyof NonNullable<Project['agent_state']>>(
    key: K,
    value: NonNullable<Project['agent_state']>[K]
  ) => {
    onStateChange({ ...state, [key]: value });
  };

  const canGoNext = (() => {
    if (activeIndex < currentStepIndex) return true;
    if (activeIndex > currentStepIndex) return false;
    return !!state[activeTab as keyof typeof state];
  })();

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Step sidebar */}
      <nav aria-label="创作步骤" className="flex items-center gap-2">
        {STEPS.map((step, idx) => {
          const reached = idx <= currentStepIndex;
          const active = step.id === activeTab;
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => setActiveTab(step.id)}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                active
                  ? 'bg-brand-500/15 text-brand-400'
                  : reached
                  ? 'text-content-secondary hover:bg-background-hover'
                  : 'text-content-tertiary cursor-not-allowed'
              )}
              disabled={!reached}
            >
              <span
                className={clsx(
                  'flex items-center justify-center w-5 h-5 rounded-full text-xs',
                  active ? 'bg-brand-500 text-white' : 'bg-background-elevated'
                )}
              >
                {idx + 1}
              </span>
              {step.label}
            </button>
          );
        })}
      </nav>

      {generating && state.generating_step && (
        <div className="flex items-center gap-2 text-sm text-brand-400">
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          Agent 正在生成{STEPS.find((s) => s.id === state.generating_step)?.label}…
        </div>
      )}

      <div className="flex-1 min-h-0 overflow-y-auto bg-background-surface border border-border-subtle rounded-lg p-4">
        {activeTab === 'script' && (
          <ScriptPanel
            value={state.script}
            project={project}
            onChange={(script) => updateSection('script', script)}
          />
        )}
        {activeTab === 'assets' && (
          <AssetsPanel
            value={state.assets}
            onChange={(assets) => updateSection('assets', assets)}
          />
        )}
        {activeTab === 'scenes' && (
          <ScenesPanel
            value={state.scenes}
            onChange={(scenes) => updateSection('scenes', scenes)}
          />
        )}
        {activeTab === 'effects' && (
          <EffectsPanel
            value={state.effects}
            scenes={state.scenes}
            onChange={(effects) => updateSection('effects', effects)}
          />
        )}
      </div>

      <div className="flex items-center justify-between">
        <Button
          variant="secondary"
          onClick={() => setActiveTab(STEPS[Math.max(0, activeIndex - 1)].id)}
          disabled={activeIndex === 0}
        >
          上一步
        </Button>
        <div className="flex items-center gap-2">
          {activeIndex === STEPS.length - 1 ? (
            <Button onClick={onApprove} disabled={generating || currentStepIndex < activeIndex}>
              确认生成
            </Button>
          ) : (
            <Button
              onClick={() => setActiveTab(STEPS[activeIndex + 1].id)}
              disabled={!canGoNext}
            >
              下一步
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
