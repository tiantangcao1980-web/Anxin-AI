import { test, expect } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'
import { installApiMocks } from './helpers/session'

test.describe('认证流程', () => {
  test('登录页面正确渲染', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: '安心智能助手' }).first()).toBeVisible()
    await expect(page.getByPlaceholder('请输入邮箱地址')).toBeVisible()
    await expect(page.getByPlaceholder('请输入密码')).toBeVisible()
  })

  test('空表单提交显示错误', async ({ page }) => {
    await page.goto('/login')
    await page.locator('form').getByRole('button', { name: '登录' }).click()
    await expect(page.getByText('请填写邮箱和密码')).toBeVisible()
  })

  test('未登录访问受保护页面重定向到登录', async ({ page }) => {
    await page.goto('/chat')
    await expect(page).toHaveURL(/login/)
  })

  test('测试账号可以登录并进入对话页', async ({ page }) => {
    await installApiMocks(page)
    await page.goto('/login')
    await page.getByPlaceholder('请输入邮箱地址').fill('admin@anxinassistant.com')
    await page.getByPlaceholder('请输入密码').fill('admin888')
    await page.locator('form').getByRole('button', { name: '登录' }).click()
    await expect(page).toHaveURL(/chat/)
  })
})
