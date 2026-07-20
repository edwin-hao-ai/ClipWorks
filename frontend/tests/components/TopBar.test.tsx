import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TopBar } from '@/components/layout/TopBar';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn() },
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      user: { id: 'u1', email: 'test@example.com', name: 'Test User' },
      logout: vi.fn(),
    }),
}));

describe('TopBar 账户下拉菜单', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ remaining_credits: 5 });
  });

  it('点击头像打开菜单，按 Escape 关闭', () => {
    render(<TopBar title="项目" />);

    fireEvent.click(screen.getByRole('button', { name: '账户菜单' }));
    expect(screen.getByRole('button', { name: /退出登录/ })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('button', { name: /退出登录/ })).not.toBeInTheDocument();
  });

  it('点击菜单外部区域关闭菜单', () => {
    render(
      <div>
        <TopBar title="项目" />
        <button>保存</button>
      </div>
    );

    fireEvent.click(screen.getByRole('button', { name: '账户菜单' }));
    expect(screen.getByRole('button', { name: /退出登录/ })).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole('button', { name: '保存' }));
    expect(screen.queryByRole('button', { name: /退出登录/ })).not.toBeInTheDocument();
  });

  it('点击菜单内部不关闭，再点头像切换关闭', () => {
    render(<TopBar title="项目" />);

    const avatar = screen.getByRole('button', { name: '账户菜单' });
    fireEvent.click(avatar);
    expect(screen.getByRole('button', { name: /退出登录/ })).toBeInTheDocument();

    // 菜单内部 mousedown（如点到菜单里的邮箱文字区）不应关闭。
    // 邮箱在顶栏用户信息区和菜单头部各出现一次，取菜单内那一处。
    const emails = screen.getAllByText('test@example.com');
    fireEvent.mouseDown(emails[emails.length - 1]);
    expect(screen.getByRole('button', { name: /退出登录/ })).toBeInTheDocument();

    fireEvent.click(avatar);
    expect(screen.queryByRole('button', { name: /退出登录/ })).not.toBeInTheDocument();
  });
});
