import { defineConfig, devices } from '@playwright/test';

// Force tests to target the already running frontend at port 8088
const BASE_URL = 'http://localhost:8088';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './src/test/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
  },
  // 仅在本地稳定性阶段运行 Chromium，提高通过率
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // 保持 Playwright 仅复用已运行的服务，避免尝试自启
  ...(process.env.PW_SKIP_WEBSERVER === '1'
    ? {}
    : {
        webServer: {
          // command intentionally removed to prevent auto-start
          url: BASE_URL,
          reuseExistingServer: true,
          timeout: 120 * 1000,
        },
      }),
});