import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { StoryboardStrip } from '@/components/project/StoryboardStrip';
import { Scene } from '@/lib/types';

const scenes: Scene[] = [
  { id: 's1', index: 0, name: '开场钩子', start_time: 0, duration: 3 },
  { id: 's2', index: 1, name: '卖点 1', start_time: 3, duration: 4 },
  { id: 's3', index: 2, name: 'CTA', start_time: 7, duration: 3 },
];

describe('StoryboardStrip', () => {
  it('renders scene thumbnails', () => {
    render(<StoryboardStrip scenes={scenes} currentIndex={0} onSelect={() => {}} />);

    expect(screen.getByText('镜 1')).toBeInTheDocument();
    expect(screen.getByText('镜 2')).toBeInTheDocument();
    expect(screen.getByText('镜 3')).toBeInTheDocument();
    expect(screen.getByText('开场钩子')).toBeInTheDocument();
    expect(screen.getByText('卖点 1')).toBeInTheDocument();
    expect(screen.getByText('CTA')).toBeInTheDocument();
  });

  it('highlights current scene', () => {
    render(<StoryboardStrip scenes={scenes} currentIndex={1} onSelect={() => {}} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons[1]).toHaveClass('border-brand-500');
    expect(buttons[0]).not.toHaveClass('border-brand-500');
  });

  it('calls onSelect with index when a scene is clicked', () => {
    const onSelect = vi.fn();
    render(<StoryboardStrip scenes={scenes} currentIndex={0} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('卖点 1'));
    expect(onSelect).toHaveBeenCalledWith(1);
  });

  it('renders empty strip gracefully', () => {
    render(<StoryboardStrip scenes={[]} currentIndex={0} onSelect={() => {}} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
