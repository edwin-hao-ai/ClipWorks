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
    get: vi.fn(() => Promise.resolve([])),
  },
}));

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders launchpad headline', () => {
    render(<HomePage />);
    expect(screen.getByText('一句话，一段素材，一条成片')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/帮我做一个/)).toBeInTheDocument();
  });

  it('renders quick prompt buttons', () => {
    render(<HomePage />);
    expect(screen.getByText('小红书口播精剪')).toBeInTheDocument();
  });

  it('creates a project from the input and navigates on submit', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'demo-123' });

    render(<HomePage />);
    const input = screen.getByPlaceholderText(/帮我做一个/);
    fireEvent.change(input, { target: { value: '测试项目' } });
    fireEvent.click(screen.getByRole('button', { name: /开始创作/ }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/', {
        title: '测试项目',
        source_url: '',
        source_type: 'url',
      });
    });

    expect(push).toHaveBeenCalledWith('/projects/demo-123?initialPrompt=%E6%B5%8B%E8%AF%95%E9%A1%B9%E7%9B%AE');
  });

  it('creates a project from a quick prompt', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'demo-456' });

    render(<HomePage />);
    fireEvent.click(screen.getByText('教程视频'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/', {
        title: '教程视频',
        source_url: '',
        source_type: 'url',
      });
    });

    expect(push).toHaveBeenCalledWith('/projects/demo-456?initialPrompt=%E6%95%99%E7%A8%8B%E8%A7%86%E9%A2%91');
  });

  it('displays an error message when project creation fails', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('网络错误'));

    render(<HomePage />);
    const input = screen.getByPlaceholderText(/帮我做一个/);
    fireEvent.change(input, { target: { value: '失败的项目' } });
    fireEvent.click(screen.getByRole('button', { name: /开始创作/ }));

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument();
    });
  });

  it('does not submit when input is empty', () => {
    render(<HomePage />);
    fireEvent.click(screen.getByRole('button', { name: /开始创作/ }));
    expect(api.post).not.toHaveBeenCalled();
  });
});
