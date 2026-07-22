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
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      user: { id: 'u1', email: 'test@example.com' },
    });
  });

  it('renders agent conversation entry headline', () => {
    render(<HomePage />);
    expect(screen.getByText('一句话，一条成片')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/帮我做一个 15 秒的产品介绍视频/)
    ).toBeInTheDocument();
  });

  it('renders quick prompt buttons', () => {
    render(<HomePage />);
    expect(screen.getByText('从公众号文章生成视频')).toBeInTheDocument();
    expect(screen.getByText('商品详情页转营销短片')).toBeInTheDocument();
    expect(screen.getByText('生日祝福视频')).toBeInTheDocument();
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
        prompt: '测试项目',
      });
    });

    expect(push).toHaveBeenCalledWith('/projects/demo-123?initialPrompt=%E6%B5%8B%E8%AF%95%E9%A1%B9%E7%9B%AE');
  });

  it('fills prompt from a quick tip button', () => {
    render(<HomePage />);
    fireEvent.click(screen.getByText('生日祝福视频'));
    const input = screen.getByPlaceholderText(/帮我做一个/) as HTMLTextAreaElement;
    expect(input.value).toBe('生日祝福视频');
  });

  it('redirects to login when not authenticated', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Unauthorized'));

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
    (api.post as ReturnType<typeof vi.fn>).mockImplementation(() => Promise.reject(new Error('网络错误')));

    render(<HomePage />);
    const input = screen.getByPlaceholderText(/帮我做一个/);
    fireEvent.change(input, { target: { value: '失败的项目' } });
    fireEvent.click(screen.getByRole('button', { name: /生成视频 →/ }));

    const errorEl = await screen.findByTestId('homepage-error');
    expect(errorEl.textContent).toBe('网络错误');
  });

  it('does not submit when input is empty', () => {
    render(<HomePage />);
    fireEvent.click(screen.getByRole('button', { name: /生成视频 →/ }));
    expect(api.get).not.toHaveBeenCalled();
    expect(api.post).not.toHaveBeenCalled();
  });
});
