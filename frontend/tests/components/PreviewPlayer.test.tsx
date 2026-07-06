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

  it('renders video when outputUrl is provided', () => {
    render(
      <PreviewPlayer
        outputUrl="/api/static/output.mp4"
        htmlOutputUrl="/api/static/output/index.html"
      />
    );
    const video = document.querySelector('video');
    expect(video).toBeInTheDocument();
    expect(video?.getAttribute('src')).toBe('/api/static/output.mp4');
  });

  it('renders iframe when only htmlOutputUrl is provided', () => {
    render(<PreviewPlayer htmlOutputUrl="/api/static/output/index.html" />);
    const iframe = document.querySelector('iframe');
    expect(iframe).toBeInTheDocument();
    expect(iframe?.getAttribute('src')).toBe('/api/static/output/index.html');
  });

  it('applies aspect-ratio class based on format', () => {
    const { container, rerender } = render(
      <PreviewPlayer videoUrl="/api/static/sample.mp4" format="9:16" />
    );
    expect(
      container.querySelector('[class*="aspect-[9/16]"]')
    ).toBeInTheDocument();

    rerender(<PreviewPlayer videoUrl="/api/static/sample.mp4" format="1:1" />);
    expect(container.querySelector('.aspect-square')).toBeInTheDocument();
  });
});
