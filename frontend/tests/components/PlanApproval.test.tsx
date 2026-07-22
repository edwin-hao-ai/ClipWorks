import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PlanApproval } from '@/components/project/PlanApproval';
import { AgentPlan } from '@/lib/types';

const plan: AgentPlan = {
  title: '耳机种草方案',
  hook: '地铁噪音瞬间消失',
  format: '9:16',
  duration: 15,
  engine_hint: 'remotion',
  assets_needed: ['耳机产品图', '地铁场景图'],
  scenes: [
    { start: 0, duration: 3, description: '开场钩子', visual: 'metro', text: '静音世界' },
    { start: 3, duration: 4, description: '卖点 1', visual: 'product', text: '主动降噪' },
  ],
};

describe('PlanApproval', () => {
  it('renders plan metadata and scenes', () => {
    render(<PlanApproval plan={plan} onApprove={() => {}} onReject={() => {}} />);

    expect(screen.getByText('方案已就绪 · 待确认')).toBeInTheDocument();
    expect(screen.getByText('9:16 · 15s · 2 镜')).toBeInTheDocument();
    expect(screen.getByText('镜 1')).toBeInTheDocument();
    expect(screen.getByText('镜 2')).toBeInTheDocument();
    expect(screen.getByText(/开场钩子/)).toBeInTheDocument();
    expect(screen.getByText(/卖点 1/)).toBeInTheDocument();
    expect(screen.getByText('“静音世界”')).toBeInTheDocument();
  });

  it('calls onApprove when approve button clicked', () => {
    const onApprove = vi.fn();
    render(<PlanApproval plan={plan} onApprove={onApprove} onReject={() => {}} />);
    fireEvent.click(screen.getByText('确认生成'));
    expect(onApprove).toHaveBeenCalledTimes(1);
  });

  it('calls onReject when reject button clicked', () => {
    const onReject = vi.fn();
    render(<PlanApproval plan={plan} onApprove={() => {}} onReject={onReject} />);
    fireEvent.click(screen.getByText('再改改'));
    expect(onReject).toHaveBeenCalledTimes(1);
  });

  it('disables both buttons when loading', () => {
    render(<PlanApproval plan={plan} onApprove={() => {}} onReject={() => {}} loading />);
    expect(screen.getByText('确认生成')).toBeDisabled();
    expect(screen.getByText('再改改')).toBeDisabled();
  });
});
