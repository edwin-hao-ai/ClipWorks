import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import LoginPage from '@/app/login/page';

describe('LoginPage', () => {
  it('renders login buttons', () => {
    render(<LoginPage />);
    expect(screen.getByText('使用 Google 登录')).toBeInTheDocument();
    expect(screen.getByText('使用 GitHub 登录')).toBeInTheDocument();
  });
});
