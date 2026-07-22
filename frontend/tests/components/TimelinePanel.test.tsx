import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { TimelinePanel } from '@/components/project/TimelinePanel';
import { Composition } from '@/lib/types';

function makeComposition(overrides: Partial<Composition> = {}): Composition {
  return {
    id: 'c1',
    project_id: 'p1',
    width: 1920,
    height: 1080,
    duration: 10,
    fps: 30,
    metadata: {},
    tracks: [
      {
        id: 't1',
        type: 'video',
        index: 0,
        name: 'Main',
        clips: [
          { id: 'clip-1', asset_id: 'a1', start_time: 0, duration: 5 },
        ],
      },
      {
        id: 't2',
        type: 'text',
        index: 1,
        name: 'Titles',
        clips: [
          { id: 'clip-2', text_content: 'Hello', start_time: 0, duration: 5 },
        ],
      },
    ],
    ...overrides,
  };
}

describe('TimelinePanel', () => {
  it('renders track labels and clip content', () => {
    render(<TimelinePanel composition={makeComposition()} />);
    expect(screen.getByText('Timeline')).toBeInTheDocument();
    expect(screen.getByText('video Track')).toBeInTheDocument();
    expect(screen.getByText('text Track')).toBeInTheDocument();
    expect(screen.getByText('a1')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('renders link to advanced editor using project_id', () => {
    render(<TimelinePanel composition={makeComposition()} />);
    const link = screen.getByText('打开高级编辑器 →');
    expect(link).toHaveAttribute('href', '/projects/p1/editor');
  });

  it('collapses and expands', () => {
    render(<TimelinePanel composition={makeComposition()} />);
    const toggle = screen.getByText('→');
    fireEvent.click(toggle);
    expect(screen.queryByText('Timeline')).not.toBeInTheDocument();
    expect(screen.getByText('←')).toBeInTheDocument();
    fireEvent.click(screen.getByText('←'));
    expect(screen.getByText('Timeline')).toBeInTheDocument();
  });

  it('returns null when composition is missing', () => {
    const { container } = render(<TimelinePanel composition={null} />);
    expect(container.firstChild).toBeNull();
  });
});
