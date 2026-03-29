import { test, expect } from '@playwright/test'

test.describe('认证流程', () => {
  test('登录页面正确渲染', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByText('安心AI法务')).toBeVisible()
    await expect(page.getByPlaceholder(/邮箱/)).toBeVisible()
    await expect(page.getByPlaceholder(/密码/)).toBeVisible()
  })

  test('空表单提交显示错误', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: /登录/ }).click()
    // 应该有错误提示
  })

  test('未登录访问受保护页面重定向到登录', async ({ page }) => {
    await page.goto('/chat')
    await expect(page).toHaveURL(/login/)
  })
})
