import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PlanWizard } from '@/components/project/PlanWizard';
import { Project } from '@/lib/types';

const baseProject: Project = {
  id: '1',
  title: 'P',
  source_type: 'url',
  status: 'planning',
  target_format: '16:9',
  target_duration: 30,
  created_at: '',
  updated_at: '',
  agent_state: {
    step: 'script',
    script: {
      title: 'T',
      hook: 'H',
      roles: [],
      narrative_arc: 'A',
      cta: 'C',
      duration: 30,
      format: '16:9',
    },
  },
};

describe('PlanWizard', () => {
  it('renders script panel when step is script', () => {
    render(
      <PlanWizard
        project={baseProject}
        onStateChange={vi.fn()}
        onApprove={vi.fn()}
        generating={false}
      />
    );
    expect(screen.getByText(/脚本/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue('T')).toBeInTheDocument();
  });
});
