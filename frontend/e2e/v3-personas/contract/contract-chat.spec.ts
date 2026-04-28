/**
 * P14-B · 合同管家 (contract_steward) — 工作台对话
 *
 * 验证：
 *   1. 工作台正确加载（顶栏 / 左侧 chat / 右侧能力）
 *   2. EmptyHint 显示能力 sample 提问
 *   3. 发送消息 → 应答气泡出现，含 persona 名
 *   4. 规划中提示出现在输入区下方
 */

import { test, expect, type Page, type Route } from '@playwright/test'
import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA_ID = 'contract_steward'

const personaPayload = {
  persona_id: PERSONA_ID,
  display_name: '合同管家',
  emoji: '📜',
  description: '从起草、审查、谈判、签署到归档，每一份合同我帮你盯',
  domain: '合规经营',
  is_implemented: false,
  capabilities: [
    '合同起草（200+ 模板库 + 智能填空 + 行业定制）',
    '合同审查（逐条审查 + 风险标注 + 修改建议）',
    '合同谈判（让步空间分析 + 替代条款建议）',
  ],
  backed_by_skills: ['legal/contract-draft', 'legal/contract-review'],
  supported_apps: ['法大大', 'e签宝'],
}

async function stubPersonaEndpoints(page: Page) {
  await page.route('**/api/v1/personas', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [personaPayload], total: 1 }),
    })
  })

  await page.route(`**/api/v1/personas/${PERSONA_ID}`, async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...personaPayload,
        backed_by_agents: ['contract_reviewer', 'contract_steward'],
        system_prompt_excerpt: '你是「合同管家」persona — mock 详情。',
      }),
    })
  })

  await page.route(`**/api/v1/personas/${PERSONA_ID}/chat`, async (route: Route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: PERSONA_ID,
        content: '📜 **合同管家**：收到您的合同问题，我可以为您起草、审查或归档相关合同。',
        metadata: { is_implemented: false, mock: true },
      }),
    })
  })
}

async function login(page: Page) {
  await installApiMocks(page)
  await stubPersonaEndpoints(page)
  await seedAuthState(page, {
    role: 'admin',
    userId: 'e2e-admin',
    name: 'E2E Admin',
    email: 'admin@anxinfawu.com',
  })
}

test.describe('合同管家 · 工作台对话', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await page.goto(`/v3/personas/${PERSONA_ID}`)
    await expect(page.getByText('合同管家').first()).toBeVisible({ timeout: 15000 })
  })

  test('工作台加载 — chat 面板与能力清单同时存在', async ({ page }) => {
    // chat 面板顶栏（"与 合同管家 对话"）
    await expect(page.getByText(/与.*合同管家.*对话/)).toBeVisible()
    // 输入框存在
    await expect(page.getByPlaceholder(/和 合同管家 说点什么/)).toBeVisible()
    // 右侧能力清单
    await expect(page.getByText(/能力清单/)).toBeVisible()
  })

  test('EmptyHint 显示能力 sample 提问', async ({ page }) => {
    await expect(page.getByText('和 合同管家 开始对话')).toBeVisible()
    // 至少一条 sample（来自 capabilities[0..2]）
    await expect(page.getByText(/请帮我：合同起草/)).toBeVisible()
  })

  test('发送消息 → 应答气泡出现', async ({ page }) => {
    const textarea = page.getByPlaceholder(/和 合同管家 说点什么/)
    await textarea.fill('帮我起草一份服务合同')
    await page.getByRole('button', { name: /发送/ }).click()

    // user 消息进 thread
    await expect(page.getByText('帮我起草一份服务合同')).toBeVisible({ timeout: 10000 })
    // assistant 应答出现
    await expect(page.getByText(/合同管家.*收到/)).toBeVisible({ timeout: 10000 })
  })

  test('未实装 persona 在输入区下方显示规划中提示', async ({ page }) => {
    await expect(page.getByText(/后端尚未实装.*规划中/)).toBeVisible()
  })
})
