/**
 * P14-D 市场研究员 — Chat 通用对话 spec
 *
 * 路径覆盖：进入工作台 → 在左侧 chat 输入 → 发送 → 看到 mock assistant 回复。
 */

import { expect, test, type Page } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA = {
  persona_id: 'market_researcher',
  display_name: '市场研究员',
  emoji: '📊',
  description: '想了解一个行业 / 一个对手 / 一个趋势，我做你的研究员',
  domain: '增长获客',
  is_implemented: true,
  capabilities: [
    '行业研究（DeepTutor 模式深度阅读多份报告）',
    '竞品监控（定时抓取竞品动态 + 异动报警）',
    '趋势挖掘（从舆情 / 社媒 / 招聘 信号识别趋势）',
  ],
  backed_by_skills: ['research/deeptutor-mode', 'research/citation-trace'],
  supported_apps: ['reddit', 'x', 'linkedin'],
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
  await page.route('**/api/v1/personas/market_researcher', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...PERSONA,
          backed_by_agents: ['market_agent'],
          system_prompt_excerpt: '你是市场研究员…',
        }),
      })
      return
    }
    await route.continue()
  })
  await page.route('**/api/v1/personas/market_researcher/chat', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.continue()
      return
    }
    const body = JSON.parse(route.request().postData() ?? '{}') as { message?: string }
    const userMsg = body.message ?? ''
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'market_researcher',
        content: `📊 **市场研究员**：收到「${userMsg.slice(0, 60)}」。\n\n我可以帮你做：行业研究 / 竞品监控 / 趋势挖掘`,
        metadata: { mock: true, is_implemented: true },
      }),
    })
  })
}

test.describe('P14-D · 📊 市场研究员 · Chat', () => {
  test.beforeEach(async ({ page }) => {
    await installApiMocks(page)
    await installPersonaMocks(page)
    await seedAuthState(page, {
      role: 'admin',
      userId: 'e2e-market',
      name: 'E2E Market',
      email: 'market@anxinassistant.com',
    })
    await page.goto('/v3/personas/market_researcher')
    await expect(page.getByRole('heading', { name: '市场研究员', level: 1 })).toBeVisible({ timeout: 15000 })
  })

  test('发送消息后能看到 user 与 assistant 两条气泡', async ({ page }) => {
    const textarea = page.getByPlaceholder(/和 市场研究员 说点什么/)
    await expect(textarea).toBeVisible()

    await textarea.fill('帮我调研一下 Notion AI 的 GTM 策略')
    await page.getByRole('button', { name: '发送' }).click()

    // user 气泡
    await expect(page.getByText('帮我调研一下 Notion AI 的 GTM 策略')).toBeVisible({ timeout: 10000 })
    // assistant 回复
    await expect(page.getByText(/收到「帮我调研一下 Notion AI 的 GTM 策略/)).toBeVisible({ timeout: 10000 })
    // 顶部 thread 计数 ≥ 2
    await expect(page.getByText(/对话 · [2-9] 条/)).toBeVisible()
  })

  test('空输入时发送按钮 disabled', async ({ page }) => {
    const sendBtn = page.getByRole('button', { name: '发送' })
    await expect(sendBtn).toBeDisabled()

    await page.getByPlaceholder(/和 市场研究员 说点什么/).fill('   ')
    await expect(sendBtn).toBeDisabled()
  })

  test('清空按钮可重置 thread', async ({ page }) => {
    const textarea = page.getByPlaceholder(/和 市场研究员 说点什么/)
    await textarea.fill('你好')
    await page.getByRole('button', { name: '发送' }).click()
    await expect(page.getByText('你好').first()).toBeVisible({ timeout: 10000 })

    const clearBtn = page.getByRole('button', { name: '清空' })
    await expect(clearBtn).toBeEnabled()
    await clearBtn.click()

    // 回到空状态
    await expect(page.getByText('和 市场研究员 开始对话')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/对话 · 0 条/)).toBeVisible()
  })

  test('空状态可点击 sample 提问回填到 textarea', async ({ page }) => {
    const sample = page.getByRole('button', { name: /请帮我：行业研究/ })
    await expect(sample).toBeVisible()
    await sample.click()

    await expect(page.getByPlaceholder(/和 市场研究员 说点什么/)).toHaveValue(/请帮我：行业研究/)
  })
})
