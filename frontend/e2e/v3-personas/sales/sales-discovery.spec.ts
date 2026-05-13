/**
 * P14-D 获客猎手 — 发现 / 进入工作台 spec
 *
 * 路径：/agents → 找到 🎯 获客猎手 → 进入 /v3/personas/lead_hunter
 */

import { expect, test, type Page } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const SALES_PERSONA = {
  persona_id: 'lead_hunter',
  display_name: '获客猎手',
  emoji: '🎯',
  description: '把陌生人变成客户，把客户变成朋友',
  domain: '增长获客',
  is_implemented: true,
  capabilities: [
    '线索挖掘（基于行业 / 招聘 / 工商信号识别潜客）',
    'Vibe Selling（基于客户语境调整销售话术）',
    '跟进策略（基于客户阶段推送下一步行动）',
    '投放决策（AI-Trader 范式，多 agent 协商出价）',
    '客户分层（RFM + 行为评分 + 优先级）',
  ],
  backed_by_skills: [
    'sales/lead-mining',
    'sales/vibe-selling',
    'sales/follow-up',
    'sales/quotation-draft',
    'decision/multi-agent-vote',
    'marketing/ad-optimize',
    'marketing/audience-target',
  ],
  supported_apps: ['salesforce', 'hubspot', 'zoho', 'pipedrive', 'feishu', 'wecom', 'linkedin'],
}

async function installPersonaMocks(page: Page) {
  await page.route('**/api/v1/personas', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [SALES_PERSONA], total: 1 }),
      })
      return
    }
    await route.continue()
  })
  await page.route('**/api/v1/personas/lead_hunter', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...SALES_PERSONA,
          backed_by_agents: ['sentiment_agent', 'consensus_agent', 'lead_agent', 'vibe_seller'],
          system_prompt_excerpt: '你是「获客猎手」persona —— 把线索变成客户。',
        }),
      })
      return
    }
    await route.continue()
  })
}

test.describe('P14-D · 🎯 获客猎手 · 发现链路', () => {
  test.beforeEach(async ({ page }) => {
    await installApiMocks(page)
    await installPersonaMocks(page)
    await seedAuthState(page, {
      role: 'admin',
      userId: 'e2e-sales',
      name: 'E2E Sales',
      email: 'sales@anxinassistant.com',
    })
  })

  test('在智能体中心可见获客猎手卡片并进入工作台', async ({ page }) => {
    await page.goto('/agents')

    await expect(page.getByRole('heading', { name: '智能体', level: 1 })).toBeVisible({ timeout: 15000 })

    const cardName = page.getByRole('heading', { name: '获客猎手' })
    await expect(cardName).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('已实装').first()).toBeVisible()
    await expect(page.getByText('把陌生人变成客户').first()).toBeVisible()

    const card = page.locator('div').filter({ has: cardName }).first()
    await card.getByRole('button', { name: '进入工作台' }).click()

    await expect(page).toHaveURL(/\/v3\/personas\/lead_hunter/)
    await expect(page.getByRole('heading', { name: '获客猎手', level: 1 })).toBeVisible()
  })

  test('直接访问 /v3/personas/lead_hunter 渲染工作台', async ({ page }) => {
    await page.goto('/v3/personas/lead_hunter')

    await expect(page.getByRole('heading', { name: '获客猎手', level: 1 })).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('已实装').first()).toBeVisible()

    // 能力清单
    await expect(page.getByText(/能力清单（\d+）/)).toBeVisible()
    await expect(page.getByText('线索挖掘（基于行业 / 招聘 / 工商信号识别潜客）')).toBeVisible()
    // chat 空状态
    await expect(page.getByText('和 获客猎手 开始对话')).toBeVisible()
  })

  test('集成应用区显示 7 个 sales / 协作类应用', async ({ page }) => {
    await page.goto('/v3/personas/lead_hunter')
    await expect(page.getByRole('heading', { name: '获客猎手', level: 1 })).toBeVisible({ timeout: 15000 })

    await expect(page.getByText(/集成应用（\d+）/)).toBeVisible()
    // 至少看到 salesforce / hubspot / linkedin 几个标识
    await expect(page.getByText('salesforce').first()).toBeVisible()
    await expect(page.getByText('hubspot').first()).toBeVisible()
    await expect(page.getByText('linkedin').first()).toBeVisible()
  })
})
