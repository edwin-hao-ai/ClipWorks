import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { WorkflowStatusBar } from '@/components/project/WorkflowStatusBar';

describe('WorkflowStatusBar', () => {
  it('highlights current step', () => {
    render(<WorkflowStatusBar currentStep="script" />);
    expect(screen.getByText('脚本')).toHaveAttribute('aria-current', 'step');
  });
});
