/**
 * P14-B · 尽调专家 (due_diligence_expert) — 工作台对话
 *
 * 验证：
 *   1. 工作台正确加载（chat 面板 + 能力清单）
 *   2. EmptyHint 显示能力 sample 提问
 *   3. 输入公司名 → 发送 → 应答气泡出现
 *   4. 规划中提示出现
 */

import { test, expect, type Page, type Route } from '@playwright/test'
import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA_ID = 'due_diligence_expert'

const personaPayload = {
  persona_id: PERSONA_ID,
  display_name: '尽调专家',
  emoji: '🔍',
  description: '见客户 / 投资 / 收购前，先让我看看对方家底',
  domain: '合规经营',
  is_implemented: false,
  capabilities: [
    '工商尽调（股权 / 实控人 / 关联 / 变更）',
    '法律尽调（诉讼 / 仲裁 / 行政处罚 / 失信）',
    '财务尽调（年报 / 经营异常 / 税务等级）',
  ],
  backed_by_skills: ['intelligence/company-profile'],
  supported_apps: ['企查查', '天眼查'],
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
        backed_by_agents: ['due_diligence', 'evidence_analyst'],
        system_prompt_excerpt: '你是「尽调专家」persona — mock 详情。',
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
        content: '🔍 **尽调专家**：收到对该公司的尽调请求，正在汇集工商 / 司法 / 舆情数据。',
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

test.describe('尽调专家 · 工作台对话', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await page.goto(`/v3/personas/${PERSONA_ID}`)
    await expect(page.getByText('尽调专家').first()).toBeVisible({ timeout: 15000 })
  })

  test('工作台加载 — chat 面板与能力清单同时存在', async ({ page }) => {
    await expect(page.getByText(/与.*尽调专家.*对话/)).toBeVisible()
    await expect(page.getByPlaceholder(/和 尽调专家 说点什么/)).toBeVisible()
    await expect(page.getByText(/能力清单/)).toBeVisible()
  })

  test('EmptyHint 显示能力 sample 提问', async ({ page }) => {
    await expect(page.getByText('和 尽调专家 开始对话')).toBeVisible()
    await expect(page.getByText(/请帮我：工商尽调/)).toBeVisible()
  })

  test('输入公司名 → 发送 → 应答气泡出现', async ({ page }) => {
    const textarea = page.getByPlaceholder(/和 尽调专家 说点什么/)
    await textarea.fill('帮我尽调一下「上海某科技有限公司」')
    await page.getByRole('button', { name: /发送/ }).click()

    await expect(page.getByText(/上海某科技有限公司/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/尽调专家.*收到/)).toBeVisible({ timeout: 10000 })
  })

  test('未实装 persona 显示规划中提示', async ({ page }) => {
    await expect(page.getByText(/后端尚未实装.*规划中/)).toBeVisible()
  })
})
