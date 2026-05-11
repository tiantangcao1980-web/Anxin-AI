/**
 * P14-D 获客猎手 — Capability 触发 spec
 *
 * v3 P8-C 阶段：通过 PersonaCapabilityRunner 选 capability + 输入 →
 * 走通用 /personas/{id}/chat 端点（capability 名 + extra 输入拼到 message）。
 *
 * 专属 UI（lead 列表 + 评分 / 邮件 3 个 subject 变体 / 报价单 docx 下载入口）
 * 尚未在 v3 实装 —— 本 spec 验证 "能力被正确触发并送到 chat 端点"，并 TODO
 * 标记待专属 endpoint 落地后扩展。
 */

import { expect, test, type Page, type Request } from '@playwright/test'

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
    '投放决策（AI-Trader 范式，多 agent 协商出价）',
    '客户分层（RFM + 行为评分 + 优先级）',
  ],
  backed_by_skills: [
    'sales/lead-mining',
    'sales/vibe-selling',
    'sales/follow-up',
    'sales/quotation-draft',
  ],
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
          backed_by_agents: ['lead_agent', 'vibe_seller'],
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
    const body = JSON.parse(route.request().postData() ?? '{}') as {
      message?: string
      extra?: { capability?: string }
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'lead_hunter',
        content: `🎯 **获客猎手**：已触发能力「${body.extra?.capability ?? '未知'}」\n\n（mock 占位 —— 待专属 endpoint 渲染 lead 列表 / 邮件变体 / docx 下载）`,
        metadata: { mock: true, is_implemented: true, capability: body.extra?.capability },
      }),
    })
  })
}

test.describe('P14-D · 🎯 获客猎手 · Capability', () => {
  test.beforeEach(async ({ page }) => {
    await installApiMocks(page)
    await installPersonaMocks(page)
    await seedAuthState(page, {
      role: 'admin',
      userId: 'e2e-sales',
      name: 'E2E Sales',
      email: 'sales@anxinfawu.com',
    })
    await page.goto('/v3/personas/lead_hunter')
    await expect(page.getByRole('heading', { name: '获客猎手', level: 1 })).toBeVisible({ timeout: 15000 })
  })

  test('发现潜在客户：选线索挖掘 → 输入行业+地区 → 触发', async ({ page }) => {
    await page.getByRole('button', { name: /线索挖掘/ }).click()
    await expect(page.getByText(/将触发：/)).toBeVisible()

    await page.getByPlaceholder(/可选：贴入你的输入/).fill('行业：跨境电商 SaaS\n地区：深圳 + 上海')

    const [chatReq] = await Promise.all([
      page.waitForRequest(
        (r: Request) => r.url().includes('/personas/lead_hunter/chat') && r.method() === 'POST',
      ),
      page.getByRole('button', { name: '触发并发送到对话' }).click(),
    ])
    const sent = JSON.parse(chatReq.postData() ?? '{}') as {
      message?: string
      extra?: { capability?: string }
    }
    expect(sent.message).toContain('线索挖掘')
    expect(sent.message).toContain('跨境电商 SaaS')
    expect(sent.extra?.capability).toBe('线索挖掘')

    await expect(page.getByText(/已触发能力「线索挖掘」/)).toBeVisible({ timeout: 10000 })

    // TODO[P14-future]: 待 lead 列表 + 评分 UI 落地后，断言：
    //   await expect(page.getByTestId('lead-list')).toBeVisible()
    //   await expect(page.getByTestId('lead-list').locator('[data-testid="lead-row"]')).toHaveCount(>0)
    //   await expect(page.getByTestId('lead-row').first().getByTestId('lead-score')).toBeVisible()
  })

  test('起草跟进邮件：选跟进策略 → 选 lead+模板 → 触发', async ({ page }) => {
    await page.getByRole('button', { name: /跟进策略/ }).click()
    await page.getByPlaceholder(/可选：贴入你的输入/).fill(
      'Lead: 字节跳动 - CTO\n模板: 二次跟进 / 价值升级',
    )

    const [req] = await Promise.all([
      page.waitForRequest(
        (r: Request) => r.url().includes('/personas/lead_hunter/chat') && r.method() === 'POST',
      ),
      page.getByRole('button', { name: '触发并发送到对话' }).click(),
    ])
    const sent = JSON.parse(req.postData() ?? '{}') as { extra?: { capability?: string } }
    expect(sent.extra?.capability).toBe('跟进策略')

    await expect(page.getByText(/已触发能力「跟进策略」/)).toBeVisible({ timeout: 10000 })

    // TODO[P14-future]: 待邮件 3 个 subject 变体 UI 落地后，断言：
    //   await expect(page.getByTestId('email-subject-variant')).toHaveCount(3)
  })

  test('生成报价单：选投放决策 → 填明细 → 触发', async ({ page }) => {
    // 注：v3 当前 capability 列表无 "生成报价单"；用最相近的 "投放决策"
    // (由 sales/quotation-draft skill 背书) 触发，待专属 endpoint 落地后细化
    await page.getByRole('button', { name: /投放决策/ }).click()
    await page.getByPlaceholder(/可选：贴入你的输入/).fill(
      '产品：企业 IP 律师套餐\n数量：12 个月\n折扣：8.5 折',
    )

    const [req] = await Promise.all([
      page.waitForRequest(
        (r: Request) => r.url().includes('/personas/lead_hunter/chat') && r.method() === 'POST',
      ),
      page.getByRole('button', { name: '触发并发送到对话' }).click(),
    ])
    const sent = JSON.parse(req.postData() ?? '{}') as { extra?: { capability?: string } }
    expect(sent.extra?.capability).toBe('投放决策')

    await expect(page.getByText(/已触发能力「投放决策」/)).toBeVisible({ timeout: 10000 })

    // TODO[P14-future]: 待 docx 下载入口 UI 落地后，断言：
    //   await expect(page.getByTestId('quotation-docx-download')).toBeVisible()
    //   await expect(page.getByRole('link', { name: /下载 .*\.docx/ })).toBeVisible()
  })

  test('未选能力时触发按钮 disabled', async ({ page }) => {
    const triggerBtn = page.getByRole('button', { name: '触发并发送到对话' })
    await expect(triggerBtn).toBeDisabled()
    await expect(page.getByText(/在上方选一项能力/)).toBeVisible()
  })
})
