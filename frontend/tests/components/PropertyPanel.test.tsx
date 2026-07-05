import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PropertyPanel } from '@/components/project/PropertyPanel';
import { Project, Scene } from '@/lib/types';

const scenes: Scene[] = [
  { id: 's1', index: 0, name: '开场', start_time: 0, duration: 5 },
  { id: 's2', index: 1, name: '正文', start_time: 5, duration: 10 },
];

const mockProject: Project = {
  id: 'p1',
  title: 'Test',
  source_type: 'url',
  status: 'draft',
  target_format: '16:9',
  target_duration: 30,
  created_at: '',
  updated_at: '',
};

describe('PropertyPanel', () => {
  it('renders project title', () => {
    render(<PropertyPanel project={mockProject} />);
    expect(screen.getByDisplayValue('Test')).toBeInTheDocument();
  });

  it('renders scene properties when scene selected', () => {
    render(<PropertyPanel project={mockProject} selectedScene={scenes[0]} />);
    expect(screen.getByText('场景属性')).toBeInTheDocument();
    expect(screen.getByDisplayValue('开场')).toBeInTheDocument();
  });
});
