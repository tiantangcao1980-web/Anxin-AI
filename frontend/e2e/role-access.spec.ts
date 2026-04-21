import { expect, test, type TestInfo } from '@playwright/test'

import { installApiMocks, seedAuthState } from './helpers/session'

test.describe('多角色访问控制（桌面端）', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await installApiMocks(page)
  })

  test('企业用户可见找律师入口但不可见案源管理', async ({ page }) => {
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })

    await page.goto('/cases')

    // /cases → /case-center?tab=cases 的兼容重定向，允许任一落点
    await expect(page).toHaveURL(/(case-center|\/cases)/)
    // 侧栏「律师精英」对应 /find-lawyer 模块入口
    await expect(page.getByRole('button', { name: '律师精英' })).toBeVisible()
    await expect(page.getByRole('button', { name: '案源管理' })).toHaveCount(0)
  })

  test('非管理员访问后台会被重定向到对话页', async ({ page }) => {
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })

    await page.goto('/admin/users')

    await expect(page).toHaveURL(/\/chat$/)
  })

  test('过期 token 访问受保护页面会跳回登录页', async ({ page }) => {
    await seedAuthState(page, {
      role: 'admin',
      name: 'Admin User',
      email: 'admin@example.com',
      expired: true,
    })

    await page.goto('/contracts')

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByPlaceholder('请输入邮箱地址')).toBeVisible()
  })
})

test.describe('多角色访问控制（移动端）', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name !== 'mobile', 'mobile only')
    await installApiMocks(page)
  })

  test('企业用户在协作页可见找律师但不可见案源管理', async ({ page }) => {
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })

    await page.goto('/cases')

    // /cases → /case-center?tab=cases 的兼容重定向
    await expect(page).toHaveURL(/(case-center|\/cases)/)
    // 侧栏「律师精英」对应 /find-lawyer 模块入口
    await expect(page.getByRole('button', { name: '律师精英' })).toBeVisible()
    await expect(page.getByRole('button', { name: '案源管理' })).toHaveCount(0)
  })

  test('非管理员在"我的"菜单中看不到后台管理入口', async ({ page }) => {
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })

    await page.goto('/chat')
    // 移动端底部导航将设置入口命名为"我的"
    await page.getByRole('navigation').getByRole('button', { name: '我的' }).click()

    await expect(page.getByRole('button', { name: '后台管理' })).toHaveCount(0)
  })

  test('管理员在"我的"菜单中可见后台管理入口', async ({ page }) => {
    await seedAuthState(page, {
      role: 'admin',
      name: 'Admin User',
      email: 'admin@example.com',
    })

    await page.goto('/chat')
    await page.getByRole('navigation').getByRole('button', { name: '我的' }).click()

    await expect(page.getByRole('button', { name: '后台管理' })).toBeVisible()
  })
})
