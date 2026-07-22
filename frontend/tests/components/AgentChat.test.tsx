import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { AgentChat } from '@/components/project/AgentChat';
import { AgentPlan } from '@/lib/types';
import { api } from '@/lib/api';

const scenes = [
  { id: 's1', index: 0, name: '开场', start_time: 0, duration: 5 },
];

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

vi.mock('@/lib/api', () => ({
  api: {
    post: vi.fn(),
    stream: vi.fn(),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AgentChat', () => {
  it('renders initial agent message', () => {
    render(<AgentChat projectId="p1" mode="modify" onStatusChange={() => {}} />);
    expect(screen.getByText(/我是你的 AI 导演/)).toBeInTheDocument();
  });

  it('shows selected scene badge', () => {
    render(
      <AgentChat projectId="p1" mode="modify" selectedSceneId="s1" scenes={scenes} onStatusChange={() => {}} />
    );
    expect(screen.getByText('开场')).toBeInTheDocument();
  });

  it('auto-adds context message when a scene is selected', () => {
    render(
      <AgentChat projectId="p1" mode="modify" selectedSceneId="s1" scenes={scenes} onStatusChange={() => {}} />
    );
    expect(screen.getByText(/你选中了「开场」/)).toBeInTheDocument();
  });

  it('does not duplicate context message when the same scene stays selected', () => {
    const { rerender } = render(
      <AgentChat projectId="p1" mode="modify" selectedSceneId="s1" scenes={scenes} onStatusChange={() => {}} />
    );
    rerender(
      <AgentChat projectId="p1" mode="modify" selectedSceneId="s1" scenes={scenes} onStatusChange={() => {}} />
    );
    const messages = screen.getAllByText(/你选中了「开场」/);
    expect(messages).toHaveLength(1);
  });

  it('sends scene_id when a scene is selected and a quick prompt is clicked', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ reply: '好的' });

    render(
      <AgentChat projectId="p1" mode="modify" selectedSceneId="s1" scenes={scenes} onStatusChange={() => {}} />
    );

    fireEvent.click(screen.getByText('更活泼一点'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/p1/agent/chat', {
        message: '更活泼一点',
        render: true,
        scene_id: 's1',
      });
    });
  });

  it('sends a typed message without scene_id when no scene is selected', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ reply: '收到' });

    render(<AgentChat projectId="p1" mode="modify" onStatusChange={() => {}} />);

    const input = screen.getByPlaceholderText('输入创作或修改指令…');
    fireEvent.change(input, { target: { value: 'hello' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/p1/agent/chat', {
        message: 'hello',
        render: true,
      });
    });
  });

  it('calls onStatusChange when the API returns a job_id', async () => {
    const onStatusChange = vi.fn();
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ reply: '开始生成', job_id: 'job-1' });

    render(<AgentChat projectId="p1" mode="modify" onStatusChange={onStatusChange} />);

    fireEvent.click(screen.getByText('更活泼一点'));

    await waitFor(() => {
      expect(onStatusChange).toHaveBeenCalledWith('generating');
    });
  });

  it('renders PlanApproval when a pending plan is provided in plan mode', async () => {
    const pendingPlan: AgentPlan = {
      title: '测试方案',
      hook: '钩子文案',
      format: '9:16',
      duration: 15,
      engine_hint: 'remotion',
      assets_needed: [],
      scenes: [
        { start: 0, duration: 5, description: '开场', visual: 'intro', text: '你好' },
      ],
    };
    const onApprove = vi.fn();
    const onStatusChange = vi.fn();

    render(
      <AgentChat
        projectId="p1"
        mode="plan"
        agentState={{ step: 'pending_approval', pending_plan: pendingPlan }}
        onStatusChange={onStatusChange}
      />
    );

    expect(screen.getByText('方案已就绪 · 待确认')).toBeInTheDocument();
    expect(screen.getByText('9:16 · 15s · 1 镜')).toBeInTheDocument();
    expect(screen.getByText('确认生成')).toBeInTheDocument();
    expect(screen.getByText('再改改')).toBeInTheDocument();

    fireEvent.click(screen.getByText('确认生成'));
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/p1/agent/approve', {});
    });
  });
});
