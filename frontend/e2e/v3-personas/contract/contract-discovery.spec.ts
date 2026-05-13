/**
 * P14-B · 合同管家 (contract_steward) — 入口发现
 *
 * 验证：
 *   1. /agents 列表能看到「📜 合同管家」persona 卡片
 *   2. 卡片显示：emoji / 名称 / persona_id / domain(合规经营)
 *   3. 显示 "规划中" 徽章 (is_implemented=false) 而不是 "已实装"
 *   4. 进入工作台 CTA 可点 → 路由跳到 /v3/personas/contract_steward
 */

import { test, expect, type Page, type Route } from '@playwright/test'
import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA_ID = 'contract_steward'

/** 在通用 mock 之上叠加 personas 端点的桩。 */
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
            display_name: '合同管家',
            emoji: '📜',
            description: '从起草、审查、谈判、签署到归档，每一份合同我帮你盯',
            domain: '合规经营',
            is_implemented: false,
            capabilities: [
              '合同起草（200+ 模板库 + 智能填空 + 行业定制）',
              '合同审查（逐条审查 + 风险标注 + 修改建议）',
              '合同谈判（让步空间分析 + 替代条款建议）',
              '合同管理（到期提醒 / 续约 / 归档 / 检索）',
              '合规校验（内部审批流 + 法务红线）',
            ],
            backed_by_skills: ['legal/contract-draft', 'legal/contract-review'],
            supported_apps: ['法大大', 'e签宝', 'feishu_doc'],
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

test.describe('合同管家 · 入口发现', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('/agents 显示合同管家卡片 + 关键元信息', async ({ page }) => {
    await page.goto('/agents')

    // 顶栏标题
    await expect(page.getByRole('heading', { name: '智能体' })).toBeVisible({ timeout: 15000 })

    // 卡片关键字段
    await expect(page.getByText('合同管家', { exact: true }).first()).toBeVisible()
    await expect(page.getByText(PERSONA_ID, { exact: true }).first()).toBeVisible()
    await expect(page.getByText('合规经营').first()).toBeVisible()
  })

  test('合同管家显示「规划中」徽章而非「已实装」', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('合同管家').first()).toBeVisible({ timeout: 15000 })

    // 至少出现一次「规划中」
    await expect(page.getByText('规划中').first()).toBeVisible()
  })

  test('点击「进入工作台」跳转到 contract_steward', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('合同管家').first()).toBeVisible({ timeout: 15000 })

    // 点击 CTA（页面上可能有多个 persona 时取第一个匹配的卡片内按钮）
    await page.getByRole('button', { name: /进入工作台/ }).first().click()

    await expect(page).toHaveURL(new RegExp(`/v3/personas/${PERSONA_ID}$`))
  })

  test('搜索 "合同" 能筛选出合同管家', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('合同管家').first()).toBeVisible({ timeout: 15000 })

    await page.getByPlaceholder(/搜索 persona/).fill('合同')
    await expect(page.getByText('合同管家').first()).toBeVisible()
  })
})
