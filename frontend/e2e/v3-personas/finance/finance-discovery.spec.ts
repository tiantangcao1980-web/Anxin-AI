/**
 * 💰 财税顾问 (tax_finance_advisor) — 发现路径 E2E
 *
 * P14-C：覆盖用户从智能体广场进入财税顾问工作台的完整发现链路。
 * 验证：列表渲染 / 搜索过滤 / 域过滤 / 卡片进入 / URL 路由。
 *
 * 数据策略：
 *   - 在 installApiMocks（catch-all `**/api/**`）之前先注册 personas 专用 mock，
 *     利用 Playwright LIFO 路由匹配机制覆盖通用路由。
 */

import { expect, test, type Page, type TestInfo } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const FINANCE_PERSONA = {
  persona_id: 'tax_finance_advisor',
  display_name: '财税顾问',
  emoji: '💰',
  description: '节税合规 + 财务健康，老板和会计的最佳搭档',
  domain: '合规经营',
  is_implemented: false,
  capabilities: [
    '税务合规（增值税 / 企业所得税 / 个税申报检查）',
    '节税筹划（合规节税方案 + 风险等级）',
    '法律计算（经济补偿金 / 加班费 / 工伤赔偿 / 利息）',
    '财务分析（现金流 / 资产负债 / 利润 关键指标）',
    '稽查预警（高频稽查指标自检）',
  ],
  backed_by_skills: [
    'tax_finance/tax-plan',
    'tax_finance/tax-check',
    'tax_finance/legal-calc',
    'tax_finance/financial-analysis',
    'tax_finance/audit-warning',
  ],
  supported_apps: ['金蝶', '用友', 'xero', 'quickbooks', '国家税务总局'],
}

const OTHER_PERSONA = {
  persona_id: 'operations_manager',
  display_name: '流程管家',
  emoji: '📋',
  description: '公司过程管理小助手，OKR 到周报都帮你梳',
  domain: '合规经营',
  is_implemented: true,
  capabilities: ['OKR 管理', '审批流程', '会议纪要'],
  backed_by_skills: ['operations/okr-plan'],
  supported_apps: ['feishu', 'dingtalk'],
}

async function installPersonasMock(page: Page) {
  await page.route('**/api/v1/personas', async (route) => {
    if (route.request().method() !== 'GET') {
      return route.fallback()
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [FINANCE_PERSONA, OTHER_PERSONA],
        total: 2,
      }),
    })
  })

  await page.route('**/api/v1/personas/tax_finance_advisor', async (route) => {
    if (route.request().method() !== 'GET') {
      return route.fallback()
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...FINANCE_PERSONA,
        backed_by_agents: ['tax_compliance', 'legal_calculator', 'compliance_officer'],
        system_prompt_excerpt: '你是财税顾问，专注节税合规与财务健康……',
      }),
    })
  })
}

test.describe('💰 财税顾问 — 发现路径', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await installPersonasMock(page)
    await installApiMocks(page)
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-finance-user',
      name: '财税用户',
      email: 'finance@example.com',
    })
  })

  test('智能体广场可见 财税顾问 卡片 + 业务域 + 规划中徽章', async ({ page }) => {
    await page.goto('/agents')

    await expect(page.getByRole('heading', { name: '智能体' })).toBeVisible({
      timeout: 15000,
    })
    const card = page.getByText('财税顾问', { exact: true })
    await expect(card).toBeVisible()
    await expect(page.getByText('tax_finance_advisor')).toBeVisible()
    await expect(page.getByText('节税合规 + 财务健康，老板和会计的最佳搭档')).toBeVisible()
    // 5 项能力 — 卡片预览前 3 条 + "+还有 2 项能力"
    await expect(page.getByText(/还有\s*2\s*项能力/)).toBeVisible()
    // 规划中徽章
    await expect(page.locator('text=规划中').first()).toBeVisible()
  })

  test('搜索 "财税" 可过滤出 财税顾问', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('财税顾问')).toBeVisible({ timeout: 15000 })

    await page.getByPlaceholder(/搜索 persona/).fill('财税')
    await expect(page.getByText('财税顾问')).toBeVisible()
    await expect(page.getByText('流程管家')).toHaveCount(0)
  })

  test('点击 "进入工作台" 跳转到 /v3/personas/tax_finance_advisor', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('财税顾问')).toBeVisible({ timeout: 15000 })

    // 财税顾问卡片所在容器
    const card = page
      .locator('div', { has: page.getByText('财税顾问', { exact: true }) })
      .filter({ has: page.getByRole('button', { name: /进入工作台/ }) })
      .first()
    await card.getByRole('button', { name: /进入工作台/ }).click()

    await expect(page).toHaveURL(/\/v3\/personas\/tax_finance_advisor/)
    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })
  })

  test('过滤切到 "规划中" 时 财税顾问 仍然可见，"已实装" 时被过滤', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('财税顾问')).toBeVisible({ timeout: 15000 })

    await page.getByRole('tab', { name: '规划中' }).click()
    await expect(page.getByText('财税顾问')).toBeVisible()

    await page.getByRole('tab', { name: '已实装' }).click()
    await expect(page.getByText('财税顾问')).toHaveCount(0)
  })
})
