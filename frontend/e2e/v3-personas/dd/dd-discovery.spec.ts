/**
 * P14-B · 尽调专家 (due_diligence_expert) — 入口发现
 *
 * 验证：
 *   1. /agents 列表能看到「🔍 尽调专家」persona 卡片
 *   2. 卡片显示 emoji / 名称 / persona_id / domain(合规经营)
 *   3. 显示 "规划中" 徽章
 *   4. 进入工作台 CTA 跳到 /v3/personas/due_diligence_expert
 *   5. 搜索关键字 "尽调" 可筛选到该 persona
 */

import { test, expect, type Page, type Route } from '@playwright/test'
import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA_ID = 'due_diligence_expert'

async function stubPersonaEndpoints(page: Page) {
  await page.route('**/api/v1/personas', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            persona_id: PERSONA_ID,
            display_name: '尽调专家',
            emoji: '🔍',
            description: '见客户 / 投资 / 收购前，先让我看看对方家底',
            domain: '合规经营',
            is_implemented: false,
            capabilities: [
              '工商尽调（股权 / 实控人 / 关联 / 变更）',
              '法律尽调（诉讼 / 仲裁 / 行政处罚 / 失信）',
              '财务尽调（年报 / 经营异常 / 税务等级）',
              '舆情尽调（新闻 / 社媒 / 维权 / 监管处罚）',
              '专项报告（投资级 / 客户级 / 供应商级 PDF 导出）',
            ],
            backed_by_skills: ['intelligence/company-profile', 'intelligence/litigation-search'],
            supported_apps: ['企查查', '天眼查', '启信宝'],
          },
        ],
        total: 1,
      }),
    })
  })
}

async function login(page: Page) {
  await installApiMocks(page)
  await stubPersonaEndpoints(page)
  await seedAuthState(page, {
    role: 'admin',
    userId: 'e2e-admin',
    name: 'E2E Admin',
    email: 'admin@anxinassistant.com',
  })
}

test.describe('尽调专家 · 入口发现', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('/agents 显示尽调专家卡片 + 关键元信息', async ({ page }) => {
    await page.goto('/agents')

    await expect(page.getByRole('heading', { name: '智能体' })).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('尽调专家', { exact: true }).first()).toBeVisible()
    await expect(page.getByText(PERSONA_ID, { exact: true }).first()).toBeVisible()
    await expect(page.getByText('合规经营').first()).toBeVisible()
  })

  test('尽调专家显示「规划中」徽章而非「已实装」', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('尽调专家').first()).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('规划中').first()).toBeVisible()
  })

  test('点击「进入工作台」跳转到 due_diligence_expert', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('尽调专家').first()).toBeVisible({ timeout: 15000 })

    await page.getByRole('button', { name: /进入工作台/ }).first().click()
    await expect(page).toHaveURL(new RegExp(`/v3/personas/${PERSONA_ID}$`))
  })

  test('搜索 "尽调" 能筛选出尽调专家', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('尽调专家').first()).toBeVisible({ timeout: 15000 })

    await page.getByPlaceholder(/搜索 persona/).fill('尽调')
    await expect(page.getByText('尽调专家').first()).toBeVisible()
  })
})
