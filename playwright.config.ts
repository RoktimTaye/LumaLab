import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: { baseURL: 'http://localhost:4173', channel: 'chrome', trace: 'retain-on-failure' },
  webServer: { command: 'npm run dev -- --host 0.0.0.0 --port 4173', url: 'http://localhost:4173', reuseExistingServer: true },
})
