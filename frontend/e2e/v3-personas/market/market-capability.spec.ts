/**
 * P14-D 市场研究员 — Capability 触发 spec
 *
 * 注：v3 P8-C 阶段，capability 通过 PersonaCapabilityRunner 统一触发，
 * 走通用 /personas/{id}/chat endpoint 把 "请帮我执行：X" 发到对话。
 *
 * 调研公司 / DeepResearch 迭代 timeline / 竞品矩阵卡 等专属 UI（ResearchReport
 * 含 citation 列表、迭代 timeline、竞品矩阵卡）尚未实装 —— 本 spec 验证
 * "能力被正确触发并送达通用 chat 端点"，并标记 TODO 待专属 endpoint 落地后扩展。
 */

import { expect, test, type Page, type Request } from '@playwright/test'

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
    'PDF 深读（RAG-Anything + MinerU 解析图表 / 公式）',
    '客户洞察（客户公司画像 + 决策链分析）',
  ],
  backed_by_skills: ['research/deeptutor-mode', 'research/citation-trace'],
  supported_apps: ['reddit', 'x', 'linkedin'],
}

const capturedChat: Array<{ message: string; capability?: string }> = []

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
          system_prompt_excerpt: '…',
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
    const body = JSON.parse(route.request().postData() ?? '{}') as {
      message?: string
      extra?: { capability?: string }
    }
    capturedChat.push({
      message: body.message ?? '',
      capability: body.extra?.capability,
    })
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'market_researcher',
        content: `📊 **市场研究员**：已触发能力「${body.extra?.capability ?? '未知'}」\n\n（本 mock 占位 —— 待专属 endpoint 渲染 ResearchReport / citations / timeline）`,
        metadata: { mock: true, is_implemented: true, capability: body.extra?.capability },
      }),
    })
  })
}

test.describe('P14-D · 📊 市场研究员 · Capability', () => {
  test.beforeEach(async ({ page }) => {
    capturedChat.length = 0
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

  test('调研公司：选行业研究 → 输入公司名 → 触发并送达 chat 端点', async ({ page }) => {
    // 选 capability "行业研究"
    await page.getByRole('button', { name: /行业研究/ }).click()
    // 触发提示
    await expect(page.getByText(/将触发：/)).toBeVisible()

    // 输入公司名
    await page.getByPlaceholder(/可选：贴入你的输入/).fill('Notion AI')
    const triggerBtn = page.getByRole('button', { name: '触发并发送到对话' })
    await expect(triggerBtn).toBeEnabled()

    // 触发 + 等待请求
    const [chatReq] = await Promise.all([
      page.waitForRequest(
        (r: Request) => r.url().includes('/personas/market_researcher/chat') && r.method() === 'POST',
      ),
      triggerBtn.click(),
    ])

    const sentBody = JSON.parse(chatReq.postData() ?? '{}') as {
      message?: string
      extra?: { capability?: string }
    }
    expect(sentBody.message).toContain('行业研究')
    expect(sentBody.message).toContain('Notion AI')
    expect(sentBody.extra?.capability).toBe('行业研究')

    // assistant 回复落到左侧 chat
    await expect(page.getByText(/已触发能力「行业研究」/)).toBeVisible({ timeout: 10000 })

    // TODO[P14-future]: 待 ResearchReport + citation 列表 UI 落地后，断言：
    //   await expect(page.getByTestId('research-report')).toBeVisible()
    //   await expect(page.getByTestId('citation-list').locator('li')).toHaveCount(>0)
  })

  test('DeepResearch：选 PDF 深读 → 输入复杂问题 → 触发', async ({ page }) => {
    await page.getByRole('button', { name: /PDF 深读/ }).click()
    await page.getByPlaceholder(/可选：贴入你的输入/).fill(
      '请基于这份 200 页年报，分析其在 AI 战略上 3 年内的资本支出曲线变化',
    )

    const [req] = await Promise.all([
      page.waitForRequest(
        (r: Request) => r.url().includes('/personas/market_researcher/chat') && r.method() === 'POST',
      ),
      page.getByRole('button', { name: '触发并发送到对话' }).click(),
    ])
    const sent = JSON.parse(req.postData() ?? '{}') as { extra?: { capability?: string } }
    expect(sent.extra?.capability).toBe('PDF 深读')

    await expect(page.getByText(/已触发能力「PDF 深读」/)).toBeVisible({ timeout: 10000 })

    // TODO[P14-future]: 待 DeepResearch 迭代步骤 timeline UI 落地后，断言：
    //   await expect(page.getByTestId('research-iteration-timeline')).toBeVisible()
    //   await expect(page.getByTestId('research-conclusion')).toBeVisible()
  })

  test('竞品监控：选竞品监控 capability 后可触发并出现 chat 回执', async ({ page }) => {
    await page.getByRole('button', { name: /竞品监控/ }).click()
    await expect(page.getByText(/将触发：/)).toBeVisible()

    await page.getByRole('button', { name: '触发并发送到对话' }).click()

    await expect(page.getByText(/已触发能力「竞品监控」/)).toBeVisible({ timeout: 10000 })

    // TODO[P14-future]: 待竞品矩阵卡 UI（CompetitorMatrixCard）落地后，断言：
    //   await expect(page.getByTestId('competitor-matrix-card')).toBeVisible()
  })

  test('未选能力时触发按钮 disabled，提示先选能力', async ({ page }) => {
    const triggerBtn = page.getByRole('button', { name: '触发并发送到对话' })
    await expect(triggerBtn).toBeDisabled()
    await expect(page.getByText(/在上方选一项能力/)).toBeVisible()
  })
})
