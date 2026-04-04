import { test, expect } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'

test.describe('导航结构', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile navigation has dedicated coverage in mobile.spec.ts')
    await loginAsAdmin(page)
  })

  test('顶部导航栏显示四大业务域', async ({ page }) => {
    const header = page.getByRole('banner')
    await expect(header.getByRole('button', { name: 'AI法务' })).toBeVisible()
    await expect(header.getByRole('button', { name: '智能协作' })).toBeVisible()
    await expect(header.getByRole('button', { name: '智能调查' })).toBeVisible()
    await expect(header.getByRole('button', { name: '法律智库' })).toBeVisible()
  })

  test('点击智能协作显示侧边栏', async ({ page }) => {
    await page.getByRole('banner').getByRole('button', { name: '智能协作' }).click()
    await page.waitForURL(/\/cases/)
    await expect(page.getByRole('main').getByRole('heading', { name: '案件管理' })).toBeVisible()
  })

  test('案件管理页面加载', async ({ page }) => {
    await page.goto('/cases')
    await expect(page.getByRole('main').getByRole('heading', { name: '案件管理' })).toBeVisible()
    await expect(page.getByRole('button', { name: '新建案件' })).toBeVisible()
  })

  test('合同管理页面加载', async ({ page }) => {
    await page.goto('/contracts')
    await expect(page.getByText('合同审查').first()).toBeVisible()
  })
})
