import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';

describe('PreviewPlayer', () => {
  it('shows placeholder when no videoUrl', () => {
    render(<PreviewPlayer />);
    expect(screen.getByText('视频将在这里预览')).toBeInTheDocument();
  });

  it('renders video when videoUrl provided', () => {
    render(<PreviewPlayer videoUrl="/api/static/sample.mp4" format="16:9" />);
    expect(screen.getByRole('button', { name: /播放/ })).toBeInTheDocument();
  });
});
