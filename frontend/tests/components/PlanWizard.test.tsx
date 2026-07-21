import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

  it('navigates to assets panel and renders the asset list', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const projectWithAssets: Project = {
      ...baseProject,
      agent_state: {
        step: 'script',
        script: baseProject.agent_state!.script,
        assets: {
          needed: [
            { type: 'image', description: '主视觉图', query: 'product hero', count: 2 },
          ],
        },
      },
    };
    render(
      <PlanWizard
        project={projectWithAssets}
        onStateChange={onChange}
        onApprove={vi.fn()}
        generating={false}
      />
    );
    await user.click(screen.getByRole('button', { name: /下一步/i }));
    expect(screen.getByRole('heading', { name: '素材' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('主视觉图')).toBeInTheDocument();
    expect(screen.getByDisplayValue('product hero')).toBeInTheDocument();
  });

  it('navigates to scenes panel and renders the scene list', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const projectWithScenes: Project = {
      ...baseProject,
      agent_state: {
        step: 'scenes',
        script: baseProject.agent_state!.script,
        assets: { needed: [] },
        scenes: {
          scenes: [
            { start: 0, duration: 5, description: '', visual: '', text: '开场', visual_type: 'text', shot: '', transition: 'fade', lower_third: '', required_assets: [] },
          ],
        },
      },
    };
    render(
      <PlanWizard
        project={projectWithScenes}
        onStateChange={onChange}
        onApprove={vi.fn()}
        generating={false}
      />
    );
    await user.click(screen.getByRole('button', { name: '3 场景' }));
    expect(screen.getByRole('heading', { name: '场景' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('开场')).toBeInTheDocument();
  });

  it('navigates to effects panel and renders the effect list', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const projectWithEffects: Project = {
      ...baseProject,
      agent_state: {
        step: 'effects',
        script: baseProject.agent_state!.script,
        assets: { needed: [] },
        scenes: {
          scenes: [
            { start: 0, duration: 5, description: '', visual: '', text: '开场', visual_type: 'text', shot: '', transition: 'fade', lower_third: '', required_assets: [] },
          ],
        },
        effects: {
          effects: [
            { scene_index: 0, visual_style: '极简高级', animation_keywords: [], generate_image: false, generate_image_prompt: '' },
          ],
        },
      },
    };
    render(
      <PlanWizard
        project={projectWithEffects}
        onStateChange={onChange}
        onApprove={vi.fn()}
        generating={false}
      />
    );
    await user.click(screen.getByRole('button', { name: '4 动效' }));
    expect(screen.getByRole('heading', { name: '动效' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '极简高级' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('fires onStateChange after a panel edit', async () => {
    const onChange = vi.fn();
    const projectWithAssets: Project = {
      ...baseProject,
      agent_state: {
        step: 'assets',
        script: baseProject.agent_state!.script,
        assets: {
          needed: [
            { type: 'image', description: '主视觉图', query: 'product hero', count: 2 },
          ],
        },
      },
    };
    render(
      <PlanWizard
        project={projectWithAssets}
        onStateChange={onChange}
        onApprove={vi.fn()}
        generating={false}
      />
    );

    const descInput = screen.getByDisplayValue('主视觉图');
    fireEvent.change(descInput, { target: { value: '更新后的描述' } });

    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.assets).toEqual({
      needed: [
        { type: 'image', description: '更新后的描述', query: 'product hero', count: 2 },
      ],
    });
  });
});
