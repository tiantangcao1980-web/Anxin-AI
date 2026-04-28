/**
 * V3 Persona E2E — 🌍 跨境电商助手 · 发现 (P14-E)
 *
 * 入口路径：/agents → 看到 persona 卡 → 点「进入工作台」→ /v3/personas/ecommerce_assistant
 *
 * 关键 assert：
 *   - "跨境电商助手" 卡片可见
 *   - 已实装徽章 + "出海跨境" 业务域
 *   - 卡片显示 emoji 🌍 + 描述
 *   - 点击 → 跳到工作台
 */

import { expect, test, type Page, type Route } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const ECOMMERCE_PERSONA = {
  persona_id: 'ecommerce_assistant',
  display_name: '跨境电商助手',
  emoji: '🌍',
  description: '从想做出海到第一笔订单，每个坑我帮你避',
  domain: '出海跨境',
  is_implemented: true,
  enabled: true,
  capabilities: [
    '选品分析（跨平台数据 + 社媒信号 + 趋势识别）',
    '验商（供应商资质 / 风险 / 历史交易）',
    'AI 议价（多轮谈判脚本 + 让步策略）',
    '独立站搭建（Shopify 主题定制）',
    '铺货（Amazon / Shopee / TikTok Shop 一键铺货）',
    '出海合规（VAT / GDPR / CCPA 指引）',
  ],
  backed_by_skills: ['ecommerce/product-selection', 'ecommerce/store-setup'],
  supported_apps: ['shopify', 'shopee', 'tiktok_shop', 'amazon_sp_api', '1688'],
}

const OTHER_STUB = {
  persona_id: 'lead_hunter',
  display_name: '获客猎手',
  emoji: '🎯',
  description: '把陌生人变成客户',
  domain: '增长获客',
  is_implemented: true,
  enabled: true,
  capabilities: ['线索挖掘'],
  backed_by_skills: ['sales/lead-mining'],
  supported_apps: ['salesforce'],
}

async function installPersonasMock(page: Page) {
  await page.route('**/api/v1/personas', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [ECOMMERCE_PERSONA, OTHER_STUB],
        total: 2,
      }),
    })
  })

  await page.route('**/api/v1/personas/ecommerce_assistant', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...ECOMMERCE_PERSONA,
        backed_by_agents: ['ecommerce_agent', 'selection_agent'],
        system_prompt_excerpt:
          '你是「跨境电商助手」persona — 从想做出海到第一笔订单，每个坑我帮你避。',
      }),
    })
  })
}

test.describe('V3 / persona 发现 / 🌍 跨境电商助手', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only — agents 卡片网格')
    await installApiMocks(page)
    await installPersonasMock(page)
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-ecommerce',
      name: '跨境 E2E',
      email: 'ecommerce@example.com',
    })
  })

  test('在智能体中心可看到 🌍 跨境电商助手卡片', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '智能体' })).toBeVisible({ timeout: 10000 })

    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible()
    await expect(page.getByText('从想做出海到第一笔订单', { exact: false })).toBeVisible()
    await expect(page.getByText('🌍').first()).toBeVisible()
  })

  test('卡片显示「已实装」徽章 + 「出海跨境」业务域', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    await expect(page.getByText('已实装').first()).toBeVisible()
    await expect(page.getByText('出海跨境').first()).toBeVisible()
  })

  test('点击「进入工作台」跳转到 /v3/personas/ecommerce_assistant', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    // 跨境电商助手卡里的进入工作台按钮（按 persona 卡定位以避免与其它卡冲突）
    const card = page.getByRole('heading', { name: '跨境电商助手' }).locator('xpath=ancestor::*[contains(@class, "p-5")][1]')
    await card.getByRole('button', { name: /进入工作台/ }).click()

    await expect(page).toHaveURL(/\/v3\/personas\/ecommerce_assistant/, { timeout: 10000 })
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible()
  })

  test('搜索框可按关键词「跨境」过滤出 🌍 跨境电商助手', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    await page.getByPlaceholder(/搜索 persona/).fill('跨境')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '获客猎手' })).toHaveCount(0)
  })
})
