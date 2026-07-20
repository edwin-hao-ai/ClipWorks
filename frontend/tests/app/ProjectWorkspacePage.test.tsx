import { render, screen } from '@testing-library/react';
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
});
