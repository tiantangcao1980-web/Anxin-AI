import { expect, type Page } from '@playwright/test'
import { installApiMocks, type MockOptions, seedAuthState } from './session'

export async function loginAsAdmin(page: Page, options?: MockOptions) {
  await loginAsRole(page, 'admin', {
    ...options,
    auth: {
      role: 'admin',
      userId: 'e2e-admin',
      name: 'E2E Admin',
      email: 'admin@anxinai.com',
      ...options?.auth,
    },
  })
}

export async function loginAsRole(page: Page, role: string, options?: MockOptions) {
  const auth = {
    role,
    userId: options?.auth?.userId ?? `e2e-${role}`,
    name: options?.auth?.name ?? `E2E ${role}`,
    email: options?.auth?.email ?? `${role}@anxinai.com`,
    primary_client: options?.auth?.primary_client,
  }
  await installApiMocks(page, { ...options, auth })
  await seedAuthState(page, {
    role: auth.role,
    userId: auth.userId,
    name: auth.name,
    email: auth.email,
    primary_client: auth.primary_client,
  })
  await page.goto('/chat')
  await expect(page.getByText('你好，有什么可以帮您？')).toBeVisible({ timeout: 15000 })
}
