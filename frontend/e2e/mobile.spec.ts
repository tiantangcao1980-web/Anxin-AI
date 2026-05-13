import { test, expect } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'

// 使用移动端视口尺寸（无需绑定特定浏览器引擎）
test.use({ viewport: { width: 375, height: 812 } })

test.describe('移动端适配', () => {
  test('底部 Tab 栏显示', async ({ page }) => {
    await loginAsAdmin(page)
    // 底部导航固定 5 项：AI 智能助手 / 协作 / 消息 / 智库 / 我的
    // （与 src/components/mobile/MobileNavBar.tsx 的 NAV_ITEMS 保持同步）
    const bottomNav = page.getByRole('navigation')
    await expect(bottomNav.getByRole('button', { name: 'AI 智能助手' })).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: '协作' })).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: '消息' })).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: '智库' })).toBeVisible()
    await expect(bottomNav.getByRole('button', { name: '我的' })).toBeVisible()
  })

  test('点击协作 Tab 跳转到案件入口', async ({ page }) => {
    await loginAsAdmin(page)
    // /cases 是旧路由，会被重定向到 /case-center?tab=cases
    await page.getByRole('button', { name: '协作' }).last().click()
    await page.waitForURL(/case-center|cases/)
  })

  test('顶部二级导航在协作页显示', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/case-center')
    await expect(page.getByText('我的案件').first()).toBeVisible()
  })
})
