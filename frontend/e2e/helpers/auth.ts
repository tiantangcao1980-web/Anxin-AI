import { expect, type Page } from '@playwright/test'
import { installApiMocks, seedAuthState } from './session'

export async function loginAsAdmin(page: Page) {
  await installApiMocks(page)
  await seedAuthState(page, {
    role: 'admin',
    userId: 'e2e-admin',
    name: 'E2E Admin',
    email: 'admin@anxinfawu.com',
  })
  await page.goto('/chat')
  await expect(page.getByText('你好，有什么可以帮您？')).toBeVisible({ timeout: 15000 })
}
