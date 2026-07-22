import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import HomePage from '@/app/page';
import { api } from '@/lib/api';

const push = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
  usePathname: () => '/',
}));

vi.mock('@/lib/api', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe('HomePage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
      if (path === '/auth/me') {
        return Promise.resolve({ user: { id: 'u1', email: 'test@example.com' } });
      }
      if (path === '/projects/') {
        return Promise.resolve([]);
      }
      return Promise.resolve({});
    });
  });

  it('renders agent conversation entry headline', async () => {
    render(<HomePage />);
    expect(screen.getByText('一句话，一条成片')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/帮我做一个 15 秒的产品介绍视频/)
    ).toBeInTheDocument();
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/projects/'));
  });

  it('renders quick tip buttons', async () => {
    render(<HomePage />);
    expect(screen.getByText('从公众号文章生成视频')).toBeInTheDocument();
    expect(screen.getByText('商品详情页转营销短片')).toBeInTheDocument();
    expect(screen.getByText('生日祝福视频')).toBeInTheDocument();
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/projects/'));
  });

  it('uses Next.js Link for internal navigation', async () => {
    render(<HomePage />);
    expect(screen.getByRole('link', { name: 'Projects' })).toHaveAttribute('href', '/projects');
    expect(screen.getByRole('link', { name: 'Billing' })).toHaveAttribute('href', '/billing');
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/settings');
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/projects/'));
  });

  it('checks auth and creates a project from the input, then navigates', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'demo-123' });

    render(<HomePage />);
    const input = screen.getByPlaceholderText(/帮我做一个/);
    fireEvent.change(input, { target: { value: '测试项目' } });
    fireEvent.click(screen.getByRole('button', { name: /生成视频 →/ }));

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/auth/me');
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/', {
        title: '测试项目',
        source_url: '',
        source_type: 'url',
        target_format: undefined,
        target_duration: undefined,
      });
    });

    expect(push).toHaveBeenCalledWith('/projects/demo-123?initialPrompt=%E6%B5%8B%E8%AF%95%E9%A1%B9%E7%9B%AE');
  });

  it('extracts intent from prompt and sends it when creating project', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'demo-789' });

    render(<HomePage />);
    const input = screen.getByPlaceholderText(/帮我做一个/);
    fireEvent.change(input, {
      target: {
        value: 'https://example.com/article 帮我做一个 30 秒的产品视频，9:16，活泼风格',
      },
    });
    fireEvent.click(screen.getByRole('button', { name: /生成视频 →/ }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/', {
        title: '帮我做一个 30 秒的产品视频，9:16，活泼风格',
        source_url: 'https://example.com/article',
        source_type: 'url',
        target_format: '9:16',
        target_duration: 30,
      });
    });

    expect(push).toHaveBeenCalledWith(
      expect.stringContaining('/projects/demo-789?initialPrompt=')
    );
  });

  it('fills prompt from a quick tip button', async () => {
    render(<HomePage />);
    fireEvent.click(screen.getByText('生日祝福视频'));
    const input = screen.getByPlaceholderText(/帮我做一个/) as HTMLTextAreaElement;
    expect(input.value).toBe('生日祝福视频');
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/projects/'));
  });

  it('redirects to login when not authenticated', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
      if (path === '/auth/me') return Promise.reject(new Error('Unauthorized'));
      return Promise.resolve([]);
    });

    render(<HomePage />);
    const input = screen.getByPlaceholderText(/帮我做一个/);
    fireEvent.change(input, { target: { value: '测试项目' } });
    fireEvent.click(screen.getByRole('button', { name: /生成视频 →/ }));

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith('/login');
    });
    expect(api.post).not.toHaveBeenCalled();
  });

  it('displays an error message when project creation fails', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockImplementation(() =>
      Promise.reject(new Error('网络错误'))
    );

    render(<HomePage />);
    const input = screen.getByPlaceholderText(/帮我做一个/);
    fireEvent.change(input, { target: { value: '失败的项目' } });
    fireEvent.click(screen.getByRole('button', { name: /生成视频 →/ }));

    const errorEl = await screen.findByTestId('homepage-error');
    expect(errorEl.textContent).toBe('网络错误');
  });

  it('does not submit when input is empty', async () => {
    render(<HomePage />);
    fireEvent.click(screen.getByRole('button', { name: /生成视频 →/ }));
    // 页面挂载会拉取最近项目，因此只断言不会调用 /auth/me 也不会创建项目。
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/projects/');
    });
    expect(api.get).not.toHaveBeenCalledWith('/auth/me');
    expect(api.post).not.toHaveBeenCalled();
  });

  describe('RecentProjects', () => {
    it('shows loading skeleton while fetching', () => {
      (api.get as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        if (path === '/auth/me') return Promise.resolve({ user: { id: 'u1' } });
        return new Promise(() => {}); // never resolve /projects/
      });

      render(<HomePage />);
      expect(screen.getByText('最近项目')).toBeInTheDocument();
      expect(document.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
    });

    it('renders recent project cards', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        if (path === '/auth/me') return Promise.resolve({ user: { id: 'u1' } });
        return Promise.resolve([
          {
            id: 'p1',
            title: '项目一',
            status: 'ready',
            updated_at: new Date(Date.now() - 3600 * 1000).toISOString(),
          },
          {
            id: 'p2',
            title: '项目二',
            status: 'draft',
            updated_at: new Date(Date.now() - 86400 * 1000).toISOString(),
          },
        ]);
      });

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByTestId('recent-projects')).toBeInTheDocument();
      });

      expect(screen.getByText('项目一')).toBeInTheDocument();
      expect(screen.getByText('项目二')).toBeInTheDocument();
      expect(screen.getByText('已完成')).toBeInTheDocument();
      expect(screen.getByText('草稿')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /项目一/ })).toHaveAttribute('href', '/projects/p1');
    });

    it('hides recent projects section when list is empty', async () => {
      render(<HomePage />);

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith('/projects/');
      });

      expect(screen.queryByTestId('recent-projects')).not.toBeInTheDocument();
    });
  });
});
