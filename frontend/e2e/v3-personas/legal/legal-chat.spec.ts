/**
 * ⚖️ 法律顾问 — chat 工作台（P14-A）
 *
 * Acceptance Criteria：
 *   - AC1: chat 面板渲染 + 顶部"与 法律顾问 对话 · 0 条"
 *   - AC2: 发送法律咨询问题后，assistant 回复带法条引用 + 免责声明
 *   - AC3: 输入框 Enter 直接发送（无 Shift）
 *   - AC4: chat history 在刷新页面后仍按 persona 维度保留（zustand 重置 → 0 条；
 *         本 case 验证当前会话内的内存持久性）
 *   - AC5: 切换到安心助理 → 法律顾问 thread 不会被污染
 *
 * TODO(前端补 testid)：
 *   - PersonaChatPanel 缺 data-testid="persona-chat-panel"
 *   - chat 输入区缺 data-testid="persona-chat-input"
 *   - 免责声明缺 data-testid="persona-chat-disclaimer"
 */

import { expect, test } from '@playwright/test'

import { setupPersonaSession } from '../_helpers/persona'

test.describe('⚖️ 法律顾问 - chat', () => {
  test.setTimeout(30_000)

  test.beforeEach(async ({ page }) => {
    await setupPersonaSession(page)
    await page.goto('/v3/personas/legal_advisor')
    await expect(
      page.getByRole('heading', { name: '法律顾问', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })
  })

  test('AC1: chat 面板初始空状态', async ({ page }) => {
    await expect(page.getByText(/与.*法律顾问.*对话.*0 条/)).toBeVisible()
    await expect(page.getByText(/和 法律顾问 开始对话/)).toBeVisible()
    await expect(page.getByPlaceholder(/和 法律顾问 说点什么/)).toBeVisible()
  })

  test('AC2: 法律咨询发送后，回复含法条引用 + 免责声明', async ({ page }) => {
    await page
      .getByPlaceholder(/和 法律顾问 说点什么/)
      .fill('劳动法规定试用期最长多久？')
    await page.getByRole('button', { name: /^发送$/ }).click()

    // user 消息
    await expect(page.getByText('劳动法规定试用期最长多久？')).toBeVisible({
      timeout: 5_000,
    })
    // assistant：法条引用
    await expect(page.getByText(/《劳动合同法》/)).toBeVisible({ timeout: 5_000 })
    // 免责声明（合规要求 — 法律意见必须有）
    await expect(page.getByText(/免责声明/)).toBeVisible()
    await expect(page.getByText(/不构成正式法律意见/)).toBeVisible()
  })

  test('AC3: Enter 键直接发送（无 Shift）', async ({ page }) => {
    const input = page.getByPlaceholder(/和 法律顾问 说点什么/)
    await input.fill('Enter 应该直接发送')
    await input.press('Enter')

    await expect(page.getByText('Enter 应该直接发送')).toBeVisible({
      timeout: 5_000,
    })
    // 顶部计数变 2（user + assistant）
    await expect(page.getByText(/与.*法律顾问.*对话.*2 条/)).toBeVisible()
  })

  test('AC4: 同一会话内多轮对话累计计数正确', async ({ page }) => {
    const input = page.getByPlaceholder(/和 法律顾问 说点什么/)

    await input.fill('问题 1')
    await page.getByRole('button', { name: /^发送$/ }).click()
    await expect(page.getByText(/与.*法律顾问.*对话.*2 条/)).toBeVisible({ timeout: 5_000 })

    await input.fill('问题 2')
    await page.getByRole('button', { name: /^发送$/ }).click()
    await expect(page.getByText(/与.*法律顾问.*对话.*4 条/)).toBeVisible({ timeout: 5_000 })

    // 两条 user 消息都还在
    await expect(page.getByText('问题 1')).toBeVisible()
    await expect(page.getByText('问题 2')).toBeVisible()
  })

  test('AC5: 切到安心助理再回来 — 法律顾问 thread 不被污染', async ({ page }) => {
    // 在法律顾问发一条
    await page
      .getByPlaceholder(/和 法律顾问 说点什么/)
      .fill('legal-only-marker')
    await page.getByRole('button', { name: /^发送$/ }).click()
    await expect(page.getByText('legal-only-marker')).toBeVisible({ timeout: 5_000 })

    // 跳到安心助理 → 应当是空线程
    await page.goto('/v3/personas/anxin_assistant')
    await expect(
      page.getByRole('heading', { name: '安心助理', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/与.*安心助理.*对话.*0 条/)).toBeVisible()
    await expect(page.getByText('legal-only-marker')).toHaveCount(0)

    // 回到法律顾问 → marker 仍在
    await page.goto('/v3/personas/legal_advisor')
    await expect(
      page.getByRole('heading', { name: '法律顾问', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('legal-only-marker')).toBeVisible()
  })
})
