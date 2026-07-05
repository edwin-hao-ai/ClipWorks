import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SceneCards } from '@/components/project/SceneCards';
import { Scene } from '@/lib/types';

const scenes: Scene[] = [
  { id: 's1', index: 0, name: '开场', start_time: 0, duration: 5 },
  { id: 's2', index: 1, name: '正文', start_time: 5, duration: 10 },
];

describe('SceneCards', () => {
  it('renders scene list', () => {
    render(<SceneCards scenes={scenes} onSelect={() => {}} />);
    expect(screen.getByText('开场')).toBeInTheDocument();
    expect(screen.getByText('正文')).toBeInTheDocument();
  });

  it('calls onSelect when scene clicked', () => {
    const onSelect = vi.fn();
    render(<SceneCards scenes={scenes} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('正文'));
    expect(onSelect).toHaveBeenCalledWith('s2');
  });
});
