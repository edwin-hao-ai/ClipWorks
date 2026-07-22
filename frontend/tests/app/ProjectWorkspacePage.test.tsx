import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProjectWorkspacePage from '@/app/projects/[id]/page';
import { api } from '@/lib/api';

let mockSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'test-id' }),
  usePathname: () => '/projects/test-id',
  useSearchParams: () => mockSearchParams,
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
  streamJsonLines: vi.fn(),
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
    loading: false,
    fetchMe: vi.fn(),
  }),
}));

const makeProject = (overrides: Partial<import('@/lib/types').Project> = {}) => ({
  id: 'test-id',
  title: 'Project',
  source_type: 'url' as const,
  status: 'draft' as const,
  target_format: '16:9',
  created_at: '',
  updated_at: '',
  composition: { tracks: [] },
  ...overrides,
});

describe.sequential('ProjectWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('renders project title from API', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') return Promise.resolve(makeProject({ title: 'Real Project' }));
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    expect(await screen.findByText('Real Project', undefined, { timeout: 3000 })).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('加载失败'));

    render(<ProjectWorkspacePage />);
    expect(await screen.findByText('加载失败', undefined, { timeout: 3000 })).toBeInTheDocument();
  });

  it('shows pipeline progress based on latest job progress', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(makeProject({ title: 'Generating Project', status: 'generating' }));
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') return Promise.resolve([{ id: 'job-1', status: 'running', progress: 50 }]);
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    expect(await screen.findByText('Agent 执行日志', undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getAllByText('生成场景').length).toBeGreaterThanOrEqual(1);
  });

  it('shows completed pipeline for ready project', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(makeProject({ title: 'Ready Project', status: 'ready' }));
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') {
        return Promise.resolve([{ id: 'job-1', status: 'completed', progress: 100 }]);
      }
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    expect(await screen.findByText('输出成片', undefined, { timeout: 3000 })).toBeInTheDocument();
  });

  it('shows failure message for failed project', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(makeProject({ title: 'Failed Project', status: 'failed' }));
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') {
        return Promise.resolve([{ id: 'job-1', status: 'failed', progress: 0, error_message: '渲染超时' }]);
      }
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    expect(await screen.findByText(/渲染超时/, undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getAllByText('生成失败').length).toBeGreaterThanOrEqual(1);
  });

  it('shows Vibe layout in planning mode and hides editor panels for draft projects', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(
          makeProject({
            title: 'Draft Project',
            status: 'planning',
            agent_state: {
              step: 'script',
              script: {
                title: 'Draft Project',
                hook: '',
                roles: [],
                narrative_arc: '',
                cta: '',
                duration: 30,
                format: '16:9',
              },
            },
          })
        );
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    expect(await screen.findByTestId('vibe-header', undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByLabelText('创作进度')).toBeInTheDocument();
    expect(screen.getByLabelText('Agent 自主级别')).toBeInTheDocument();
    // The script title appears in both the top bar (h1) and AgentCanvas (h4);
    // target the canvas heading explicitly now that legacy top-level state is supported.
    expect(screen.getByRole('heading', { level: 4, name: 'Draft Project' })).toBeInTheDocument();
    expect(screen.queryByText('暂无预览')).not.toBeInTheDocument();
    expect(screen.queryByText('项目属性')).not.toBeInTheDocument();
    expect(screen.queryByText('场景卡片')).not.toBeInTheDocument();
  });

  it('shows centered generation progress for generating projects', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(makeProject({ title: 'Generating Project', status: 'generating' }));
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') {
        return Promise.resolve([{ id: 'job-1', status: 'running', progress: 50 }]);
      }
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    expect(await screen.findByText(/正在生成/, undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText('Agent 执行日志')).toBeInTheDocument();
    expect(screen.getAllByText('生成场景').length).toBeGreaterThanOrEqual(1);
  });

  it('shows three-column workspace with chat, canvas and timeline for ready projects', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(makeProject({ title: 'Ready Project', status: 'ready' }));
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') {
        return Promise.resolve([{ id: 'job-1', status: 'completed', progress: 100 }]);
      }
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    expect(await screen.findByText('AI 导演 · 修改', undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText('预览 & 故事板')).toBeInTheDocument();
    expect(screen.getByText('Timeline')).toBeInTheDocument();
    expect(screen.getByText('打开高级编辑器 →')).toBeInTheDocument();
    expect(screen.queryByText('项目属性')).not.toBeInTheDocument();
  });

  it('saves autonomy level changes and updates local state', async () => {
    const user = userEvent.setup();
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(
          makeProject({
            title: 'Draft Project',
            status: 'planning',
            agent_state: {
              step: 'script',
              script: {
                title: 'Old Title',
                hook: '',
                roles: [],
                narrative_arc: '',
                cta: '',
                duration: 30,
                format: '16:9',
              },
            },
          })
        );
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      return Promise.resolve({});
    });
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({});

    render(<ProjectWorkspacePage />);
    const select = await screen.findByLabelText('Agent 自主级别', undefined, { timeout: 3000 });
    await user.selectOptions(select, 'full_auto');

    expect(select).toHaveValue('full_auto');
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        '/projects/test-id/agent/state',
        expect.objectContaining({
          state: expect.objectContaining({ autonomy_level: 'full_auto' }),
        })
      )
    );
  });

  it('reverts local state and shows error banner when autonomy save fails', async () => {
    const user = userEvent.setup();
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(
          makeProject({
            title: 'Draft Project',
            status: 'planning',
            agent_state: {
              step: 'script',
              script: {
                title: 'Original Title',
                hook: '',
                roles: [],
                narrative_arc: '',
                cta: '',
                duration: 30,
                format: '16:9',
              },
            },
          })
        );
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      return Promise.resolve({});
    });
    (api.post as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id/agent/state') {
        return Promise.reject(new Error('save failed'));
      }
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    const select = await screen.findByLabelText('Agent 自主级别', undefined, { timeout: 3000 });
    await user.selectOptions(select, 'full_auto');

    expect(await screen.findByTestId('action-error-banner')).toHaveTextContent('save failed');
    expect(select).toHaveValue('confirm_each');
  });

});
