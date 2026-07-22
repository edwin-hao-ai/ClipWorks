import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { IntentCard } from '@/components/project/IntentCard';

describe('IntentCard', () => {
  it('renders all intent fields', () => {
    render(
      <IntentCard
        intent={{
          goal: '为降噪耳机制作种草短视频',
          duration: 15,
          format: '9:16 竖屏',
          style: '活泼、面向年轻人',
        }}
        onConfirm={() => {}}
        onEdit={() => {}}
      />
    );

    expect(screen.getByText('AI 理解的需求')).toBeInTheDocument();
    expect(screen.getByText(/目标：为降噪耳机制作种草短视频/)).toBeInTheDocument();
    expect(screen.getByText(/时长：15 秒/)).toBeInTheDocument();
    expect(screen.getByText(/画幅：9:16 竖屏/)).toBeInTheDocument();
    expect(screen.getByText(/风格：活泼、面向年轻人/)).toBeInTheDocument();
  });

  it('skips missing fields', () => {
    render(<IntentCard intent={{ goal: '测试' }} onConfirm={() => {}} onEdit={() => {}} />);
    expect(screen.getByText(/目标：测试/)).toBeInTheDocument();
    expect(screen.queryByText(/时长/)).not.toBeInTheDocument();
    expect(screen.queryByText(/画幅/)).not.toBeInTheDocument();
    expect(screen.queryByText(/风格/)).not.toBeInTheDocument();
  });

  it('calls onConfirm when confirm button clicked', () => {
    const onConfirm = vi.fn();
    render(<IntentCard intent={{}} onConfirm={onConfirm} onEdit={() => {}} />);
    fireEvent.click(screen.getByText('确认'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onEdit when edit button clicked', () => {
    const onEdit = vi.fn();
    render(<IntentCard intent={{}} onConfirm={() => {}} onEdit={onEdit} />);
    fireEvent.click(screen.getByText('修改'));
    expect(onEdit).toHaveBeenCalledWith('');
  });
});
