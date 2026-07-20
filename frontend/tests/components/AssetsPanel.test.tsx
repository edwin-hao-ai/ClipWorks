import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { AssetsPanel } from '@/components/project/AssetsPanel';

const baseAssets = {
  needed: [
    { type: 'image' as const, description: '主视觉图', query: 'hero', count: 2 },
  ],
};

describe('AssetsPanel', () => {
  it('renders existing asset items', () => {
    render(<AssetsPanel value={baseAssets} onChange={vi.fn()} />);
    expect(screen.getByDisplayValue('主视觉图')).toBeInTheDocument();
    expect(screen.getByDisplayValue('hero')).toBeInTheDocument();
    expect(screen.getByDisplayValue('2')).toBeInTheDocument();
  });

  it('adds a new asset and calls onChange with the correct payload', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AssetsPanel value={baseAssets} onChange={onChange} />);

    await user.click(screen.getByRole('button', { name: /添加素材/i }));

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({
      needed: [
        ...baseAssets.needed,
        { type: 'image', description: '', query: '', count: 1 },
      ],
    });
  });

  it('removes an asset and calls onChange with the correct payload', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AssetsPanel value={baseAssets} onChange={onChange} />);

    await user.click(screen.getByRole('button', { name: /删除素材/i }));

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ needed: [] });
  });

  it('updates an asset field and calls onChange with the correct payload', () => {
    const onChange = vi.fn();
    render(<AssetsPanel value={baseAssets} onChange={onChange} />);

    const descInput = screen.getByDisplayValue('主视觉图');
    fireEvent.change(descInput, { target: { value: '新描述' } });

    expect(onChange).toHaveBeenLastCalledWith({
      needed: [{ type: 'image', description: '新描述', query: 'hero', count: 2 }],
    });
  });

  it('clamps count to at least 1', () => {
    const onChange = vi.fn();
    const { rerender } = render(<AssetsPanel value={baseAssets} onChange={onChange} />);

    const countInput = screen.getByDisplayValue('2');
    fireEvent.change(countInput, { target: { value: '0' } });

    expect(onChange).toHaveBeenLastCalledWith({
      needed: [{ type: 'image', description: '主视觉图', query: 'hero', count: 1 }],
    });

    // Re-render with count 1 and confirm it stays at 1 rather than falling to 0.
    rerender(<AssetsPanel value={{ needed: [{ type: 'image', description: '主视觉图', query: 'hero', count: 1 }] }} onChange={onChange} />);
    const updatedCountInput = screen.getByDisplayValue('1');
    fireEvent.change(updatedCountInput, { target: { value: '' } });

    expect(onChange).toHaveBeenLastCalledWith({
      needed: [{ type: 'image', description: '主视觉图', query: 'hero', count: 1 }],
    });
  });
});
