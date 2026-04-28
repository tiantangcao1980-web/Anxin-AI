/**
 * 📋 流程管家 (operations_manager) — 发现路径 E2E
 *
 * P14-C：覆盖 OKR / 审批 / 周报 / 会议纪要 入口的发现链路。
 * operations_manager 是 P7-A 已实装的 persona，徽章应显示 "已实装"。
 */

import { expect, test, type Page, type TestInfo } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

const OPERATIONS_PERSONA = {
  persona_id: 'operations_manager',
  display_name: '流程管家',
  emoji: '📋',
  description: '公司过程管理小助手，OKR 到周报都帮你梳',
  domain: '合规经营',
  is_implemented: true,
  capabilities: [
    'OKR 管理（制定 / 拆解 / 跟进 / 复盘）',
    '审批流程（报销 / 请假 / 采购 智能审批）',
    '会议纪要（录音 → 转写 → 提炼 → 分发待办）',
    '周报 / 月报（OKR + 飞书 + 日历 自动聚合）',
    '日程协调（多人会议时间协调 + 议程起草）',
  ],
  backed_by_skills: [
    'operations/okr-plan',
    'operations/approval-flow',
    'operations/meeting-minutes',
    'operations/weekly-report',
    'office/calendar-coordinate',
    'office/transcribe',
  ],
  supported_apps: ['feishu', 'dingtalk', 'wecom', 'notion', 'google_calendar', 'outlook'],
}

const FINANCE_PERSONA = {
  persona_id: 'tax_finance_advisor',
  display_name: '财税顾问',
  emoji: '💰',
  description: '节税合规 + 财务健康',
  domain: '合规经营',
  is_implemented: false,
  capabilities: ['税务合规'],
  backed_by_skills: ['tax_finance/tax-plan'],
  supported_apps: ['金蝶'],
}

async function installPersonasMock(page: Page) {
  await page.route('**/api/v1/personas', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [OPERATIONS_PERSONA, FINANCE_PERSONA],
        total: 2,
      }),
    })
  })

  await page.route('**/api/v1/personas/operations_manager', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...OPERATIONS_PERSONA,
        backed_by_agents: ['requirement_analyst', 'coordinator', 'okr_agent'],
        system_prompt_excerpt: '你是流程管家……',
      }),
    })
  })
}

test.describe('📋 流程管家 — 发现路径', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await installPersonasMock(page)
    await installApiMocks(page)
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-ops-user',
      name: '运营经理',
      email: 'ops@example.com',
    })
  })

  test('智能体广场可见 流程管家 卡片 + 已实装徽章 + 业务域', async ({ page }) => {
    await page.goto('/agents')

    await expect(page.getByRole('heading', { name: '智能体' })).toBeVisible({
      timeout: 15000,
    })
    await expect(page.getByText('流程管家', { exact: true })).toBeVisible()
    await expect(page.getByText('operations_manager')).toBeVisible()
    await expect(page.locator('text=已实装').first()).toBeVisible()
    // 应该显示 5 项能力中前 3 + 还有 2 项
    await expect(page.getByText(/还有\s*2\s*项能力/)).toBeVisible()
  })

  test('搜索关键词 "OKR" 命中 流程管家', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('流程管家')).toBeVisible({ timeout: 15000 })

    await page.getByPlaceholder(/搜索 persona/).fill('OKR')
    await expect(page.getByText('流程管家')).toBeVisible()
    await expect(page.getByText('财税顾问')).toHaveCount(0)
  })

  test('过滤切到 "已实装" 时 流程管家 仍可见', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByText('流程管家')).toBeVisible({ timeout: 15000 })

    await page.getByRole('tab', { name: '已实装' }).click()
    await expect(page.getByText('流程管家')).toBeVisible()
    await expect(page.getByText('财税顾问')).toHaveCount(0)
  })

  test('点击 "进入工作台" 跳转到 /v3/personas/operations_manager', async ({
    page,
  }) => {
    await page.goto('/agents')
    await expect(page.getByText('流程管家')).toBeVisible({ timeout: 15000 })

    const card = page
      .locator('div', { has: page.getByText('流程管家', { exact: true }) })
      .filter({ has: page.getByRole('button', { name: /进入工作台/ }) })
      .first()
    await card.getByRole('button', { name: /进入工作台/ }).click()

    await expect(page).toHaveURL(/\/v3\/personas\/operations_manager/)
    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })
  })
})
