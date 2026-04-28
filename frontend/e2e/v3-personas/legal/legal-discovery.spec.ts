/**
 * ⚖️ 法律顾问 — 发现 → 进入工作台 (P14-A)
 *
 * Acceptance Criteria：
 *   - AC1: /agents 列表中能看到 "法律顾问" 卡片（含 emoji ⚖️）
 *   - AC2: 卡片显示业务域 = 合规经营
 *   - AC3: 点击卡片跳转到 /v3/personas/legal_advisor
 *   - AC4: 工作台头部含 ⚖️ + "法律顾问" + persona 描述
 *   - AC5: 顶部搜索"法律"或"法规检索"都能命中法律顾问卡片
 *
 * TODO(前端补 testid)：
 *   - PersonaCard 需要 data-testid="persona-card-legal_advisor"
 *   - 业务域徽章需要 data-testid="persona-domain-badge"
 */

import { expect, test } from '@playwright/test'

import { setupPersonaSession } from '../_helpers/persona'

test.describe('⚖️ 法律顾问 - discovery', () => {
  test.setTimeout(30_000)

  test.beforeEach(async ({ page }) => {
    await setupPersonaSession(page, { role: 'enterprise_user' })
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '智能体' })).toBeVisible()
  })

  test('AC1: 法律顾问卡片在列表中可见', async ({ page }) => {
    await expect(page.getByText('法律顾问', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('legal_advisor').first()).toBeVisible()
  })

  test('AC2: 卡片显示业务域 = 合规经营', async ({ page }) => {
    // legal_advisor 卡片域 = 合规经营（多个 persona 共享，至少出现 1 次）
    await expect(page.getByText('合规经营').first()).toBeVisible()
  })

  test('AC3: 点击法律顾问卡片跳转到 /v3/personas/legal_advisor', async ({ page }) => {
    const card = page.locator('div').filter({ hasText: 'legal_advisor' }).first()
    await card.getByRole('button', { name: /进入工作台/ }).click()

    await expect(page).toHaveURL(/\/v3\/personas\/legal_advisor/)
    await expect(
      page.getByRole('heading', { name: '法律顾问', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })
  })

  test('AC4: 工作台头部显示完整身份信息', async ({ page }) => {
    await page.goto('/v3/personas/legal_advisor')
    await expect(
      page.getByRole('heading', { name: '法律顾问', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })

    // 描述（顶部一句话定位）
    await expect(page.getByText(/你的随身法律大脑.*问法条/)).toBeVisible()
    // 规划中徽章（mock 中 is_implemented=false）
    await expect(page.getByText('规划中').first()).toBeVisible()
  })

  test('AC5a: 搜索"法律"能命中法律顾问', async ({ page }) => {
    await page.getByPlaceholder(/搜索 persona/).fill('法律')
    // 命中 法律顾问
    await expect(page.getByText('法律顾问', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('legal_advisor').first()).toBeVisible()
  })

  test('AC5b: 搜索能力关键词"法规检索"也能命中', async ({ page }) => {
    await page.getByPlaceholder(/搜索 persona/).fill('法规检索')
    await expect(page.getByText('legal_advisor').first()).toBeVisible()
    // 应只剩 1 张卡（capabilities 唯一匹配）
    await expect(page.getByRole('button', { name: /进入工作台/ })).toHaveCount(1)
  })
})
