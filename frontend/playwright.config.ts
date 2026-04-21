import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  // 本地也保留 1 次 retry：并行浏览器调度偶尔让 50ms 级的时序测试抖动，
  // 一次 retry 足以区分「真实 bug」与「浏览器调度抖动」。
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['iPhone 14'] } },
  ],
  webServer: {
    command: 'npm run dev -- --port 3001',
    port: 3001,
    reuseExistingServer: !process.env.CI,
  },
})
