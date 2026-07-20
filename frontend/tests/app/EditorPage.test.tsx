import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import EditorPage from '@/app/projects/[id]/editor/page';
import { api } from '@/lib/api';

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'test-id' }),
  usePathname: () => '/projects/test-id/editor',
}));

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    postForm: vi.fn(),
  },
  API_URL: 'http://localhost:8000',
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
    loading: false,
    fetchMe: vi.fn(),
    logout: vi.fn(),
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

const mockProject = {
  id: 'test-id',
  title: '测试项目',
  source_type: 'url',
  status: 'ready',
  target_format: '16:9',
  created_at: '',
  updated_at: '',
};

const mockComposition = {
  id: 'comp-1',
  width: 1920,
  height: 1080,
  duration: 10,
  fps: 30,
  metadata: {},
  tracks: [
    {
      id: 't1',
      type: 'video',
      index: 0,
      name: '视频轨道',
      clips: [{ id: 'c1', start_time: 0, duration: 5 }],
    },
  ],
};

describe('EditorPage', () => {
  it('renders loading state initially', () => {
    render(<EditorPage />);
    expect(screen.getByText('加载编辑器中…')).toBeInTheDocument();
  });

  it('renders editor after project and composition load', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') return Promise.resolve(mockProject);
      if (url === '/compositions/test-id') return Promise.resolve(mockComposition);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      return Promise.reject(new Error(`unexpected ${url}`));
    });

    render(<EditorPage />);

    expect(await screen.findByText('测试项目 - 时间线编辑器')).toBeInTheDocument();
    expect(screen.getByText('返回工作区')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /保存/ })).toBeInTheDocument();
    expect(screen.getByText('时间线')).toBeInTheDocument();
    expect(screen.getByText('暂无预览')).toBeInTheDocument();
  });

  it('saves composition and shows success status', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url === '/projects/test-id') return Promise.resolve(mockProject);
      if (url === '/compositions/test-id') return Promise.resolve(mockComposition);
      if (url === '/projects/test-id/renders/') return Promise.resolve([]);
      return Promise.reject(new Error(`unexpected ${url}`));
    });
    (api.put as ReturnType<typeof vi.fn>).mockResolvedValue(mockComposition);

    render(<EditorPage />);
    await screen.findByRole('button', { name: /保存/ });

    fireEvent.click(screen.getByRole('button', { name: /保存/ }));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith('/compositions/test-id', mockComposition);
    });
    expect(await screen.findByText('已保存')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('加载编辑器失败'));

    render(<EditorPage />);

    expect(await screen.findByText('加载编辑器失败')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /重试/ })).toBeInTheDocument();
  });
});
