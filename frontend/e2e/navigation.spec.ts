import { test, expect } from '@playwright/test'

test.describe('导航结构', () => {
  test.beforeEach(async ({ page }) => {
    // DEV_MODE 下自动登录
    await page.goto('/chat')
  })

  test('顶部导航栏显示四大业务域', async ({ page }) => {
    await expect(page.getByText('AI法务')).toBeVisible()
    await expect(page.getByText('智能协作')).toBeVisible()
    await expect(page.getByText('信息中心')).toBeVisible()
    await expect(page.getByText('法律智库')).toBeVisible()
  })

  test('点击智能协作显示侧边栏', async ({ page }) => {
    await page.getByText('智能协作').click()
    await expect(page.getByText('案件管理')).toBeVisible()
    await expect(page.getByText('合同管理')).toBeVisible()
  })

  test('案件管理页面加载', async ({ page }) => {
    await page.goto('/cases')
    await expect(page.getByText('案件管理')).toBeVisible()
    await expect(page.getByText('新建案件')).toBeVisible()
  })

  test('合同管理页面加载', async ({ page }) => {
    await page.goto('/contracts')
    await expect(page.getByText('合同审查')).toBeVisible()
  })
})
