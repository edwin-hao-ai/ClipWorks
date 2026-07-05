import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SceneCard } from '@/components/project/SceneCard';
import { Scene } from '@/lib/types';

const mockScene: Scene = {
  id: 'scene-1',
  index: 0,
  name: '产品痛点引入',
  description: '用一个问题引出用户痛点',
  start_time: 0,
  duration: 8,
  thumbnail: undefined,
  text_content: '还在手动做视频？',
  visual_content: '产品首页截图',
};

describe('SceneCard', () => {
  it('renders scene name and duration', () => {
    render(<SceneCard scene={mockScene} isSelected={false} onClick={() => {}} />);
    expect(screen.getByText('产品痛点引入')).toBeInTheDocument();
    expect(screen.getByText('0:00 - 0:08')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<SceneCard scene={mockScene} isSelected={false} onClick={onClick} />);
    fireEvent.click(screen.getByText('产品痛点引入'));
    expect(onClick).toHaveBeenCalledWith('scene-1');
  });
});
