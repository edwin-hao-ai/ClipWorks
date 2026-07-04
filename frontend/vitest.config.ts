import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  // @ts-expect-error Plugin type mismatch between @vitejs/plugin-react (vite 7) and vitest/config (vite 5).
  // Keeping this avoids forcing a single Vite version and prevents an esbuild downgrade.
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
