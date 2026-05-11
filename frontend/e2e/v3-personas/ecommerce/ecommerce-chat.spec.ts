/**
 * V3 Persona E2E — 🌍 跨境电商助手 · 通用对话 (P14-E)
 *
 * POST /api/v1/personas/ecommerce_assistant/chat
 *
 * 关键 assert：
 *   - 工作台顶部 / 输入框 / 发送 / 清空 4 个核心交互
 *   - mock 回复中的关键字段在气泡中可见
 */

import { expect, test, type Page, type Route } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA = {
  persona_id: 'ecommerce_assistant',
  display_name: '跨境电商助手',
  emoji: '🌍',
  description: '从想做出海到第一笔订单，每个坑我帮你避',
  domain: '出海跨境',
  is_implemented: true,
  enabled: true,
  capabilities: [
    '选品分析',
    '验商',
    'AI 议价',
    '独立站搭建',
    '铺货',
    'VAT 指引',
  ],
  backed_by_skills: ['ecommerce/product-selection', 'ecommerce/store-setup'],
  supported_apps: ['shopify', 'shopee', 'tiktok_shop', '1688'],
}

async function installEcommerceMocks(page: Page, opts: { reply?: string } = {}) {
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
        content:
          opts.reply ?? '🌍 **跨境电商助手**：已收到你的出海需求，正在为你拟方案。',
        metadata: { mock: true, is_implemented: true },
      }),
    })
  })
}

test.describe('V3 / persona 对话 / 🌍 跨境电商助手', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only — 双栏工作台')
    await installApiMocks(page)
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-ecommerce',
      name: '跨境 E2E',
      email: 'ecommerce@example.com',
    })
  })

  test('工作台正确渲染 persona 头像 / 名称 / 描述 / 已实装徽章', async ({ page }) => {
    await installEcommerceMocks(page)
    await page.goto('/v3/personas/ecommerce_assistant')

    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('从想做出海到第一笔订单', { exact: false })).toBeVisible()
    await expect(page.getByText('已实装').first()).toBeVisible()
  })

  test('发送出海咨询可看到用户气泡和 assistant 回复', async ({ page }) => {
    await installEcommerceMocks(page, {
      reply: '🌍 跨境电商助手：建议你先做选品 + 选平台 + 选物流三件事。',
    })
    await page.goto('/v3/personas/ecommerce_assistant')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    const input = page.getByPlaceholder(/和 跨境电商助手 说点什么/)
    await input.fill('我想做美区 TikTok Shop，现在该从哪一步开始？')
    await page.getByRole('button', { name: /发送/ }).click()

    await expect(page.getByText('美区 TikTok Shop', { exact: false })).toBeVisible({ timeout: 6000 })
    await expect(page.getByText(/选品 \+ 选平台 \+ 选物流/)).toBeVisible({ timeout: 6000 })
  })

  test('对话历史可被「清空」按钮重置', async ({ page }) => {
    await installEcommerceMocks(page, { reply: '🌍 已收到出海咨询' })
    await page.goto('/v3/personas/ecommerce_assistant')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    await page.getByPlaceholder(/和 跨境电商助手 说点什么/).fill('你好')
    await page.getByRole('button', { name: /发送/ }).click()

    await expect(page.getByText(/已收到出海咨询/)).toBeVisible({ timeout: 6000 })

    await page.getByRole('button', { name: /清空/ }).click()
    await expect(page.getByText(/已收到出海咨询/)).toHaveCount(0)
  })

  test('未输入时发送按钮处于禁用态', async ({ page }) => {
    await installEcommerceMocks(page)
    await page.goto('/v3/personas/ecommerce_assistant')
    await expect(page.getByRole('heading', { name: '跨境电商助手' })).toBeVisible({ timeout: 10000 })

    const sendBtn = page.getByRole('button', { name: /发送/ })
    await expect(sendBtn).toBeDisabled()
  })
})
