import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';

const SAMPLE_HTML =
  '<!DOCTYPE html><html><head></head><body><div id="stage"><div class="scene scene-0">hi</div></div></body></html>';

describe('PreviewPlayer', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: () => Promise.resolve(SAMPLE_HTML),
      })
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

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

  it('renders iframe when only htmlOutputUrl is provided', async () => {
    render(<PreviewPlayer htmlOutputUrl="/api/static/output/index.html" />);
    const iframe = await waitFor(() => {
      const el = document.querySelector('iframe');
      if (!el) throw new Error('iframe not ready');
      return el;
    });
    // The HTML preview is rendered via srcdoc (fetched and patched so scenes
    // are visible and animations loop), not via a cross-origin src attribute.
    expect(iframe.getAttribute('srcdoc')).toContain('__replay');
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
