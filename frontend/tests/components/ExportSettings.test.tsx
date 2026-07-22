import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ExportSettings } from '@/components/project/ExportSettings';
import { api } from '@/lib/api';
import { Project } from '@/lib/types';

vi.mock('@/lib/api', () => ({
  api: {
    put: vi.fn(),
    post: vi.fn(),
  },
}));

const mockProject: Project = {
  id: 'project-1',
  title: '测试项目',
  source_type: 'url',
  status: 'ready',
  target_format: '16:9',
  target_duration: 30,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const renderOpen = (props?: { onStart?: () => void; onClose?: () => void }) =>
  render(
    <ExportSettings
      project={mockProject}
      open={true}
      onClose={props?.onClose ?? vi.fn()}
      onStart={props?.onStart ?? vi.fn()}
    />
  );

describe('ExportSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a centered modal with export options', () => {
    renderOpen();

    expect(screen.getByRole('heading', { name: '导出设置' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '横屏 16:9' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '竖屏 9:16' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '方形 1:1' })).toBeInTheDocument();
    expect(screen.getByLabelText('目标时长（秒）')).toHaveValue(30);
    expect(screen.getByRole('button', { name: '高清 1080p / 推荐' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '本地下载' })).toBeInTheDocument();
  });

  it('closes on Escape key and backdrop click', () => {
    const onClose = vi.fn();
    renderOpen({ onClose });

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);

    // 点击面板内部不关闭
    fireEvent.click(screen.getByRole('heading', { name: '导出设置' }));
    expect(onClose).toHaveBeenCalledTimes(1);

    // 点击遮罩空白处关闭
    fireEvent.click(screen.getByRole('dialog'));
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it('updates project settings then triggers render on submit', async () => {
    const onStart = vi.fn();
    (api.put as ReturnType<typeof vi.fn>).mockResolvedValue({ ...mockProject, target_format: '9:16', target_duration: 45 });
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ job_id: 'job-1', status: 'queued' });

    renderOpen({ onStart });

    fireEvent.click(screen.getByRole('button', { name: '竖屏 9:16' }));
    fireEvent.change(screen.getByLabelText('目标时长（秒）'), { target: { value: '45' } });
    fireEvent.click(screen.getByRole('button', { name: '超清 2K+ / 较慢' }));

    fireEvent.click(screen.getByRole('button', { name: '开始导出' }));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith('/projects/project-1', {
        target_format: '9:16',
        target_duration: 45,
      });
      expect(api.post).toHaveBeenCalledWith('/projects/project-1/renders/generate', { quality: 'ultra' });
      expect(onStart).toHaveBeenCalled();
    });
  });

  it('does not send location to the backend', async () => {
    (api.put as ReturnType<typeof vi.fn>).mockResolvedValue(mockProject);
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ job_id: 'job-1', status: 'queued' });

    renderOpen();

    // 切换保存位置为云端（纯 UI 状态）
    fireEvent.click(screen.getByRole('button', { name: '云端存储' }));
    fireEvent.click(screen.getByRole('button', { name: '开始导出' }));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith('/projects/project-1', expect.objectContaining({
        target_format: '16:9',
        target_duration: 30,
      }));
      expect(api.post).toHaveBeenCalledWith('/projects/project-1/renders/generate', { quality: 'high' });
      // location 不应出现在任何请求中
      expect(api.put).not.toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ location: expect.anything() })
      );
      expect(api.post).not.toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ location: expect.anything() })
      );
    });
  });

  it('shows inline validation error and disables submit for invalid duration', async () => {
    renderOpen();

    fireEvent.change(screen.getByLabelText('目标时长（秒）'), { target: { value: '400' } });

    expect(screen.getByText('目标时长需在 5–300 秒之间')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始导出' })).toBeDisabled();
    expect(api.put).not.toHaveBeenCalled();
  });

  it('shows inline validation error and disables submit when duration is empty', async () => {
    renderOpen();

    fireEvent.change(screen.getByLabelText('目标时长（秒）'), { target: { value: '' } });

    expect(screen.getByLabelText('目标时长（秒）')).toHaveValue(null);
    expect(screen.getByText('目标时长需在 5–300 秒之间')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始导出' })).toBeDisabled();
    expect(api.put).not.toHaveBeenCalled();
  });

  it('shows error when render trigger fails', async () => {
    (api.put as ReturnType<typeof vi.fn>).mockResolvedValue(mockProject);
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('渲染队列已满'));

    renderOpen();

    fireEvent.click(screen.getByRole('button', { name: '开始导出' }));

    const errorEl = await screen.findByTestId('export-error');
    expect(errorEl).toHaveTextContent('渲染队列已满');
  });

  it('shows credits error for 402 response', async () => {
    (api.put as ReturnType<typeof vi.fn>).mockResolvedValue(mockProject);
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('API error 402: credits exhausted'));

    renderOpen();

    fireEvent.click(screen.getByRole('button', { name: '开始导出' }));

    const errorEl = await screen.findByTestId('export-error');
    expect(errorEl).toHaveTextContent('额度不足：前往计费页切换套餐即可补充额度（演示环境）。');
  });
});
