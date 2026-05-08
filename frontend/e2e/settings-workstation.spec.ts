import { expect, test } from '@playwright/test'

import { loginAsAdmin } from './helpers/auth'

test.describe('桌面主工作站设置入口', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('direct and legacy links open the workstation tab', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await expect(page.getByRole('tab', { name: '工作站' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('desktop-workstation-panel')).toBeVisible()
    await expect(page.getByText('桌面主工作站')).toBeVisible()
    await expect(page.getByText('非桌面预览')).toBeVisible()

    await page.goto('/settings?tab=privacy')

    await expect(page.getByRole('tab', { name: '工作站' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('desktop-workstation-panel')).toBeVisible()
  })

  test('tab changes write back to the URL', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await page.getByRole('tab', { name: '服务集成' }).click()

    await expect(page).toHaveURL(/\/settings\?tab=mcp$/)
    await expect(page.getByRole('tab', { name: '服务集成' })).toHaveAttribute('aria-selected', 'true')
  })

  test('non-desktop preview keeps desktop-only actions disabled', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await expect(page.getByRole('button', { name: '配置模型' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '同步状态' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '查看任务' })).toBeDisabled()
    await expect(page.getByText('请在桌面客户端启用')).toHaveCount(3)
  })
})

test.describe('桌面主工作站移动宽度', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile', 'mobile viewport coverage only')
    await loginAsAdmin(page)
  })

  test('resource cards stay within the mobile viewport', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await expect(page.getByTestId('desktop-workstation-panel')).toBeVisible()
    await expect(page.getByText('非桌面预览')).toBeVisible()

    const cardBoxes = await page
      .locator('[data-testid^="desktop-workstation-resource-"]')
      .evaluateAll((nodes) =>
        nodes.map((node) => {
          const rect = node.getBoundingClientRect()
          return {
            left: rect.left,
            right: rect.right,
            width: rect.width,
            viewport: window.innerWidth,
          }
        }),
      )

    expect(cardBoxes).toHaveLength(6)
    for (const box of cardBoxes) {
      expect(box.left).toBeGreaterThanOrEqual(0)
      expect(box.right).toBeLessThanOrEqual(box.viewport + 1)
      expect(box.width).toBeGreaterThan(280)
    }
  })
})
