import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NewProjectDialog } from '@/components/project/NewProjectDialog';
import { api } from '@/lib/api';

const push = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

vi.mock('@/lib/api', () => ({
  api: {
    post: vi.fn(),
    postForm: vi.fn(),
  },
}));

const openDialog = () => {
  fireEvent.click(screen.getByRole('button', { name: /新建项目/ }));
};

const getPrompt = () => screen.getByTestId('new-project-prompt');

describe('NewProjectDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('opens as an agent-style dialog: prompt input, quick prompts and optional file attachment', () => {
    render(<NewProjectDialog onCreated={() => {}} />);

    openDialog();

    expect(screen.getByRole('heading', { name: '新建项目' })).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(
        '例如：帮我做一个 30 秒的产品介绍视频，9:16，风格活泼，面向年轻人…'
      )
    ).toBeInTheDocument();
    // 快捷词 chips 与首页一致
    expect(screen.getByRole('button', { name: 'SaaS 产品发布' })).toBeInTheDocument();
    // 上传不再是默认表单，而是可选的附加素材行
    expect(screen.getByText(/附加素材文件（可选）/)).toBeInTheDocument();
    expect(screen.getByTestId('new-project-file')).toBeInTheDocument();
  });

  it('creates a project from a prompt with parsed intent and navigates to the workspace', async () => {
    const onCreated = vi.fn();
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'new-project-id' });

    render(<NewProjectDialog onCreated={onCreated} />);

    openDialog();
    const text = '30 秒的产品介绍视频 https://example.com 9:16';
    fireEvent.change(getPrompt(), { target: { value: text } });
    fireEvent.click(screen.getByTestId('new-project-submit'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/', {
        title: '30 秒的产品介绍视频 9:16',
        source_url: 'https://example.com',
        source_type: 'url',
        target_format: '9:16',
        target_duration: 30,
      });
      expect(onCreated).toHaveBeenCalled();
      expect(push).toHaveBeenCalledWith(
        `/projects/new-project-id?initialPrompt=${encodeURIComponent(text)}`
      );
    });

    expect(screen.queryByRole('heading', { name: '新建项目' })).not.toBeInTheDocument();
  });

  it('fills the prompt when a quick prompt chip is clicked', () => {
    render(<NewProjectDialog onCreated={() => {}} />);

    openDialog();
    fireEvent.click(screen.getByRole('button', { name: '小红书口播精剪' }));

    expect(getPrompt()).toHaveValue('小红书口播精剪');
  });

  it('disables submit when prompt and file are both empty', () => {
    render(<NewProjectDialog onCreated={() => {}} />);

    openDialog();
    expect(screen.getByTestId('new-project-submit')).toBeDisabled();

    fireEvent.change(getPrompt(), { target: { value: '随便做点什么' } });
    expect(screen.getByTestId('new-project-submit')).toBeEnabled();
  });

  it('uploads an attached file after project creation and seeds a filename-based prompt', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'upload-project-id' });
    (api.postForm as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'asset-id' });

    render(<NewProjectDialog onCreated={() => {}} />);

    openDialog();
    const file = new File(['x'], 'test.mp4', { type: 'video/mp4' });
    fireEvent.change(screen.getByTestId('new-project-file'), {
      target: { files: [file] },
    });

    expect(screen.getByTestId('new-project-submit')).toBeEnabled();
    fireEvent.click(screen.getByTestId('new-project-submit'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/', {
        title: 'test.mp4',
        source_url: '',
        source_type: 'upload',
        target_format: undefined,
        target_duration: undefined,
      });
      expect(api.postForm).toHaveBeenCalledTimes(1);
      const [path, form] = (api.postForm as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(path).toBe('/projects/upload-project-id/assets/');
      expect((form as FormData).get('file')).toBe(file);
      expect(push).toHaveBeenCalledWith(
        `/projects/upload-project-id?initialPrompt=${encodeURIComponent('用我上传的素材「test.mp4」做一个视频')}`
      );
    });
  });

  it('closes on Escape key', () => {
    render(<NewProjectDialog onCreated={() => {}} />);

    openDialog();
    expect(screen.getByRole('heading', { name: '新建项目' })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('heading', { name: '新建项目' })).not.toBeInTheDocument();
  });

  it('closes on backdrop click but not on panel click', () => {
    render(<NewProjectDialog onCreated={() => {}} />);

    openDialog();
    expect(screen.getByTestId('new-project-backdrop')).toBeInTheDocument();

    // 点面板内部（事件在面板上 stopPropagation）不应关闭
    fireEvent.click(screen.getByRole('heading', { name: '新建项目' }));
    expect(screen.getByRole('heading', { name: '新建项目' })).toBeInTheDocument();

    // 点遮罩空白处关闭
    fireEvent.click(screen.getByTestId('new-project-backdrop'));
    expect(screen.queryByRole('heading', { name: '新建项目' })).not.toBeInTheDocument();
  });

  it('displays an error message when project creation fails', async () => {
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('创建项目失败'));

    render(<NewProjectDialog onCreated={() => {}} />);

    openDialog();
    fireEvent.change(getPrompt(), { target: { value: '失败的项目' } });
    fireEvent.click(screen.getByTestId('new-project-submit'));

    expect(await screen.findByText('创建项目失败')).toBeInTheDocument();
  });
});
