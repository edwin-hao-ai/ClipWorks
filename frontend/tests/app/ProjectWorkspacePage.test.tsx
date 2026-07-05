import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import ProjectWorkspacePage from '@/app/projects/[id]/page';

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'test-id' }),
  usePathname: () => '/projects/test-id',
}));

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(() => Promise.reject(new Error('mock'))),
  },
}));

vi.mock('@/lib/demoData', () => ({
  DEMO_USER: {
    id: 'demo-user',
    name: 'Demo Creator',
    email: 'demo@clipworks.io',
  },
  getDemoProjectById: () => ({
    id: 'test-id',
    title: 'Demo Project',
    source_type: 'url',
    status: 'draft',
    target_format: '16:9',
    created_at: '',
    updated_at: '',
  }),
}));

describe('ProjectWorkspacePage', () => {
  it('renders project title', async () => {
    render(<ProjectWorkspacePage />);
    expect(await screen.findByText('Demo Project')).toBeInTheDocument();
  });
});
