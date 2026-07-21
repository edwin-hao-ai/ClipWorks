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
            platform: 'TikTok',
            cta: 'Buy now',
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
            cta: 'Shop now',
            duration: 15,
            format: '1:1',
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
          assets: {
            needed: [
              { description: 'Hero product shot', source: 'pexels' },
              { description: 'Upbeat music', source: 'upload' },
            ],
          },
        })}
      />
    );
    expect(screen.getByText('Hero product shot')).toBeInTheDocument();
    expect(screen.getByText('Upbeat music')).toBeInTheDocument();
  });

  it('renders timed scene list', () => {
    render(
      <AgentCanvas
        agentState={state('scenes', {
          scenes: {
            scenes: [
              {
                id: 's1',
                index: 0,
                name: 'Open',
                start_time: 0,
                duration: 5,
                description: 'Logo reveal',
              },
              {
                id: 's2',
                index: 1,
                name: 'Product',
                start_time: 5,
                duration: 10,
                description: 'Feature walkthrough',
              },
            ],
          },
        })}
      />
    );
    expect(screen.getByText('Logo reveal')).toBeInTheDocument();
    expect(screen.getByText('Feature walkthrough')).toBeInTheDocument();
  });

  it('renders effects keywords', () => {
    render(
      <AgentCanvas
        agentState={state('effects', {
          effects: {
            effects: [
              { scene_index: 0, visual_style: '霓虹', animation_keywords: ['glow', 'pan'] },
            ],
          },
        })}
      />
    );
    expect(screen.getByText('霓虹')).toBeInTheDocument();
    expect(screen.getByText('glow')).toBeInTheDocument();
    expect(screen.getByText('pan')).toBeInTheDocument();
  });

  it('renders render status / preview placeholder', () => {
    render(<AgentCanvas agentState={state('render')} />);
    expect(screen.getByText('等待渲染完成…')).toBeInTheDocument();
  });

  it('falls back to understand when agentState is missing', () => {
    render(<AgentCanvas />);
    expect(screen.getByText('等待输入…')).toBeInTheDocument();
  });
});
