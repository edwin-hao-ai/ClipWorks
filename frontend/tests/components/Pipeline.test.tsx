import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Pipeline } from '@/components/project/Pipeline';

const steps = [
  { id: 'understand', label: '理解需求' },
  { id: 'analyze', label: '分析素材' },
  { id: 'script', label: '编写脚本' },
  { id: 'scenes', label: '生成场景' },
  { id: 'render', label: '渲染成片' },
];

describe('Pipeline', () => {
  it('renders all step labels', () => {
    render(<Pipeline steps={steps} currentStepIndex={2} />);
    steps.forEach((s) => {
      expect(screen.getByText(s.label)).toBeInTheDocument();
    });
  });

  it('shows current description when provided', () => {
    render(<Pipeline steps={steps} currentStepIndex={2} currentDescription="正在编写脚本..." />);
    expect(screen.getByText('正在编写脚本...')).toBeInTheDocument();
  });
});
