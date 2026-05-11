/**
 * 📋 流程管家 — 通用聊天 E2E
 *
 * P14-C：覆盖 PersonaChatPanel 在 P7-A 已实装 persona 上的行为。
 * 已实装 persona 不应显示 "规划中" 提示条。
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
  backed_by_skills: ['operations/okr-plan', 'operations/weekly-report'],
  supported_apps: ['feishu', 'dingtalk', 'wecom', 'notion'],
}

async function installPersonasMock(
  page: Page,
  options: { chatReply?: string } = {},
) {
  await page.route('**/api/v1/personas', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [OPERATIONS_PERSONA], total: 1 }),
    })
  })

  await page.route('**/api/v1/personas/operations_manager', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...OPERATIONS_PERSONA,
        backed_by_agents: ['requirement_analyst', 'okr_agent'],
      }),
    })
  })

  await page.route('**/api/v1/personas/operations_manager/chat', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'operations_manager',
        content:
          options.chatReply ??
          '📋 **流程管家**：收到，我可以帮你做 OKR / 审批 / 会议纪要 / 周报。',
        metadata: { mock: true, is_implemented: true },
      }),
    })
  })
}

test.describe('📋 流程管家 — 通用聊天', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-ops-user',
      name: '运营经理',
      email: 'ops@example.com',
    })
  })

  test('打开工作台展示 已实装 徽章 + 空状态 + sample 提问', async ({ page }) => {
    await installPersonasMock(page)
    await installApiMocks(page)

    await page.goto('/v3/personas/operations_manager')

    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })
    await expect(page.locator('text=已实装').first()).toBeVisible()
    await expect(page.getByText('和 流程管家 开始对话')).toBeVisible()
    await expect(page.getByRole('button', { name: /请帮我：OKR 管理/ })).toBeVisible()
  })

  test('已实装 persona 不显示 "规划中" 提示条', async ({ page }) => {
    await installPersonasMock(page)
    await installApiMocks(page)

    await page.goto('/v3/personas/operations_manager')
    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })

    await expect(page.getByText(/该 persona 后端尚未实装/)).toHaveCount(0)
  })

  test('发送 "今天有什么待办" 后看到用户气泡 + assistant 响应', async ({ page }) => {
    await installPersonasMock(page, {
      chatReply:
        '📋 **今日待办**\n\n1. 审批：3 笔报销待您批（截止今晚 18:00）\n2. 会议：14:00 周会，议程已生成\n3. 周报：本周 OKR 进度 68%',
    })
    await installApiMocks(page)

    await page.goto('/v3/personas/operations_manager')
    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })

    await page.getByPlaceholder(/和 流程管家 说点什么/).fill('今天有什么待办')
    await page.getByRole('button', { name: /^发送$/ }).click()

    await expect(page.getByText('今天有什么待办')).toBeVisible()
    await expect(page.getByText(/今日待办/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/3 笔报销待您批/)).toBeVisible()
    await expect(page.getByText(/对话\s*·\s*2\s*条/)).toBeVisible()
  })

  test('点击 sample 提问 自动填充输入框', async ({ page }) => {
    await installPersonasMock(page)
    await installApiMocks(page)

    await page.goto('/v3/personas/operations_manager')
    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })

    await page.getByRole('button', { name: /请帮我：审批流程/ }).click()
    const textarea = page.getByPlaceholder(/和 流程管家 说点什么/)
    await expect(textarea).toHaveValue(/请帮我：审批流程/)
  })
})
