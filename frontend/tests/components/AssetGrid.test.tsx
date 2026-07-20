import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AssetGrid } from '@/components/assets/AssetGrid';
import { MediaAsset } from '@/lib/types';

const mockAssets: MediaAsset[] = [
  {
    id: 'a1',
    project_id: 'p1',
    type: 'image',
    source: 'upload',
    original_url: 'photo.jpg',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'a2',
    project_id: 'p1',
    type: 'video',
    source: 'pexels',
    original_url: 'video.mp4',
    created_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 'a3',
    project_id: 'p1',
    type: 'audio',
    source: 'upload',
    local_path: '/assets/audio.ogg',
    created_at: '2024-01-03T00:00:00Z',
  },
];

describe('AssetGrid', () => {
  it('renders all asset cards with labels', () => {
    render(<AssetGrid assets={mockAssets} />);

    expect(screen.getByText('photo.jpg')).toBeInTheDocument();
    expect(screen.getByText('video.mp4')).toBeInTheDocument();
    expect(screen.getByText('audio.ogg')).toBeInTheDocument();
    expect(screen.getByText('图片')).toBeInTheDocument();
    expect(screen.getByText('视频')).toBeInTheDocument();
    expect(screen.getByText('音频')).toBeInTheDocument();
  });

  it('renders nothing when assets is empty', () => {
    const { container } = render(<AssetGrid assets={[]} />);
    expect(container.firstChild).toBeEmptyDOMElement();
  });
});
