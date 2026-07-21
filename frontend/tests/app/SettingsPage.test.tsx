import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SettingsPage from '@/app/settings/page';

vi.mock('next/navigation', () => ({
  usePathname: () => '/settings',
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn(), back: vi.fn() }),
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (selector?: (state: unknown) => unknown) => {
    const state = {
      user: { id: 'test-user', email: 'test@example.com', name: 'Test User', provider: 'google' },
      loading: false,
      fetchMe: vi.fn(),
      logout: vi.fn(),
    };
    return selector ? selector(state) : state;
  },
}));

describe('SettingsPage', () => {
  it('renders account settings with user info', () => {
    render(<SettingsPage />);

    expect(screen.getByRole('heading', { name: '账户设置' })).toBeInTheDocument();
    expect(screen.getByText('管理你的账户信息和偏好')).toBeInTheDocument();

    // Account info rows
    const rows = screen.getAllByText(/昵称|邮箱|登录方式|通知/);
    expect(rows.length).toBeGreaterThanOrEqual(4);

    expect(screen.getByTestId('setting-value-昵称')).toHaveTextContent('Test User');
    expect(screen.getByTestId('setting-value-邮箱')).toHaveTextContent('test@example.com');
    expect(screen.getByTestId('setting-value-登录方式')).toHaveTextContent('google');
    expect(screen.getByTestId('setting-value-通知')).toHaveTextContent('通知已开启（本地偏好）');
  });
});
