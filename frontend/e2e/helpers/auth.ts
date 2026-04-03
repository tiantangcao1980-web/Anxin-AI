import { expect, type Page } from '@playwright/test'

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@anxinfawu.com'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'admin888'

export async function loginAsAdmin(page: Page) {
  await page.goto('/login')

  await page.getByPlaceholder('请输入邮箱地址').fill(ADMIN_EMAIL)
  await page.getByPlaceholder('请输入密码').fill(ADMIN_PASSWORD)
  await page.locator('form').getByRole('button', { name: '登录' }).click()

  await page.waitForURL('**/chat', { timeout: 15000 })
  await expect(page.getByText('你好，有什么可以帮您？')).toBeVisible({ timeout: 15000 })
}
