/**
 * ⚖️ 法律顾问 — capability 触发（P14-A）
 *
 * 法律顾问核心 capability：法律咨询（基于业务上下文给可执行建议）
 *
 * Acceptance Criteria：
 *   - AC1: 工作台右栏 "能力清单（5）" + 5 条 capability 全部可见
 *   - AC2: 选中"法律咨询" → 触发后 chat 流出现 user 触发指令 + assistant 回复
 *   - AC3: assistant 回复必含免责声明（合规要求）
 *   - AC4: assistant 回复必引用具体法条（如《劳动合同法》）
 *   - AC5: chat request body 中带 extra.capability = "法律咨询"
 *   - AC6: 触发"风险评估"时同样满足免责声明 + extra 字段
 *
 * TODO(前端补 testid)：
 *   - PersonaCapabilityRunner 缺 data-testid
 *   - 触发按钮缺 data-testid="persona-capability-trigger"
 *   - assistant 免责声明 span 缺 data-testid="persona-disclaimer"
 */

import { expect, test } from '@playwright/test'

import { setupPersonaSession } from '../_helpers/persona'

test.describe('⚖️ 法律顾问 - capability 触发', () => {
  test.setTimeout(30_000)

  test.beforeEach(async ({ page }) => {
    await setupPersonaSession(page)
    await page.goto('/v3/personas/legal_advisor')
    await expect(
      page.getByRole('heading', { name: '法律顾问', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })
  })

  test('AC1: 右栏渲染 5 条 capability', async ({ page }) => {
    await expect(page.getByText('能力清单（5）')).toBeVisible()
    await expect(page.getByRole('button', { name: /法规检索/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /法律咨询/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /风险评估/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /法规监测/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /判例检索/ })).toBeVisible()
  })

  test('AC2 + AC3 + AC4: 触发"法律咨询" → 回复含法条 + 免责声明', async ({ page }) => {
    await page.getByRole('button', { name: /法律咨询/ }).click()
    await expect(page.getByText(/将触发：/)).toBeVisible()

    // 在 textarea 填写业务上下文
    await page
      .getByPlaceholder(/可选：贴入你的输入/)
      .fill('员工试用期 5 个月，劳动合同期 18 个月，是否合规？')

    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    // user 触发消息进入 chat 流
    await expect(page.getByText(/请帮我执行：法律咨询/)).toBeVisible({ timeout: 5_000 })
    await expect(
      page.getByText(/员工试用期 5 个月.*劳动合同期 18 个月/),
    ).toBeVisible()

    // assistant 回复 — 法条引用
    await expect(page.getByText(/《劳动合同法》/)).toBeVisible({ timeout: 5_000 })
    // 免责声明（mock 默认 legal_advisor 回复必含）
    await expect(page.getByText(/免责声明/)).toBeVisible()
    await expect(page.getByText(/不构成正式法律意见/)).toBeVisible()
    await expect(page.getByText(/请咨询执业律师/)).toBeVisible()
  })

  test('AC5: 触发 chat 时 request body 含 extra.capability', async ({ page }) => {
    type ChatBody = { message?: string; extra?: { capability?: string } }
    const captured: { body: ChatBody | null } = { body: null }

    await page.route('**/api/v1/personas/legal_advisor/chat', async (route) => {
      const body = route.request().postDataJSON() as ChatBody
      captured.body = body
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          persona_id: 'legal_advisor',
          content:
            '⚖️ 法律顾问：根据《劳动合同法》第十九条……\n\n免责声明：本回答不构成正式法律意见。',
          metadata: { mock: true, capability: body?.extra?.capability },
        }),
      })
    })

    await page.getByRole('button', { name: /法律咨询/ }).click()
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/根据《劳动合同法》第十九条/)).toBeVisible({
      timeout: 5_000,
    })

    expect(captured.body).not.toBeNull()
    expect(captured.body?.extra?.capability).toBe('法律咨询')
    expect(captured.body?.message ?? '').toContain('请帮我执行：法律咨询')
  })

  test('AC6: 触发"风险评估" — 同样满足免责声明', async ({ page }) => {
    await page.getByRole('button', { name: /风险评估/ }).click()
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/请帮我执行：风险评估/)).toBeVisible({ timeout: 5_000 })
    // mock 对 legal_advisor 的所有 chat 都注入免责声明
    await expect(page.getByText(/免责声明/)).toBeVisible({ timeout: 5_000 })
    await expect(page.getByText(/请咨询执业律师/)).toBeVisible()
  })
})
