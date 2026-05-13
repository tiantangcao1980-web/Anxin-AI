/**
 * P14-D 获客猎手 — Chat 通用对话 spec
 */

import { expect, test, type Page } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA = {
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
  ],
  backed_by_skills: ['sales/lead-mining', 'sales/follow-up'],
  supported_apps: ['salesforce', 'hubspot', 'linkedin'],
}

async function installPersonaMocks(page: Page) {
  await page.route('**/api/v1/personas', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [PERSONA], total: 1 }),
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
          ...PERSONA,
          backed_by_agents: ['lead_agent'],
          system_prompt_excerpt: '…',
        }),
      })
      return
    }
    await route.continue()
  })
  await page.route('**/api/v1/personas/lead_hunter/chat', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.continue()
      return
    }
    const body = JSON.parse(route.request().postData() ?? '{}') as { message?: string }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'lead_hunter',
        content: `🎯 **获客猎手**：收到「${(body.message ?? '').slice(0, 60)}」。\n\n我可以帮你做：线索挖掘 / Vibe Selling / 跟进策略`,
        metadata: { mock: true, is_implemented: true },
      }),
    })
  })
}

test.describe('P14-D · 🎯 获客猎手 · Chat', () => {
  test.beforeEach(async ({ page }) => {
    await installApiMocks(page)
    await installPersonaMocks(page)
    await seedAuthState(page, {
      role: 'admin',
      userId: 'e2e-sales',
      name: 'E2E Sales',
      email: 'sales@anxinassistant.com',
    })
    await page.goto('/v3/personas/lead_hunter')
    await expect(page.getByRole('heading', { name: '获客猎手', level: 1 })).toBeVisible({ timeout: 15000 })
  })

  test('发送消息后能看到 user 与 assistant 两条气泡', async ({ page }) => {
    const textarea = page.getByPlaceholder(/和 获客猎手 说点什么/)
    await expect(textarea).toBeVisible()
    await textarea.fill('帮我挖一批 SaaS 行业 D 轮以上的公司线索')
    await page.getByRole('button', { name: '发送' }).click()

    await expect(page.getByText('帮我挖一批 SaaS 行业 D 轮以上的公司线索')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/收到「帮我挖一批 SaaS 行业 D 轮以上的公司线索/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/对话 · [2-9] 条/)).toBeVisible()
  })

  test('Enter 提交快捷键工作正常', async ({ page }) => {
    const textarea = page.getByPlaceholder(/和 获客猎手 说点什么/)
    await textarea.fill('你好')
    await textarea.press('Enter')

    await expect(page.getByText('你好').first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/收到「你好/)).toBeVisible({ timeout: 10000 })
  })

  test('清空按钮可重置 thread', async ({ page }) => {
    await page.getByPlaceholder(/和 获客猎手 说点什么/).fill('一句话')
    await page.getByRole('button', { name: '发送' }).click()
    await expect(page.getByText('一句话').first()).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: '清空' }).click()
    await expect(page.getByText('和 获客猎手 开始对话')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/对话 · 0 条/)).toBeVisible()
  })

  test('空状态可点击 sample 提问回填到 textarea', async ({ page }) => {
    const sample = page.getByRole('button', { name: /请帮我：线索挖掘/ })
    await expect(sample).toBeVisible()
    await sample.click()
    await expect(page.getByPlaceholder(/和 获客猎手 说点什么/)).toHaveValue(/请帮我：线索挖掘/)
  })
})
