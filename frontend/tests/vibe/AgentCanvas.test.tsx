import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AgentCanvas } from '@/components/project/AgentCanvas';
import { AgentState } from '@/lib/types';

function state(step: AgentState['step'], payload: AgentState['payload'] = {}): AgentState {
  return { step, payload };
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

  it('renders generic fallback for unknown steps', () => {
    render(<AgentCanvas agentState={state('assets')} />);
    expect(screen.getByText('当前步骤：assets')).toBeInTheDocument();
  });

  it('falls back to understand when agentState is missing', () => {
    render(<AgentCanvas />);
    expect(screen.getByText('等待输入…')).toBeInTheDocument();
  });
});
