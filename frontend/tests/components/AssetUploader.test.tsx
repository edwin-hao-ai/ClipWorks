import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AssetUploader } from '@/components/assets/AssetUploader';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    postForm: vi.fn(),
  },
}));

describe('AssetUploader', () => {
  it('renders upload button and uploads a selected file', async () => {
    const onUploaded = vi.fn();
    (api.postForm as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'asset-1',
      filename: 'cat.png',
    });

    const { container } = render(
      <AssetUploader projectId="project-1" onUploaded={onUploaded} />
    );

    expect(screen.getByRole('button', { name: /上传素材/i })).toBeInTheDocument();

    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['dummy'], 'cat.png', { type: 'image/png' });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(api.postForm).toHaveBeenCalledTimes(1);
      expect(api.postForm).toHaveBeenCalledWith(
        '/projects/project-1/assets/',
        expect.any(FormData)
      );
      expect(onUploaded).toHaveBeenCalledTimes(1);
    });
  });

  it('shows an error message when upload fails', async () => {
    const onUploaded = vi.fn();
    (api.postForm as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('上传失败')
    );

    const { container } = render(
      <AssetUploader projectId="project-1" onUploaded={onUploaded} />
    );

    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['dummy'], 'dog.mp4', { type: 'video/mp4' });

    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText('上传失败')).toBeInTheDocument();
    expect(onUploaded).not.toHaveBeenCalled();
  });
});
