import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProjectsPage from '@/app/projects/page';
import { api } from '@/lib/api';

const mockProjects = [
  {
    id: 'p1',
    title: '产品发布视频',
    source_url: 'https://example.com',
    source_type: 'url',
    status: 'draft',
    target_format: '16:9',
    target_duration: 60,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'p2',
    title: '教程视频',
    source_url: '',
    source_type: 'upload',
    status: 'ready',
    target_format: '9:16',
    target_duration: 30,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
];

vi.mock('next/navigation', () => ({
  usePathname: () => '/projects',
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
    loading: false,
    fetchMe: vi.fn(),
    logout: vi.fn(),
  }),
}));

describe('ProjectsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title and loads projects from API', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);

    render(<ProjectsPage />);

    expect(screen.getByText('全部项目')).toBeInTheDocument();
    expect(await screen.findByText('产品发布视频')).toBeInTheDocument();
    expect(screen.getByText('教程视频')).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledWith('/projects/');
  });

  it('renders empty state when no projects exist', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<ProjectsPage />);

    expect(await screen.findByText('开始你的第一个视频项目')).toBeInTheDocument();
    expect(screen.getByText('输入官网链接或上传素材，让 AI 为你生成成片')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /新建项目/ }).length).toBeGreaterThan(0);
  });

  it('renders error message when loading projects fails', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('服务不可用'));

    render(<ProjectsPage />);

    expect(await screen.findByText('服务不可用')).toBeInTheDocument();
  });

  it('deletes a project and reloads the list', async () => {
    // Key mock responses by URL (not call order): the page also triggers other
    // GETs (e.g. the TopBar credits badge), so a strict call-order mock is brittle.
    let list: typeof mockProjects = mockProjects;
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/') return Promise.resolve(list);
      if (url === '/auth/me/stats')
        return Promise.resolve({ videos_generated: 0, remaining_credits: 5, current_plan: 'free' });
      return Promise.resolve([]);
    });
    (api.delete as ReturnType<typeof vi.fn>).mockImplementation(() => {
      list = [mockProjects[1]];
      return Promise.resolve(undefined);
    });

    render(<ProjectsPage />);

    expect(await screen.findByText('产品发布视频')).toBeInTheDocument();

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith('/projects/p1');
    });

    await waitFor(() => {
      expect(screen.queryByText('产品发布视频')).not.toBeInTheDocument();
    });
    expect(screen.getByText('教程视频')).toBeInTheDocument();
  });
});
