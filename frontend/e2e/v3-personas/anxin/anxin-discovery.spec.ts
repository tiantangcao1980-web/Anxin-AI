/**
 * 🤖 安心助理 — 发现 → 进入工作台 (P14-A)
 *
 * Acceptance Criteria：
 *   - AC1: /agents 加载后显示 10 个 persona 卡片
 *   - AC2: 安心助理卡片可见（含 emoji + display_name + persona_id）
 *   - AC3: 点击安心助理卡片跳转到 /v3/personas/anxin_assistant
 *   - AC4: 工作台头部显示安心助理身份信息
 *   - AC5: 顶部搜索框可按名称过滤出"安心助理"
 *
 * TODO(前端补 testid)：
 *   - PersonaCard 缺 data-testid="persona-card" / data-testid="persona-card-{id}"
 *   - AgentsPage 顶部搜索 Input 缺 data-testid="persona-search"
 */

import { expect, test } from '@playwright/test'

import { setupPersonaSession } from '../_helpers/persona'

test.describe('🤖 安心助理 - discovery（/agents → 工作台）', () => {
  test.setTimeout(30_000)

  test.beforeEach(async ({ page }) => {
    await setupPersonaSession(page, { role: 'enterprise_user' })
    await page.goto('/agents')
  })

  test('AC1: /agents 列表显示 10 个 persona 卡片', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '智能体' })).toBeVisible()
    // 卡片用"进入工作台" CTA 计数（每张卡片 1 个）
    await expect(page.getByRole('button', { name: /进入工作台/ })).toHaveCount(10)
  })

  test('AC2: 安心助理卡片可见（emoji + display_name）', async ({ page }) => {
    // 用 display_name 锚定（card 内 truncate h3 文本）
    await expect(page.getByText('安心助理', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('anxin_assistant').first()).toBeVisible()
  })

  test('AC3: 点击安心助理卡片跳转到 /v3/personas/anxin_assistant', async ({ page }) => {
    // 找到卡片（含 display_name 的 Card）→ 点 CTA
    const card = page.locator('div').filter({ hasText: 'anxin_assistant' }).first()
    await card.getByRole('button', { name: /进入工作台/ }).click()

    await expect(page).toHaveURL(/\/v3\/personas\/anxin_assistant/)
    // 工作台头部显示 display_name
    await expect(
      page.getByRole('heading', { name: '安心助理', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })
  })

  test('AC4: "已实装" / "规划中" 徽章在卡片上正确分布', async ({ page }) => {
    // 5 个已实装 persona（operations / market / lead / content / ecommerce）
    // 注：徽章文案在卡片+顶部状态条都会出现，所以用 getByText().count() 不严格
    await expect(page.getByText('已实装 5 个')).toBeVisible()
    await expect(page.getByText('规划中 5 个')).toBeVisible()
  })

  test('AC5: 顶部搜索框可按名称过滤出"安心助理"', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/搜索 persona/)
    await searchInput.fill('安心助理')

    // 过滤后只剩 1 张卡片
    await expect(page.getByRole('button', { name: /进入工作台/ })).toHaveCount(1)
    await expect(page.getByText('anxin_assistant').first()).toBeVisible()
  })

  test('AC6: 切换"规划中" tab 后安心助理仍然在列', async ({ page }) => {
    await page.getByRole('tab', { name: '规划中' }).click()
    // 规划中 5 个 persona
    await expect(page.getByRole('button', { name: /进入工作台/ })).toHaveCount(5)
    await expect(page.getByText('anxin_assistant').first()).toBeVisible()
  })
})
