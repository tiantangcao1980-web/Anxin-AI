/**
 * V3 Persona E2E — ✍️ 内容总监 · 发现 (P14-E)
 *
 * 入口路径：/agents → 看到 persona 卡 → 点「进入工作台」→ /v3/personas/content_director
 *
 * 这一族 spec 自包含 mock：
 *   - 通用 /api/** mock 来自 helpers/session（auth/me、notifications 等）
 *   - 额外为 /personas、/personas/{id}、/personas/{id}/chat 三个端点补 mock
 *     （helpers/session 内置 mock 不覆盖 personas 域）。
 *
 * 关键 assert：
 *   - "内容总监" 卡片可见
 *   - 卡片有"已实装"徽章
 *   - 显示 emoji ✍️ 和 业务域 "增长获客"
 *   - 点击 → 跳到工作台
 */

import { expect, test, type Page, type Route } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const CONTENT_PERSONA = {
  persona_id: 'content_director',
  display_name: '内容总监',
  emoji: '✍️',
  description: '从一句话灵感到一支成片，全链路内容生产',
  domain: '增长获客',
  is_implemented: true,
  enabled: true,
  capabilities: [
    '图文创作（公众号 / 知乎 / 小红书 / 头条 多平台适配）',
    '视觉设计（海报 / 封面 / Banner via canvas-design）',
    '短视频脚本 + 成片（脚本 → 分镜 → Remotion 自动剪辑）',
    '落地页生成（web-artifacts-builder 一键生成产品页）',
    '文案矩阵（标题 / 钩子 / 卖点 多版本 A/B）',
    '品牌一致性检查（VI / tone / 合规 红线）',
    '本地化（多语种 + 文化适配）',
  ],
  backed_by_skills: [
    'content/article-write',
    'content/headline-generate',
    'design/poster',
    'content/video-script',
  ],
  supported_apps: ['canvas-design', 'figma', 'canva', 'remotion', '微信公众号', '抖音'],
}

const OTHER_PERSONA_STUB = {
  persona_id: 'operations_manager',
  display_name: '流程管家',
  emoji: '📋',
  description: '公司过程管理小助手',
  domain: '合规经营',
  is_implemented: true,
  enabled: true,
  capabilities: ['OKR 管理'],
  backed_by_skills: ['operations/okr-plan'],
  supported_apps: ['feishu'],
}

async function installPersonasMock(page: Page) {
  await page.route('**/api/v1/personas', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [CONTENT_PERSONA, OTHER_PERSONA_STUB],
        total: 2,
      }),
    })
  })

  await page.route('**/api/v1/personas/content_director', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...CONTENT_PERSONA,
        backed_by_agents: ['content_agent', 'design_agent'],
        system_prompt_excerpt:
          '你是「内容总监」persona — 从一句话灵感到一支成片，全链路内容生产。',
      }),
    })
  })
}

test.describe('V3 / persona 发现 / ✍️ 内容总监', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only — agents 卡片网格')
    await installApiMocks(page)
    await installPersonasMock(page)
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-content',
      name: '内容总监 E2E',
      email: 'content@example.com',
    })
  })

  test('在智能体中心可看到 ✍️ 内容总监卡片', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '智能体' })).toBeVisible({ timeout: 10000 })

    // 卡片显示 display_name + emoji + 描述
    const card = page.getByRole('heading', { name: '内容总监' })
    await expect(card).toBeVisible()
    await expect(page.getByText('从一句话灵感到一支成片', { exact: false })).toBeVisible()
    await expect(page.getByText('✍️').first()).toBeVisible()
  })

  test('卡片显示「已实装」状态徽章和「增长获客」业务域', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    // 已实装徽章
    await expect(page.getByText('已实装').first()).toBeVisible()
    // 业务域分组
    await expect(page.getByText('增长获客').first()).toBeVisible()
  })

  test('点击卡片「进入工作台」跳转到 /v3/personas/content_director', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    await page.getByRole('button', { name: /进入工作台/ }).first().click()
    await expect(page).toHaveURL(/\/v3\/personas\/content_director/, { timeout: 10000 })
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible()
  })

  test('搜索框可按关键词「内容」过滤出 ✍️ 内容总监', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible({ timeout: 10000 })

    await page.getByPlaceholder(/搜索 persona/).fill('内容')
    await expect(page.getByRole('heading', { name: '内容总监' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '流程管家' })).toHaveCount(0)
  })
})
