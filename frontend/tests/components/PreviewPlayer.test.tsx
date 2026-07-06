import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';

describe('PreviewPlayer', () => {
  it('shows placeholder when no videoUrl', () => {
    render(<PreviewPlayer />);
    expect(screen.getByText('暂无预览')).toBeInTheDocument();
  });

  it('renders video with download link when videoUrl provided', () => {
    render(<PreviewPlayer videoUrl="/api/static/sample.mp4" format="16:9" />);
    const video = document.querySelector('video');
    expect(video).toBeInTheDocument();
    expect(video?.getAttribute('src')).toBe('/api/static/sample.mp4');
    expect(screen.getByText('下载 MP4')).toBeInTheDocument();
  });
});
