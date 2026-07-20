import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AssetsPage from '@/app/projects/[id]/assets/page';
import { api } from '@/lib/api';

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'test-project-id' }),
  usePathname: () => '/projects/test-project-id/assets',
}));

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    postForm: vi.fn(),
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

const mockAssets = [
  {
    id: 'a1',
    project_id: 'test-project-id',
    type: 'image',
    source: 'upload',
    original_url: 'https://example.com/photo.jpg',
    local_path: '/assets/photo.jpg',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'a2',
    project_id: 'test-project-id',
    type: 'video',
    source: 'pexels',
    original_url: 'https://videos.pexels.com/video.mp4',
    created_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 'a3',
    project_id: 'test-project-id',
    type: 'audio',
    source: 'generated',
    local_path: '/assets/music.ogg',
    created_at: '2024-01-03T00:00:00Z',
  },
];

describe('AssetsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders assets from API', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockAssets);

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText('项目素材')).toBeInTheDocument();
    });

    expect(api.get).toHaveBeenCalledWith('/projects/test-project-id/assets/');
    expect(screen.getByText('photo.jpg')).toBeInTheDocument();
    expect(screen.getByText('video.mp4')).toBeInTheDocument();
    expect(screen.getByText('music.ogg')).toBeInTheDocument();
    expect(screen.getByText('图片')).toBeInTheDocument();
    expect(screen.getByText('视频')).toBeInTheDocument();
    expect(screen.getByText('音频')).toBeInTheDocument();
  });

  it('renders empty state when there are no assets', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText('还没有素材')).toBeInTheDocument();
    });
    expect(screen.getByText('点击上传按钮添加你的第一个素材')).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('加载素材失败'));

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText('加载素材失败')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /重试/ })).toBeInTheDocument();
  });
});
