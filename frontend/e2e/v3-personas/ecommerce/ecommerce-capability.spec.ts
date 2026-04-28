/**
 * V3 Persona E2E — 🌍 跨境电商助手 · 能力触发器 (P14-E)
 *
 * P14-E 要求覆盖三类能力：
 *   1. 选品分析 → 输入赛道 → 看到 NicheReport（市场规模 / 竞品 / 利润预估）
 *   2. AI 议价 → 输入目标价 → 看到 4 轮议价脚本（中英双版）
 *   3. VAT 指引 → 选德国 → 看到 VAT 率 + 申报手续 + disclaimer
 *
 * 验证策略与 content-capability 一致：
 *   走通用 chat 端点（CapabilityRunner 现有实现），
 *   mock 在 chat response 中返回结构化文本，验证关键字段在气泡中可见。
 */

import { expect, test, type Page, type Route } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA = {
  persona_id: 'ecommerce_assistant',
  display_name: '跨境电商助手',
  emoji: '🌍',
  description: '从想做出海到第一笔订单',
  domain: '出海跨境',
  is_implemented: true,
  enabled: true,
  capabilities: [
    '选品分析',
    'AI 议价',
    'VAT 指引',
    '验商',
  ],
  backed_by_skills: ['ecommerce/product-selection', 'ecommerce/oversea-compliance'],
  supported_apps: ['shopify', 'tiktok_shop'],
}

interface ChatRouteOptions {
  reply: string
}

async function installEcommerceMocks(page: Page, opts: ChatRouteOptions) {
  await page.route('**/api/v1/personas', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [PERSONA], total: 1 }),
    })
  })

  await page.route('**/api/v1/personas/ecommerce_assistant', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...PERSONA,
        backed_by_agents: ['ecommerce_agent'],
        system_prompt_excerpt: '你是「跨境电商助手」persona。',
      }),
    })
  })

  await page.route('**/api/v1/personas/ecommerce_assistant/chat', async (route: Route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'ecommerce_assistant',
        content: opts.reply,
        metadata: { mock: true, is_implemented: true },
      }),
    })
  })
}

test.describe('V3 / persona 能力触发 / 🌍 跨境电商助手', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only — 三栏 capability runner')
    await installApiMocks(page)
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-ecommerce',
      name: '跨境 E2E',
      email: 'ecommerce@example.com',
    })
  })

  test('选品分析：输入赛道 → 看到 NicheReport（市场规模 / 竞品 / 利润预估）', async ({ page }) => {
    await installEcommerceMocks(page, {
      reply: [
        '📊 **NicheReport — 户外便携咖啡机（北美）**',
        '',
        '**市场规模：** 2026 年北美预计 USD 4.2B / yoy +18%',
        '**竞品 Top 3：** Wacaco Picopresso · Outin Nano · Cafflano Kompact',
        '**利润预估：** 出厂价 USD 35 / 零售价 USD 79 / 毛利 ~52%',
        '**风险提示：** 涉及食品接触认证（FDA / NSF）',
      ].join('\n'),
    })
    await page.goto('/v3/personas/ecommerce_assistant')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: /选品分析/ }).click()
    await expect(page.getByText(/将触发：/)).toBeVisible()

    await page.getByPlaceholder(/可选：贴入你的输入/).fill('赛道：户外便携咖啡机；目标市场：北美')
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/NicheReport/)).toBeVisible({ timeout: 6000 })
    await expect(page.getByText(/市场规模/)).toBeVisible()
    await expect(page.getByText(/竞品 Top 3/)).toBeVisible()
    await expect(page.getByText(/利润预估/)).toBeVisible()
  })

  test('AI 议价：输入目标价 → 看到 4 轮议价脚本（中英双版）', async ({ page }) => {
    await installEcommerceMocks(page, {
      reply: [
        '💬 **AI 议价方案 — 目标 USD 28 / pcs**',
        '',
        '**Round 1（试探）：**',
        '  CN：你好，量大可以做到 30 美金吗？',
        '  EN: Hi, would you consider USD 30 / pcs for a larger order?',
        '',
        '**Round 2（条件让步）：**',
        '  CN：我们可以付 30% 预付款，但单价希望降到 28。',
        '  EN: We can pay 30% upfront if you can lower it to USD 28.',
        '',
        '**Round 3（增量诱导）：**',
        '  CN：第一单 500 件，复购 5000 件起，能到 27 吗？',
        '  EN: 500 pcs for first order, 5000 + on repeat. Could you do USD 27?',
        '',
        '**Round 4（收口）：**',
        '  CN：那就 USD 28 全单，T/T 30%。',
        '  EN: Let\'s settle at USD 28, T/T 30%.',
      ].join('\n'),
    })
    await page.goto('/v3/personas/ecommerce_assistant')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: /AI 议价/ }).click()
    await page.getByPlaceholder(/可选：贴入你的输入/).fill('目标价：USD 28；首单：500 pcs')
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/Round 1/)).toBeVisible({ timeout: 6000 })
    await expect(page.getByText(/Round 2/)).toBeVisible()
    await expect(page.getByText(/Round 3/)).toBeVisible()
    await expect(page.getByText(/Round 4/)).toBeVisible()
    // 中英双版的存在
    await expect(page.getByText(/USD 28/).first()).toBeVisible()
    await expect(page.getByText(/复购/)).toBeVisible()
  })

  test('VAT 指引：选德国 → 看到 VAT 率 + 申报手续 + disclaimer', async ({ page }) => {
    await installEcommerceMocks(page, {
      reply: [
        '🇩🇪 **VAT 指引 — 德国（Germany）**',
        '',
        '**VAT 率：** 标准 19%（部分商品 7% 优惠率）',
        '**申报手续：**',
        '  1. 在 Bundeszentralamt für Steuern 注册并取得 VAT 税号',
        '  2. 任命德国境内税务代表（非欧盟卖家强制）',
        '  3. 月度 / 季度申报（年销售额阈值决定）',
        '  4. ELSTER 系统线上提交',
        '',
        '⚠️ **Disclaimer：** 本指引仅供参考，具体申报请以税务代表或当地税局确认为准。',
      ].join('\n'),
    })
    await page.goto('/v3/personas/ecommerce_assistant')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: /VAT 指引/ }).click()
    await page.getByPlaceholder(/可选：贴入你的输入/).fill('国家：德国（Germany）')
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/德国/)).toBeVisible({ timeout: 6000 })
    await expect(page.getByText(/VAT 率/)).toBeVisible()
    await expect(page.getByText(/19%/)).toBeVisible()
    await expect(page.getByText(/申报手续/)).toBeVisible()
    await expect(page.getByText(/Disclaimer/)).toBeVisible()
  })

  test('未选能力时点击触发会被禁用', async ({ page }) => {
    await installEcommerceMocks(page, { reply: '不应被调用' })
    await page.goto('/v3/personas/ecommerce_assistant')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    const triggerBtn = page.getByRole('button', { name: /触发并发送到对话/ })
    await expect(triggerBtn).toBeDisabled()
  })
})
