import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    // 仅收集单元/集成测试，排除 e2e 与其他无关目录
    include: [
      'src/**/*.test.ts',
      'src/**/*.test.tsx',
      'src/test/integration/**/*.test.ts',
      'src/test/integration/**/*.test.tsx',
    ],
    exclude: [
      'src/test/e2e/**',
      'e2e/**',
      'playwright/**',
      // 硬隔离三方与构建产物
      'node_modules/**',
      'dist/**',
      '.turbo/**',
      'coverage/**',
    ],
  },
});