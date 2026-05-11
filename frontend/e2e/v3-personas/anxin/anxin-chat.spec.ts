/**
 * 🤖 安心助理 — 工作台 chat（P14-A）
 *
 * Acceptance Criteria：
 *   - AC1: 工作台 chat 面板渲染 + 顶部条 "与 安心助理 对话 · 0 条"
 *   - AC2: 输入消息发送后，会话列表出现 user 气泡 + assistant 回复
 *   - AC3: assistant 回复内容来自 mock（含 emoji 🤖 + display_name）
 *   - AC4: 切换到其它 persona 后回到本 persona，原会话仍在
 *   - AC5: 触发 chat API 错误后，会话区显示"❌ 调用失败"占位
 *   - AC6: "清空" 按钮把当前线程会话清空
 *
 * TODO(前端补 testid)：
 *   - PersonaChatPanel 缺 data-testid="persona-chat-panel"
 *   - chat textarea 缺 data-testid="persona-chat-input"
 *   - 发送按钮缺 data-testid="persona-chat-send"
 *   - assistant 气泡缺 data-testid="persona-chat-msg-assistant"
 */

import { expect, test } from '@playwright/test'

import { setupPersonaSession } from '../_helpers/persona'

test.describe('🤖 安心助理 - chat 面板', () => {
  test.setTimeout(30_000)

  test.beforeEach(async ({ page }) => {
    await setupPersonaSession(page)
    await page.goto('/v3/personas/anxin_assistant')
    await expect(
      page.getByRole('heading', { name: '安心助理', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })
  })

  test('AC1: 工作台渲染 chat 面板 + 空线程提示', async ({ page }) => {
    await expect(page.getByText(/与.*安心助理.*对话.*0 条/)).toBeVisible()
    // 空状态引导卡片
    await expect(page.getByText(/和 安心助理 开始对话/)).toBeVisible()
    // textarea 存在
    await expect(page.getByPlaceholder(/和 安心助理 说点什么/)).toBeVisible()
  })

  test('AC2 + AC3: 发送消息后看到 user 气泡 + assistant 回复（mock 内容）', async ({ page }) => {
    const textarea = page.getByPlaceholder(/和 安心助理 说点什么/)
    await textarea.fill('我们公司想签一份新合同，应该找谁？')

    await page.getByRole('button', { name: /^发送$/ }).click()

    // user 消息回显
    await expect(
      page.getByText('我们公司想签一份新合同，应该找谁？'),
    ).toBeVisible({ timeout: 5_000 })
    // assistant 回复（mock 默认会带"识别到您的意图"）
    await expect(page.getByText(/识别到您的意图/)).toBeVisible({ timeout: 5_000 })
    // 顶部计数从 0 变为 2（user + assistant）
    await expect(page.getByText(/与.*安心助理.*对话.*2 条/)).toBeVisible()
  })

  test('AC4: 切到法律顾问再回安心助理，原会话仍在（store 按 persona 分线程）', async ({ page }) => {
    // 先在安心助理发一条
    await page.getByPlaceholder(/和 安心助理 说点什么/).fill('hello anxin')
    await page.getByRole('button', { name: /^发送$/ }).click()
    await expect(page.getByText('hello anxin')).toBeVisible({ timeout: 5_000 })

    // 用顶部"切换"下拉切到法律顾问
    await page.getByRole('button', { name: /^切换/ }).click()
    await page.getByRole('menuitem', { name: /法律顾问/ }).click()
    await expect(page).toHaveURL(/\/v3\/personas\/legal_advisor/)
    await expect(
      page.getByRole('heading', { name: '法律顾问', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })

    // 切回安心助理
    await page.goto('/v3/personas/anxin_assistant')
    await expect(
      page.getByRole('heading', { name: '安心助理', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })

    // 原 user 消息还在
    await expect(page.getByText('hello anxin')).toBeVisible()
  })

  test('AC5: chat API 报错时显示"❌ 调用失败"占位 assistant 气泡', async ({ page, context }) => {
    // 重新构造一个失败 chat 的 session
    await context.clearCookies()
    await page.goto('about:blank')
    await setupPersonaSession(page, { failChat: true })
    await page.goto('/v3/personas/anxin_assistant')
    await expect(
      page.getByRole('heading', { name: '安心助理', level: 1 }),
    ).toBeVisible({ timeout: 10_000 })

    await page.getByPlaceholder(/和 安心助理 说点什么/).fill('触发失败')
    await page.getByRole('button', { name: /^发送$/ }).click()

    await expect(page.getByText(/❌ 调用失败/)).toBeVisible({ timeout: 5_000 })
  })

  test('AC6: 清空按钮把当前线程清空', async ({ page }) => {
    // 先发一条
    await page.getByPlaceholder(/和 安心助理 说点什么/).fill('稍后清空')
    await page.getByRole('button', { name: /^发送$/ }).click()
    await expect(page.getByText('稍后清空')).toBeVisible({ timeout: 5_000 })

    // 清空
    await page.getByRole('button', { name: /^清空$/ }).click()
    await expect(page.getByText(/与.*安心助理.*对话.*0 条/)).toBeVisible()
    await expect(page.getByText('稍后清空')).toHaveCount(0)
  })
})
