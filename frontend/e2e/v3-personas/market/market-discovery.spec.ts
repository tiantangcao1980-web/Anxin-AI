/**
 * P14-D 市场研究员 — 发现 / 进入工作台 spec
 *
 * 路径覆盖：/agents → 找到 📊 市场研究员卡片 → 点 "进入工作台"
 *           → /v3/personas/market_researcher，验证布局 + 状态徽章。
 *
 * 仅前端断言：通用 /personas* endpoint 在本 spec 内 inline mock，
 * 不依赖后端 P7-B 真实装。
 */

import { expect, test, type Page } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const MARKET_PERSONA = {
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
  backed_by_skills: [
    'research/deeptutor-mode',
    'research/multi-source-synthesize',
    'research/citation-trace',
    'research/competitive-monitor',
    'intelligence/news-aggregate',
    'intelligence/social-listen',
  ],
  supported_apps: ['reddit', 'x', 'linkedin', 'youtube', 'tiktok', 'headlessx'],
}

async function installPersonaMocks(page: Page) {
  await page.route('**/api/v1/personas', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [MARKET_PERSONA], total: 1 }),
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
          ...MARKET_PERSONA,
          backed_by_agents: ['legal_researcher', 'evidence_analyst', 'sentiment_agent', 'market_agent'],
          system_prompt_excerpt: '你是「市场研究员」，使用 DeepTutor 范式深读多份报告。',
        }),
      })
      return
    }
    await route.continue()
  })
}

test.describe('P14-D · 📊 市场研究员 · 发现链路', () => {
  test.beforeEach(async ({ page }) => {
    await installApiMocks(page)
    await installPersonaMocks(page)
    await seedAuthState(page, {
      role: 'admin',
      userId: 'e2e-market',
      name: 'E2E Market',
      email: 'market@anxinai.com',
    })
  })

  test('在智能体中心可看到市场研究员卡片并进入工作台', async ({ page }) => {
    await page.goto('/agents')

    // 标题：智能体（H1）
    await expect(page.getByRole('heading', { name: '智能体', level: 1 })).toBeVisible({ timeout: 15000 })

    // persona 卡片显示
    const cardName = page.getByRole('heading', { name: '市场研究员' })
    await expect(cardName).toBeVisible({ timeout: 10000 })
    // 实装徽章可见
    await expect(page.getByText('已实装').first()).toBeVisible()
    // 描述显示
    await expect(page.getByText('想了解一个行业').first()).toBeVisible()

    // 点 "进入工作台" 按钮 — 用 card 的局部范围避免选错
    const card = page.locator('div').filter({ has: cardName }).first()
    await card.getByRole('button', { name: '进入工作台' }).click()

    // 跳转到 persona 工作台
    await expect(page).toHaveURL(/\/v3\/personas\/market_researcher/)
    // 顶部 H1 显示 persona 名
    await expect(page.getByRole('heading', { name: '市场研究员', level: 1 })).toBeVisible()
  })

  test('直接访问 /v3/personas/market_researcher 渲染工作台三栏', async ({ page }) => {
    await page.goto('/v3/personas/market_researcher')

    // 顶部
    await expect(page.getByRole('heading', { name: '市场研究员', level: 1 })).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('已实装').first()).toBeVisible()

    // 右栏：能力清单 section 头
    await expect(page.getByText(/能力清单（\d+）/)).toBeVisible()
    // 至少一条能力可见
    await expect(page.getByText('行业研究（DeepTutor 模式深度阅读多份报告）')).toBeVisible()

    // 左栏：聊天空状态提示
    await expect(page.getByText('和 市场研究员 开始对话')).toBeVisible()
  })

  test('未知 persona id 应跳回 /agents', async ({ page }) => {
    await page.goto('/v3/personas/__nonexistent__')
    // 等待 store load 后做兜底跳转
    await expect(page).toHaveURL(/\/agents/, { timeout: 10000 })
    await expect(page.getByRole('heading', { name: '智能体', level: 1 })).toBeVisible()
  })
})
