/**
 * V3 Persona E2E — ✍️ 内容总监 · 能力触发器 (P14-E)
 *
 * 流程：在右侧 CapabilityRunner 选一项能力 → 输入参数 → 触发 → 发送到对话流
 *
 * P14-E 要求覆盖三类能力：
 *   1. 起草公众号文章 → 选主题 → 看到 3 标题选项 + 正文预览
 *   2. 短视频脚本 → TikTok 30s → 看到分镜列表
 *   3. 品牌一致性检查 → 输入文本 → 看到合规分 + issues + "需人工 review" 锁
 *
 * 由于真实 capability endpoint 因子繁多（P14-E 仅 spec 阶段），
 * 这组 spec 走通用 chat 端点（CapabilityRunner 当前实现），
 * 用 mock 在 chat response 中返回结构化文本，验证：
 *   - 能力清单 list 可点击
 *   - 选中后下方有触发输入区
 *   - 触发后看到 mock 回的关键字段（标题 / 分镜 / 合规分）
 */

import { expect, test, type Page, type Route } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA = {
  persona_id: 'content_director',
  display_name: '内容总监',
  emoji: '✍️',
  description: '从一句话灵感到一支成片',
  domain: '增长获客',
  is_implemented: true,
  enabled: true,
  capabilities: [
    '起草公众号文章',
    '短视频脚本',
    '品牌一致性检查',
    '本地化（多语种）',
  ],
  backed_by_skills: ['content/article-write', 'content/video-script'],
  supported_apps: ['canvas-design', '微信公众号', '抖音'],
}

interface ChatRouteOptions {
  /** chat 回复体内容 */
  reply: string
}

async function installContentMocks(page: Page, opts: ChatRouteOptions) {
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
        content: opts.reply,
        metadata: { mock: true, is_implemented: true },
      }),
    })
  })
}

test.describe('V3 / persona 能力触发 / ✍️ 内容总监', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only — 三栏 capability runner')
    await installApiMocks(page)
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-content',
      name: '内容总监 E2E',
      email: 'content@example.com',
    })
  })

  test('起草公众号文章：触发后看到 3 标题选项 + 正文预览', async ({ page }) => {
    await installContentMocks(page, {
      reply: [
        '✍️ **公众号文章** — 已为你生成 3 个候选标题：',
        '',
        '1. 【标题候选 A】AI 让法务变得简单',
        '2. 【标题候选 B】每个老板都该有一个 AI 智能助手',
        '3. 【标题候选 C】合同审查只要 30 秒',
        '',
        '**正文预览：** 在 AI 时代，企业法务正在被重新定义……',
      ].join('\n'),
    })
    await page.goto('/v3/personas/content_director')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    // 在 capability list 选「起草公众号文章」
    await page.getByRole('button', { name: /起草公众号文章/ }).click()
    await expect(page.getByText(/将触发：/)).toBeVisible()

    // 填补充输入并触发
    await page.getByPlaceholder(/可选：贴入你的输入/).fill('主题：AI 智能助手，目标读者：中小企业老板')
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    // 验证 mock 返回的 3 标题候选都出现
    await expect(page.getByText(/标题候选 A/)).toBeVisible({ timeout: 6000 })
    await expect(page.getByText(/标题候选 B/)).toBeVisible()
    await expect(page.getByText(/标题候选 C/)).toBeVisible()
    await expect(page.getByText(/正文预览/)).toBeVisible()
  })

  test('短视频脚本：选 TikTok 30s → 看到分镜列表', async ({ page }) => {
    await installContentMocks(page, {
      reply: [
        '🎬 **短视频脚本 — TikTok 30 秒**',
        '',
        '**分镜 1（0-5s）：** Hook — 老板皱眉看合同',
        '**分镜 2（5-15s）：** 痛点 — "审一份合同要 2 小时"',
        '**分镜 3（15-25s）：** 转折 — AI 智能助手 30 秒出审查报告',
        '**分镜 4（25-30s）：** CTA — 扫码体验',
      ].join('\n'),
    })
    await page.goto('/v3/personas/content_director')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: /短视频脚本/ }).click()
    await page.getByPlaceholder(/可选：贴入你的输入/).fill('平台：TikTok，时长：30s，主题：AI 智能助手')
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/分镜 1/)).toBeVisible({ timeout: 6000 })
    await expect(page.getByText(/分镜 2/)).toBeVisible()
    await expect(page.getByText(/分镜 3/)).toBeVisible()
    await expect(page.getByText(/分镜 4/)).toBeVisible()
  })

  test('品牌一致性检查：输入文本 → 看到合规分 + issues + 需人工 review 锁', async ({ page }) => {
    await installContentMocks(page, {
      reply: [
        '🛡️ **品牌一致性检查报告**',
        '',
        '**合规分：** 72 / 100',
        '',
        '**Issues（3 项）：**',
        '- ❌ 标题与品牌 tone 不符（建议改为更稳重的措辞）',
        '- ⚠️ 包含可能引发监管风险的表述（"包治百病"）',
        '- ⚠️ 未引用必要的免责声明',
        '',
        '🔒 **需人工 review** — 当前合规分低于 80，已自动锁定，待品牌负责人审核后方可发布。',
      ].join('\n'),
    })
    await page.goto('/v3/personas/content_director')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: /品牌一致性检查/ }).click()
    await page.getByPlaceholder(/可选：贴入你的输入/).fill('我们的 AI 智能助手产品包治百病，效率提升 1000%。')
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/合规分.*72/)).toBeVisible({ timeout: 6000 })
    await expect(page.getByText(/Issues/)).toBeVisible()
    await expect(page.getByText(/需人工 review/)).toBeVisible()
  })

  test('未选能力时点击触发会被禁用', async ({ page }) => {
    await installContentMocks(page, { reply: '不应被调用' })
    await page.goto('/v3/personas/content_director')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    const triggerBtn = page.getByRole('button', { name: /触发并发送到对话/ })
    await expect(triggerBtn).toBeDisabled()
  })
})
