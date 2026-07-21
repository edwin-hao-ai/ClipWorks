import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Sidebar 现在挂载 NewProjectDialog，后者使用 useRouter；全局 mock 避免每个页面测试重复声明。
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn(), back: vi.fn() }),
  usePathname: () => '/',
}));
