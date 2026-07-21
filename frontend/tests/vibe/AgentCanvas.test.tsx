import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AgentCanvas } from '@/components/project/AgentCanvas';
import { AgentState } from '@/lib/types';

function state(step: AgentState['step'], payload: Record<string, unknown> = {}): AgentState {
  return { step, payload } as AgentState;
}

describe('AgentCanvas', () => {
  it('renders understand summary', () => {
    render(
      <AgentCanvas
        agentState={state('understand', {
          understand: { summary: 'A product promo' },
        })}
      />
    );
    expect(screen.getByText('A product promo')).toBeInTheDocument();
  });

  it('renders understand meta chips', () => {
    render(
      <AgentCanvas
        agentState={state('understand', {
          understand: {
            summary: 'Promo video',
            duration: 30,
            format: '9:16',
            audience: 'Gen Z',
            style: 'cyberpunk',
          },
        })}
      />
    );
    expect(screen.getByText('Promo video')).toBeInTheDocument();
    expect(screen.getByText('9:16')).toBeInTheDocument();
    expect(screen.getByText('30 秒')).toBeInTheDocument();
    expect(screen.getByText('Gen Z')).toBeInTheDocument();
    expect(screen.getByText('cyberpunk')).toBeInTheDocument();
  });

  it('renders script artifact', () => {
    render(
      <AgentCanvas
        agentState={state('script', {
          script: {
            title: 'Summer Sale',
            hook: '50% off today only',
            narrative_arc: 'Intro → Offer → CTA',
          },
        })}
      />
    );
    expect(screen.getByText('Summer Sale')).toBeInTheDocument();
    expect(screen.getByText('50% off today only')).toBeInTheDocument();
    expect(screen.getByText('Intro → Offer → CTA')).toBeInTheDocument();
  });

  it('renders assets list', () => {
    render(
      <AgentCanvas
        agentState={state('assets', {
          assets: { needed: [{ description: 'Hero image', source: 'upload' }] },
        })}
      />
    );
    expect(screen.getByText('素材清单')).toBeInTheDocument();
    expect(screen.getByText('Hero image')).toBeInTheDocument();
  });

  it('renders scenes list', () => {
    render(
      <AgentCanvas
        agentState={state('scenes', {
          scenes: {
            scenes: [
              { description: 'Opening', text: 'Hello', visual: 'dark gradient', start_time: 0, duration: 5 },
            ],
          },
        })}
      />
    );
    expect(screen.getByText('场景规划')).toBeInTheDocument();
    expect(screen.getByText('Opening')).toBeInTheDocument();
  });

  it('renders effects list', () => {
    render(
      <AgentCanvas
        agentState={state('effects', {
          effects: {
            effects: [
              { scene_index: 0, visual_style: 'neon', animation_keywords: ['fade', 'glow'] },
            ],
          },
        })}
      />
    );
    expect(screen.getByText('动效设计')).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('neon'))).toBeInTheDocument();
  });

  it('renders render placeholder', () => {
    render(<AgentCanvas agentState={state('render', { render: { job_id: 'job-1' } })} />);
    expect(screen.getByText('渲染')).toBeInTheDocument();
    expect(screen.getByText('渲染任务已创建：job-1')).toBeInTheDocument();
  });

  it('renders generic fallback for unknown steps', () => {
    render(<AgentCanvas agentState={state('chatting')} />);
    expect(screen.getByText('当前步骤：chatting')).toBeInTheDocument();
  });

  it('falls back to understand when agentState is missing', () => {
    render(<AgentCanvas />);
    expect(screen.getByText('等待输入…')).toBeInTheDocument();
  });
});
