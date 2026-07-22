import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AgentCanvas } from '@/components/project/AgentCanvas';
import { AgentState, Project, Scene } from '@/lib/types';

function state(step: AgentState['step'], payload: Record<string, unknown> = {}): AgentState {
  return { step, payload } as AgentState;
}

describe('AgentCanvas', () => {
  it('renders understand summary and meta chips', () => {
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

  it('renders script artifact with title, hook and arc', () => {
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
    expect(screen.getAllByText('动效设计').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText((content) => content.includes('neon'))).toBeInTheDocument();
  });

  it('renders render job info', () => {
    render(<AgentCanvas agentState={state('render', { render: { job_id: 'job-1' } })} />);
    expect(screen.getByText('渲染')).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('job-1'))).toBeInTheDocument();
  });

  it('renders waiting message for empty non-understand steps', () => {
    render(<AgentCanvas agentState={state('chatting')} />);
    expect(screen.getByText('等待输入…')).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('chatting'))).toBeInTheDocument();
  });

  it('renders welcome state when agentState is missing', () => {
    render(<AgentCanvas />);
    expect(screen.getByText('让 AI 导演帮你做视频')).toBeInTheDocument();
  });

  it('falls back to top-level script when payload script is missing', () => {
    render(
      <AgentCanvas
        agentState={{
          step: 'script',
          script: { title: 'Legacy Script', hook: 'Legacy hook', narrative_arc: 'Arc' },
        } as AgentState}
      />
    );
    expect(screen.getByText('Legacy Script')).toBeInTheDocument();
    expect(screen.getByText('Legacy hook')).toBeInTheDocument();
  });

  it('falls back to top-level assets when payload assets is missing', () => {
    render(
      <AgentCanvas
        agentState={{
          step: 'assets',
          assets: { needed: [{ description: 'Legacy asset', source: 'stock' }] },
        } as unknown as AgentState}
      />
    );
    expect(screen.getByText('Legacy asset')).toBeInTheDocument();
  });

  it('falls back to top-level scenes when payload scenes is missing', () => {
    render(
      <AgentCanvas
        agentState={{
          step: 'scenes',
          scenes: {
            scenes: [{ description: 'Legacy scene', text: 'Hello', visual: 'gradient', start_time: 0, duration: 3 }],
          },
        } as unknown as AgentState}
      />
    );
    expect(screen.getByText('Legacy scene')).toBeInTheDocument();
  });

  it('falls back to top-level effects when payload effects is missing', () => {
    render(
      <AgentCanvas
        agentState={{
          step: 'effects',
          effects: {
            effects: [{ scene_index: 0, visual_style: 'legacy', animation_keywords: ['zoom'] }],
          },
        } as AgentState}
      />
    );
    expect(screen.getByText((content) => content.includes('legacy'))).toBeInTheDocument();
  });

  it('renders preview & storyboard when project prop is provided', () => {
    const project = {
      id: 'p1',
      title: 'Ready Project',
      source_type: 'url',
      status: 'ready',
      target_format: '16:9',
      created_at: '',
      updated_at: '',
    } as Project;

    render(<AgentCanvas project={project} scenes={[]} />);
    expect(screen.getByText('预览 & 故事板')).toBeInTheDocument();
    expect(screen.getByText('镜 1')).toBeInTheDocument();
    expect(screen.getByText('预览区域')).toBeInTheDocument();
    expect(screen.queryByText('场景卡片')).not.toBeInTheDocument();
  });

  it('renders StoryboardStrip and syncs preview on selection', () => {
    const project = {
      id: 'p1',
      title: 'Storyboard Project',
      source_type: 'url',
      status: 'draft',
      target_format: '9:16',
      created_at: '',
      updated_at: '',
    } as Project;
    const sceneScenes: Scene[] = [
      { id: 's1', index: 0, name: '开场', start_time: 0, duration: 3, text_content: '开场文案' },
      { id: 's2', index: 1, name: '正文', start_time: 3, duration: 4, text_content: '正文文案' },
    ];
    const onSelectScene = vi.fn();

    render(
      <AgentCanvas
        project={project}
        scenes={sceneScenes}
        onSelectScene={onSelectScene}
      />
    );

    expect(screen.getByText('开场')).toBeInTheDocument();
    expect(screen.getByText('正文')).toBeInTheDocument();
    expect(screen.getByText('开场文案')).toBeInTheDocument();

    fireEvent.click(screen.getByText('正文'));
    expect(onSelectScene).toHaveBeenCalledWith('s2');
    expect(screen.getByText('正文文案')).toBeInTheDocument();
  });
});
