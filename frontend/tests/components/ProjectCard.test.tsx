import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProjectCard } from '@/components/project/ProjectCard';
import { Project } from '@/lib/types';

const mockProject: Project = {
  id: 'p1',
  title: 'Test Project',
  source_url: 'https://example.com',
  source_type: 'url',
  status: 'draft',
  target_format: '16:9',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('ProjectCard', () => {
  it('renders project title', () => {
    render(<ProjectCard project={mockProject} onDelete={() => {}} />);
    expect(screen.getByText('Test Project')).toBeInTheDocument();
  });

  it('calls onDelete when delete button clicked', () => {
    const onDelete = vi.fn();
    render(<ProjectCard project={mockProject} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onDelete).toHaveBeenCalledWith('p1');
  });
});
