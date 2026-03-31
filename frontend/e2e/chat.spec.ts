import { test, expect } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'

test.describe('AI 对话', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('对话页面正确渲染', async ({ page }) => {
    await expect(page.getByText('你好，有什么可以帮您？')).toBeVisible()
    await expect(page.getByPlaceholder(/发送消息或输入/)).toBeVisible()
    await expect(page.getByText(/快速咨询/)).toBeVisible()
  })

  test('新建对话', async ({ page }) => {
    await page.getByRole('button', { name: /新建对话/ }).click()
    await expect(page.getByText('你好，有什么可以帮您？')).toBeVisible()
  })
})
