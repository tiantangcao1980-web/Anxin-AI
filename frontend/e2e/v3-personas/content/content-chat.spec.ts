/**
 * V3 Persona E2E — ✍️ 内容总监 · 通用对话 (P14-E)
 *
 * 走通用 chat 端点：POST /api/v1/personas/content_director/chat
 *
 * 关键 assert：
 *   - 工作台顶部显示「内容总监」+ 描述
 *   - 输入框 placeholder 含 persona 名
 *   - 发送一句话 → 看到用户气泡 + assistant 气泡（mock 文本）
 *   - 「清空」按钮可重置历史
 */

import { expect, test, type Page, type Route } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA = {
  persona_id: 'content_director',
  display_name: '内容总监',
  emoji: '✍️',
  description: '从一句话灵感到一支成片，全链路内容生产',
  domain: '增长获客',
  is_implemented: true,
  enabled: true,
  capabilities: [
    '图文创作（公众号 / 知乎 / 小红书 / 头条 多平台适配）',
    '短视频脚本 + 成片',
    '品牌一致性检查',
  ],
  backed_by_skills: ['content/article-write', 'content/headline-generate'],
  supported_apps: ['canvas-design', '微信公众号'],
}

async function installContentMocks(page: Page, opts: { reply?: string } = {}) {
  await page.route('**/api/v1/personas', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [PERSONA], total: 1 }),
    })
  })

  await page.route('**/api/v1/personas/content_director', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...PERSONA,
        backed_by_agents: ['content_agent'],
        system_prompt_excerpt: '你是「内容总监」persona。',
      }),
    })
  })

  await page.route('**/api/v1/personas/content_director/chat', async (route: Route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'content_director',
        content:
          opts.reply ?? '✍️ **内容总监**：已收到你的内容创作需求，正在为你拟稿……',
        metadata: { mock: true, is_implemented: true },
      }),
    })
  })
}

test.describe('V3 / persona 对话 / ✍️ 内容总监', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only — 双栏工作台')
    await installApiMocks(page)
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-content',
      name: '内容总监 E2E',
      email: 'content@example.com',
    })
  })

  test('工作台顶部正确渲染 persona 头像 / 名称 / 描述', async ({ page }) => {
    await installContentMocks(page)
    await page.goto('/v3/personas/content_director')

    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('从一句话灵感到一支成片', { exact: false })).toBeVisible()
    await expect(page.getByText('已实装').first()).toBeVisible()
  })

  test('发送一句话可看到用户气泡和 assistant 回复', async ({ page }) => {
    await installContentMocks(page, {
      reply: '✍️ 内容总监：我建议从「场景化标题」入手，先列 3 个候选标题供你挑选。',
    })
    await page.goto('/v3/personas/content_director')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    const input = page.getByPlaceholder(/和 内容总监 说点什么/)
    await input.fill('帮我写一篇公众号文章，主题：AI 智能助手')
    await page.getByRole('button', { name: /发送/ }).click()

    // 用户气泡
    await expect(page.getByText('帮我写一篇公众号文章')).toBeVisible({ timeout: 6000 })
    // assistant 气泡（mock 文本）
    await expect(page.getByText('场景化标题', { exact: false })).toBeVisible({ timeout: 6000 })
  })

  test('对话历史可被「清空」按钮重置', async ({ page }) => {
    await installContentMocks(page, { reply: '✍️ 已收到内容需求' })
    await page.goto('/v3/personas/content_director')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    const input = page.getByPlaceholder(/和 内容总监 说点什么/)
    await input.fill('你好')
    await page.getByRole('button', { name: /发送/ }).click()

    await expect(page.getByText('已收到内容需求', { exact: false })).toBeVisible({ timeout: 6000 })

    await page.getByRole('button', { name: /清空/ }).click()
    await expect(page.getByText('已收到内容需求', { exact: false })).toHaveCount(0)
  })

  test('未输入时发送按钮处于禁用态', async ({ page }) => {
    await installContentMocks(page)
    await page.goto('/v3/personas/content_director')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    const sendBtn = page.getByRole('button', { name: /发送/ })
    await expect(sendBtn).toBeDisabled()
  })
})
