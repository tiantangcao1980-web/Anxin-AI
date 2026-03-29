import { test, expect, devices } from '@playwright/test'

test.describe('移动端适配', () => {
  test.use({ ...devices['iPhone 14'] })

  test('底部 Tab 栏显示', async ({ page }) => {
    await page.goto('/chat')
    // 底部 Tab 栏应该可见
    await expect(page.getByText('AI法务')).toBeVisible()
    await expect(page.getByText('智能协作')).toBeVisible()
    await expect(page.getByText('信息中心')).toBeVisible()
    await expect(page.getByText('法律智库')).toBeVisible()
    await expect(page.getByText('更多')).toBeVisible()
  })

  test('点击智能协作 Tab 跳转', async ({ page }) => {
    await page.goto('/chat')
    await page.getByText('智能协作').click()
    await page.waitForURL(/cases/)
  })

  test('顶部二级导航在协作页显示', async ({ page }) => {
    await page.goto('/cases')
    // 应该看到二级导航
    await expect(page.getByText('案件管理')).toBeVisible()
  })
})
