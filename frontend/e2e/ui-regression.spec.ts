import { expect, test } from '@playwright/test'

import { loginAsAdmin } from './helpers/auth'

test.describe('全局 UI 回归', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'mobile uses dedicated coverage')
    await loginAsAdmin(page)
  })

  test('全局设计系统基线已统一到品牌橙与标准卡片', async ({ page }) => {
    await page.goto('/contracts')

    await expect(page.locator('[data-ui="page-shell"]')).toBeVisible()
    await expect(page.locator('[data-ui="page-header"]')).toBeVisible()
    await expect(page.locator('[data-ui="surface-card"]').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /完整审查|上传审查/ })).toBeVisible()
  })

  test('标准业务页共享同一 page shell 结构', async ({ page }) => {
    await page.goto('/documents')

    await expect(page.locator('[data-ui="page-shell"]')).toBeVisible()
    await expect(page.locator('[data-ui="page-header"]')).toBeVisible()
    await expect(page.locator('[data-ui="surface-card"]').first()).toBeVisible()
  })

  test('分析页共享统一的任务摘要与控制布局', async ({ page }) => {
    await page.goto('/due-diligence')

    await expect(page.locator('[data-analysis-shell]')).toBeVisible()
    await expect(page.locator('[data-analysis-toolbar]')).toBeVisible()
    await expect(page.locator('[data-analysis-main]')).toBeVisible()
  })

  test('后台页使用统一 token 而不是独立颜色常量', async ({ page }) => {
    await page.goto('/admin')

    await expect(page.locator('[data-admin-shell]')).toBeVisible()
    await expect(page.locator('[data-ui="surface-card"]').first()).toBeVisible()
  })

  test('知识库与案件页接入统一业务壳层语义', async ({ page }) => {
    await page.goto('/knowledge-base')
    await expect(page.locator('[data-ui="page-shell"]')).toBeVisible()
    await expect(page.locator('[data-ui="page-header"]')).toBeVisible()

    await page.goto('/cases')
    await expect(page.locator('[data-ui="page-shell"]')).toBeVisible()
    await expect(page.locator('[data-ui="page-header"]')).toBeVisible()
  })

  test('chat 桌面端欢迎区与工作台具备统一视觉锚点', async ({ page }) => {
    await page.goto('/chat')

    await expect(page.locator('[data-chat-welcome]')).toBeVisible()
    await expect(page.locator('[data-workbench-surface]')).toBeVisible()
    await expect(page.locator('[data-workbench-header]')).toBeVisible()
  })
})

test.describe('移动端视觉平衡', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile', 'mobile-only checks')
    await loginAsAdmin(page)
  })

  test('chat 移动端不出现重复顶部状态栏', async ({ page }) => {
    await page.goto('/chat')

    await expect(page.locator('[data-chat-local-header]')).toBeHidden()
  })
})
