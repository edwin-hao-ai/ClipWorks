import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ScenesPanel } from '@/components/project/ScenesPanel';

const baseScenes = {
  scenes: [
    { start: 0, duration: 5, description: '', visual: '', text: '开场', visual_type: 'text' as const, shot: '', transition: 'fade' as const, lower_third: '', required_assets: [] },
    { start: 10, duration: 3, description: '', visual: '', text: '中段', visual_type: 'text' as const, shot: '', transition: 'fade' as const, lower_third: '', required_assets: [] },
  ],
};

describe('ScenesPanel', () => {
  it('renders existing scenes', () => {
    render(<ScenesPanel value={baseScenes} onChange={vi.fn()} />);
    expect(screen.getByDisplayValue('开场')).toBeInTheDocument();
    expect(screen.getByDisplayValue('中段')).toBeInTheDocument();
  });

  it('adds a new scene whose start is the maximum scene end', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ScenesPanel value={baseScenes} onChange={onChange} />);

    await user.click(screen.getByRole('button', { name: /添加场景/i }));

    expect(onChange).toHaveBeenCalledTimes(1);
    const payload = onChange.mock.calls[0][0];
    expect(payload.scenes).toHaveLength(3);
    expect(payload.scenes[2].start).toBe(13);
    expect(payload.scenes[2].duration).toBe(5);
  });

  it('removes a scene and calls onChange with the correct payload', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ScenesPanel value={baseScenes} onChange={onChange} />);

    const removeButtons = screen.getAllByRole('button', { name: /删除场景/i });
    await user.click(removeButtons[0]);

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({
      scenes: [baseScenes.scenes[1]],
    });
  });

  it('updates a scene field and calls onChange with the correct payload', () => {
    const onChange = vi.fn();
    render(<ScenesPanel value={baseScenes} onChange={onChange} />);

    const textInput = screen.getByDisplayValue('开场');
    fireEvent.change(textInput, { target: { value: '新开场' } });

    expect(onChange).toHaveBeenLastCalledWith({
      scenes: [
        { ...baseScenes.scenes[0], text: '新开场' },
        baseScenes.scenes[1],
      ],
    });
  });
});
