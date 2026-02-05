import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const authFile = join(__dirname, 'e2e/.auth/user.json');
const isDocker = process.env.E2E_DOCKER === '1' || existsSync('/.dockerenv');
const defaultBaseURL = process.env.SKIP_WEBSERVER && isDocker ? 'http://frontend:5173' : 'http://localhost:5173';
const baseURL = process.env.BASE_URL || defaultBaseURL;
const proxyTarget = process.env.PROXY_TARGET || (isDocker ? 'http://web:8000' : 'http://localhost:8002');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 4,
  reporter: 'list',
  timeout: 30000,
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    // Setup project - faz login e salva estado
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    // Testes que requerem autenticação
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: authFile,
      },
      dependencies: ['setup'],
      testIgnore: [/.*\.setup\.ts/, /checklist\/.*/],
    },
    // Testes do checklist (não requerem autenticação)
    {
      name: 'checklist',
      testDir: './e2e/checklist',
      use: {
        ...devices['Desktop Chrome'],
      },
      // Sem dependência de setup - não precisa de auth
    },
  ],
  webServer: process.env.SKIP_WEBSERVER ? undefined : {
    command: 'npm run dev',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    env: {
      ...process.env,
      PROXY_TARGET: proxyTarget,
      // For E2E, force relative API base to use Vite proxy (avoid localhost:8002 in Docker)
      VITE_API_URL: '/api',
    },
  },
});
