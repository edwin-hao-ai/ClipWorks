import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import BillingPage from '@/app/billing/page';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    postForm: vi.fn(),
  },
}));

vi.mock('next/navigation', () => ({
  usePathname: () => '/billing',
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn(), back: vi.fn() }),
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
    loading: false,
    fetchMe: vi.fn(),
  }),
}));

describe('BillingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders usage stats from API', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      videos_generated: 12,
      remaining_credits: 88,
      current_plan: 'pro',
    });

    render(<BillingPage />);

    expect(screen.getByRole('heading', { name: '用量统计' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '计费' })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('stat-videos')).toHaveTextContent('12');
    });

    expect(screen.getByTestId('stat-credits')).toHaveTextContent('88');
    expect(screen.getByTestId('stat-plan')).toHaveTextContent('专业版');
    expect(screen.getByText('已生成视频')).toBeInTheDocument();
    expect(screen.getByText('剩余次数')).toBeInTheDocument();
    expect(screen.getByText('当前套餐')).toBeInTheDocument();
  });

  it('falls back to free plan label for unknown plans', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      videos_generated: 0,
      remaining_credits: 0,
      current_plan: 'free',
    });

    render(<BillingPage />);

    expect(await screen.findByTestId('stat-plan')).toHaveTextContent('免费版');
    expect(screen.getByTestId('stat-videos')).toHaveTextContent('0');
    expect(screen.getByTestId('stat-credits')).toHaveTextContent('0');
  });

  it('displays an error message when stats request fails', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('获取用量失败'));

    render(<BillingPage />);

    expect(await screen.findByText('获取用量失败')).toBeInTheDocument();
  });

  it('switches plan via PUT /auth/me and refreshes stats', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      videos_generated: 0,
      remaining_credits: 10,
      current_plan: 'free',
    });
    (api.put as ReturnType<typeof vi.fn>).mockResolvedValue({});

    render(<BillingPage />);
    await screen.findByTestId('stat-plan');

    const proBtn = screen.getByTestId('plan-select-pro');
    const freeBtn = screen.getByTestId('plan-select-free');
    expect(freeBtn).toBeDisabled();
    expect(proBtn).not.toBeDisabled();

    proBtn.click();

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith('/auth/me', { plan: 'pro' });
    });
    // stats re-fetched after a successful switch
    expect((api.get as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThanOrEqual(2);
  });
});
