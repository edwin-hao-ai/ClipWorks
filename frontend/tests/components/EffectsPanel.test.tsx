import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { EffectsPanel } from '@/components/project/EffectsPanel';

const baseScenes = {
  scenes: [
    { start: 0, duration: 5, description: '', visual: '', text: '开场', visual_type: 'text' as const, shot: '', transition: 'fade' as const, lower_third: '', required_assets: [] },
  ],
};

describe('EffectsPanel', () => {
  it('selects a style preset and sets aria-pressed', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<EffectsPanel value={{ effects: [] }} scenes={baseScenes} onChange={onChange} />);

    const presetButton = screen.getByRole('button', { name: '极简高级' });
    expect(presetButton).toHaveAttribute('aria-pressed', 'false');

    await user.click(presetButton);

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({
      effects: [
        {
          scene_index: 0,
          visual_style: '极简高级',
          animation_keywords: [],
          generate_image: false,
          generate_image_prompt: '',
        },
      ],
    });

    // Re-render with selected style to assert aria-pressed reflects state.
    render(<EffectsPanel value={onChange.mock.calls[0][0]} scenes={baseScenes} onChange={vi.fn()} />);
    const pressedButtons = screen.getAllByRole('button', { name: '极简高级' }).filter((b) => b.getAttribute('aria-pressed') === 'true');
    expect(pressedButtons).toHaveLength(1);
  });

  it('updates animation keywords from comma-separated input', () => {
    const onChange = vi.fn();
    render(<EffectsPanel value={{ effects: [] }} scenes={baseScenes} onChange={onChange} />);

    const keywordsInput = screen.getByLabelText(/动画关键词/i);
    fireEvent.change(keywordsInput, { target: { value: '淡入, 缩放' } });

    expect(onChange).toHaveBeenLastCalledWith({
      effects: [
        {
          scene_index: 0,
          visual_style: '',
          animation_keywords: ['淡入', '缩放'],
          generate_image: false,
          generate_image_prompt: '',
        },
      ],
    });
  });

  it('toggles generate image and reveals the prompt input', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<EffectsPanel value={{ effects: [] }} scenes={baseScenes} onChange={onChange} />);

    const toggle = screen.getByLabelText(/需要生成图/i);
    await user.click(toggle);

    expect(onChange).toHaveBeenLastCalledWith({
      effects: [
        {
          scene_index: 0,
          visual_style: '',
          animation_keywords: [],
          generate_image: true,
          generate_image_prompt: '',
        },
      ],
    });

    // Re-render with generate_image enabled to reveal prompt input.
    render(<EffectsPanel value={onChange.mock.calls[0][0]} scenes={baseScenes} onChange={vi.fn()} />);
    expect(screen.getAllByLabelText(/生成图 Prompt/i).length).toBeGreaterThanOrEqual(1);
  });

  it('preserves existing effect entries when filling missing indices', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const scenes = {
      scenes: [
        { start: 0, duration: 5, description: '', visual: '', text: 'A', visual_type: 'text' as const, shot: '', transition: 'fade' as const, lower_third: '', required_assets: [] },
        { start: 5, duration: 5, description: '', visual: '', text: 'B', visual_type: 'text' as const, shot: '', transition: 'fade' as const, lower_third: '', required_assets: [] },
      ],
    };
    const effects = {
      effects: [
        {
          scene_index: 0,
          visual_style: '深蓝科技粒子',
          animation_keywords: ['粒子'],
          generate_image: false,
          generate_image_prompt: '',
        },
      ],
    };

    render(<EffectsPanel value={effects} scenes={scenes} onChange={onChange} />);

    // Interact with the second scene to verify the first effect is preserved.
    const presetButtons = screen.getAllByRole('button', { name: '赛博霓虹' });
    expect(presetButtons).toHaveLength(2);
    await user.click(presetButtons[1]);

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({
      effects: [
        effects.effects[0],
        {
          scene_index: 1,
          visual_style: '赛博霓虹',
          animation_keywords: [],
          generate_image: false,
          generate_image_prompt: '',
        },
      ],
    });
  });
});
