/**
 * 🤖 安心助理 — capability 触发（P14-A）
 *
 * 安心助理核心 capability：意图识别（自然语言路由到正确 persona）
 *
 * Acceptance Criteria：
 *   - AC1: 工作台右栏显示 capability 清单（5 条 + 已实装/规划中状态）
 *   - AC2: 选中"意图识别"后右下方显示"将触发：意图识别"
 *   - AC3: 触发按钮发起 chat → assistant 回复出现在左侧 chat 流
 *   - AC4: 安心助理是规划中状态，capability 列表项徽章显示"规划中"
 *   - AC5: 触发后 chat metadata 中带 capability 字段（验证 request body）
 *
 * TODO(前端补 testid)：
 *   - PersonaCapabilityRunner 缺 data-testid="persona-capability-runner"
 *   - 触发按钮缺 data-testid="persona-capability-trigger"
 *   - 每条 capability 按钮缺 data-testid="persona-capability-item-{name}"
 */

import { expect, test } from '@playwright/test'

import { setupPersonaSession } from '../_helpers/persona'

test.describe('🤖 安心助理 - capability 触发', () => {
  test.setTimeout(30_000)

  test.beforeEach(async ({ page }) => {
    await setupPersonaSession(page)
    await page.goto('/v3/personas/anxin_assistant')
    await expect(
      page.getByRole('heading', { name: '安心助理', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })
  })

  test('AC1: 右栏显示 5 条 capability + "能力清单（5）" 标题', async ({ page }) => {
    await expect(page.getByText('能力清单（5）')).toBeVisible()
    await expect(page.getByRole('button', { name: /意图识别/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /任务拆解/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /多 agent 协商/ })).toBeVisible()
  })

  test('AC2: 选中"意图识别"后下方提示"将触发"', async ({ page }) => {
    await page.getByRole('button', { name: /意图识别/ }).click()
    await expect(page.getByText(/将触发：/)).toBeVisible()
    // chip 内显示能力名称（截断到 "（" 之前）
    await expect(
      page.getByText('意图识别', { exact: true }).first(),
    ).toBeVisible()
  })

  test('AC3: 触发"意图识别"后 chat 流出现 user + assistant 消息', async ({ page }) => {
    await page.getByRole('button', { name: /意图识别/ }).click()

    // 触发按钮（"触发并发送到对话"）
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    // chat 中出现 user 触发消息
    await expect(page.getByText(/请帮我执行：意图识别/)).toBeVisible({ timeout: 5_000 })
    // assistant 回复 mock 内容（含"识别到您的意图" + 推荐 persona）
    await expect(page.getByText(/识别到您的意图/)).toBeVisible({ timeout: 5_000 })
    await expect(page.getByText(/推荐 persona/)).toBeVisible()
    await expect(page.getByText(/法律顾问.*法规咨询/)).toBeVisible()
  })

  test('AC4: 安心助理（规划中）— capability 列表徽章显示"规划中"', async ({ page }) => {
    // 规划中提示出现在 chat 输入区下方 + capability 列表上
    await expect(
      page.getByText(/该 persona 后端尚未实装.*前端 mock 占位应答/),
    ).toBeVisible()
    // 至少 1 个"规划中"徽章在右栏 capability 列表
    await expect(page.getByText('规划中').first()).toBeVisible()
  })

  test('AC5: 触发 chat 时 request body 含 capability extra 字段', async ({ page }) => {
    // 拦截一次 chat 请求，断言 body 含 extra.capability
    type ChatBody = { message?: string; extra?: { capability?: string } }
    const captured: { body: ChatBody | null } = { body: null }

    await page.route('**/api/v1/personas/anxin_assistant/chat', async (route) => {
      const body = route.request().postDataJSON() as ChatBody
      captured.body = body
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          persona_id: 'anxin_assistant',
          content: '🤖 mock 已收到 capability 触发',
          metadata: { mock: true, capability: body?.extra?.capability },
        }),
      })
    })

    await page.getByRole('button', { name: /意图识别/ }).click()
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/mock 已收到 capability 触发/)).toBeVisible({ timeout: 5_000 })

    expect(captured.body).not.toBeNull()
    expect(captured.body?.extra?.capability).toBe('意图识别')
    expect(captured.body?.message ?? '').toContain('请帮我执行：意图识别')
  })
})
