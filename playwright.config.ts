import { defineConfig, devices } from '@playwright/test';

/**
 * BASE_URL_API  -> the conduit-backend under test (default: local dev server)
 * BASE_URL_WEB  -> the conduit-frontend under test (default: local dev server)
 *
 * In CI these point at services started by the workflow (see .github/workflows/ci.yml).
 * Locally, start both apps yourself and export the URLs, or rely on the defaults below.
 */
const API_URL = process.env.BASE_URL_API || 'http://localhost:3000';
const WEB_URL = process.env.BASE_URL_WEB || 'http://localhost:4100';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  projects: [
    {
      name: 'api',
      testDir: './tests/api',
      use: {
        baseURL: API_URL,
      },
    },
    {
      name: 'e2e-chromium',
      testDir: './tests/e2e',
      use: {
        baseURL: WEB_URL,
        ...devices['Desktop Chrome'],
      },
    },
  ],
});
