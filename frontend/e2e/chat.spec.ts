import { test, expect } from '@playwright/test'

test.describe('AI 对话', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat')
  })

  test('对话页面正确渲染', async ({ page }) => {
    await expect(page.getByText('AI 法务助手')).toBeVisible()
    // 输入框存在
    const input = page.locator('textarea, [contenteditable], input[type="text"]').first()
    await expect(input).toBeVisible()
  })

  test('新建对话', async ({ page }) => {
    const newChatBtn = page.getByRole('button', { name: /新建/ })
    if (await newChatBtn.isVisible()) {
      await newChatBtn.click()
    }
  })
})
