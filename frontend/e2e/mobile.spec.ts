import { test, expect } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'

// 使用移动端视口尺寸（无需绑定特定浏览器引擎）
test.use({ viewport: { width: 375, height: 812 } })

test.describe('移动端适配', () => {
  test('底部 Tab 栏显示', async ({ page }) => {
    await loginAsAdmin(page)
    const bottomNav = page.getByRole('navigation')
    await expect(bottomNav.getByRole('button', { name: 'AI法务' })).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: '智能协作' })).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: '智能调查' })).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: '法律智库' })).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: '更多' })).toBeVisible()
  })

  test('点击智能协作 Tab 跳转', async ({ page }) => {
    await loginAsAdmin(page)
    await page.getByRole('button', { name: '智能协作' }).last().click()
    await page.waitForURL(/cases/)
  })

  test('顶部二级导航在协作页显示', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/cases')
    await expect(page.getByText('案件管理').first()).toBeVisible()
  })
})
