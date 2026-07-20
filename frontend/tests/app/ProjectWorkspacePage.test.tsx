import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProjectWorkspacePage from '@/app/projects/[id]/page';
import { api, streamJsonLines } from '@/lib/api';

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

  it('shows PlanWizard in planning mode and hides editor panels for draft projects', async () => {
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
    expect(await screen.findByRole('button', { name: '1 脚本' }, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '2 素材' })).toBeInTheDocument();
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

  it('shows full editor with property panel and scene cards for ready projects', async () => {
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
    expect(await screen.findByText('项目属性', undefined, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText('场景卡片')).toBeInTheDocument();
  });

  it('saves wizard state changes and updates local state', async () => {
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
    const input = await screen.findByDisplayValue('Old Title', undefined, { timeout: 3000 });
    fireEvent.change(input, { target: { value: 'New Title' } });

    expect(await screen.findByDisplayValue('New Title')).toBeInTheDocument();
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        '/projects/test-id/agent/state',
        expect.objectContaining({
          state: expect.objectContaining({
            script: expect.objectContaining({ title: 'New Title' }),
          }),
        })
      )
    );
  });

  it('reverts local state and shows error banner when state save fails', async () => {
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
    const input = await screen.findByDisplayValue('Original Title', undefined, { timeout: 3000 });
    fireEvent.change(input, { target: { value: 'Changed Title' } });

    expect(await screen.findByTestId('action-error-banner')).toHaveTextContent('save failed');
    expect(screen.getByDisplayValue('Original Title')).toBeInTheDocument();
  });

  it('runs a wizard step, streams chunks, and refreshes state after stream', async () => {
    const user = userEvent.setup();
    const updatedState = {
      step: 'scenes',
      script: {
        title: 'Draft Project',
        hook: '',
        roles: [],
        narrative_arc: '',
        cta: '',
        duration: 30,
        format: '16:9',
      },
      scenes: { scenes: [] },
    };

    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(
          makeProject({
            title: 'Draft Project',
            status: 'planning',
            agent_state: {
              step: 'script',
              script: updatedState.script,
            },
          })
        );
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      if (url === '/projects/test-id/agent/state') return Promise.resolve(updatedState);
      return Promise.resolve({});
    });
    (streamJsonLines as ReturnType<typeof vi.fn>).mockImplementation(async function* () {
      yield { type: 'progress' };
      yield { type: 'token', text: 'ok' };
    });

    render(<ProjectWorkspacePage />);
    const runButton = await screen.findByRole('button', { name: '重新生成当前步骤' }, { timeout: 3000 });
    await user.click(runButton);

    await waitFor(() =>
      expect(streamJsonLines).toHaveBeenCalledWith(
        '/projects/test-id/agent/step/script',
        expect.objectContaining({ user_input: '' })
      )
    );
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/projects/test-id/agent/state'));
  });

  it('approves the plan and transitions to generating', async () => {
    const user = userEvent.setup();
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(
          makeProject({
            title: 'Draft Project',
            status: 'planning',
            agent_state: {
              step: 'effects',
              script: {
                title: 'Draft Project',
                hook: '',
                roles: [],
                narrative_arc: '',
                cta: '',
                duration: 30,
                format: '16:9',
              },
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
          })
        );
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      return Promise.resolve({});
    });
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({});

    render(<ProjectWorkspacePage />);
    await user.click(await screen.findByRole('button', { name: '4 动效' }, { timeout: 3000 }));
    const approveButton = await screen.findByRole('button', { name: '确认生成' }, { timeout: 3000 });
    await user.click(approveButton);

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/projects/test-id/agent/approve', {})
    );
    expect(await screen.findByText(/《Draft Project》/)).toBeInTheDocument();
  });

  it('sets creditBlocked when approve returns 402', async () => {
    const user = userEvent.setup();
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') {
        return Promise.resolve(
          makeProject({
            title: 'Draft Project',
            status: 'planning',
            agent_state: {
              step: 'effects',
              script: {
                title: 'Draft Project',
                hook: '',
                roles: [],
                narrative_arc: '',
                cta: '',
                duration: 30,
                format: '16:9',
              },
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
          })
        );
      }
      if (url === '/projects/test-id/assets/') return Promise.resolve([]);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      return Promise.resolve({});
    });
    (api.post as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id/agent/approve') {
        return Promise.reject(new Error('API error 402: credits depleted'));
      }
      return Promise.resolve({});
    });

    render(<ProjectWorkspacePage />);
    await user.click(await screen.findByRole('button', { name: '4 动效' }, { timeout: 3000 }));
    const approveButton = await screen.findByRole('button', { name: '确认生成' }, { timeout: 3000 });
    await user.click(approveButton);

    expect(await screen.findByTestId('credits-depleted-banner')).toBeInTheDocument();
  });
});
