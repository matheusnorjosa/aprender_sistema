/**
 * Playwright Configuration - Aprender Sistema v2
 *
 * E2E tests for Solicitação → Google Calendar workflow
 * Uses fake GCal client for testing without real API credentials
 *
 * Fase 2 - Plano DAT/GCal 2025-10-29
 */

import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'fs';

const isDocker = process.env.E2E_DOCKER === '1' || existsSync('/.dockerenv');
const defaultBaseURL = process.env.SKIP_WEBSERVER
  ? (isDocker ? 'http://frontend:5173' : 'http://localhost:5173')
  : 'http://localhost:5173';
const baseURL = process.env.BASE_URL || defaultBaseURL;
const proxyTarget = process.env.PROXY_TARGET || (isDocker ? 'http://web:8000' : 'http://localhost:8002');

/**
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',

  /* Run tests in files in parallel */
  fullyParallel: false, // Sequential for E2E (evita conflitos de dados)

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : 1,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: './playwright-report', open: 'never' }],
    ['list'],
    ['json', { outputFile: './test-results/results.json' }],
  ],

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'retain-on-failure',

    /* Timeout for each action (click, fill, etc) */
    actionTimeout: 10000,

    /* Navigation timeout */
    navigationTimeout: 30000,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // Uncomment for multi-browser testing
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  /* Run your local dev server before starting the tests */
  webServer: process.env.SKIP_WEBSERVER ? undefined : {
    command: 'cd ../../frontend && npm run dev',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120000, // 2 minutes for npm run dev to start
    stdout: 'pipe',
    stderr: 'pipe',
    env: {
      ...process.env,
      PROXY_TARGET: proxyTarget,
      // For E2E, force relative API base to use Vite proxy (avoid localhost:8002 in Docker)
      VITE_API_URL: '/api',
    },
  },

  /* Global timeout for each test */
  timeout: 60000, // 1 minute per test (E2E pode ser lento)

  /* Global setup/teardown */
  // globalSetup: require.resolve('./global-setup'),
  // globalTeardown: require.resolve('./global-teardown'),
});
