/**
 * 💰 财税顾问 — 通用聊天 E2E
 *
 * P14-C：覆盖 PersonaChatPanel + 通用 /personas/{id}/chat 端点。
 * 验证：空状态提示词 / 发送 / 渲染 assistant 响应 / "规划中" 标识 / 清空线程。
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
  backed_by_skills: ['tax_finance/tax-plan', 'tax_finance/tax-check'],
  supported_apps: ['金蝶', '用友', 'xero', 'quickbooks', '国家税务总局'],
}

async function installPersonasMock(
  page: Page,
  options: { chatReply?: string } = {},
) {
  await page.route('**/api/v1/personas', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [FINANCE_PERSONA], total: 1 }),
    })
  })

  await page.route('**/api/v1/personas/tax_finance_advisor', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...FINANCE_PERSONA,
        backed_by_agents: ['tax_compliance', 'legal_calculator'],
        system_prompt_excerpt: '你是财税顾问……',
      }),
    })
  })

  await page.route('**/api/v1/personas/tax_finance_advisor/chat', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'tax_finance_advisor',
        content:
          options.chatReply ??
          '💰 **财税顾问**（规划中 · mock 占位）：「你好」\n\n本 persona 后端尚未实装……',
        metadata: { mock: true, is_implemented: false },
      }),
    })
  })
}

test.describe('💰 财税顾问 — 通用聊天', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-finance-user',
      name: '财税用户',
      email: 'finance@example.com',
    })
  })

  test('打开工作台展示 persona header + 空状态提示 + sample 提问', async ({
    page,
  }) => {
    await installPersonasMock(page)
    await installApiMocks(page)

    await page.goto('/v3/personas/tax_finance_advisor')

    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })
    // 顶部规划中徽章
    await expect(page.locator('text=规划中').first()).toBeVisible()
    // 聊天空状态提示
    await expect(page.getByText('和 财税顾问 开始对话')).toBeVisible()
    // sample 提问由 capabilities[0..3] 派生
    await expect(page.getByRole('button', { name: /请帮我：税务合规/ })).toBeVisible()
  })

  test('发送消息后显示用户气泡 + assistant 回复 + 计数 +2', async ({ page }) => {
    await installPersonasMock(page, {
      chatReply:
        '💰 **财税顾问**：增值税基本税率 13%，小规模纳税人征收率 1% / 3%。请告诉我您的销售额和行业，我可以为您测算。',
    })
    await installApiMocks(page)

    await page.goto('/v3/personas/tax_finance_advisor')
    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })

    const textarea = page.getByPlaceholder(/和 财税顾问 说点什么/)
    await textarea.fill('增值税税率是多少？')
    await page.getByRole('button', { name: /^发送$/ }).click()

    // user 气泡
    await expect(page.getByText('增值税税率是多少？')).toBeVisible()
    // assistant 回复
    await expect(page.getByText(/增值税基本税率\s*13%/)).toBeVisible({
      timeout: 10000,
    })
    // 顶部计数：2 条
    await expect(page.getByText(/对话\s*·\s*2\s*条/)).toBeVisible()
  })

  test('未实装 persona 显示 "规划中" mock 占位提示条', async ({ page }) => {
    await installPersonasMock(page)
    await installApiMocks(page)

    await page.goto('/v3/personas/tax_finance_advisor')
    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })

    await expect(page.getByText(/该 persona 后端尚未实装/)).toBeVisible()
  })

  test('发送 → 清空线程后历史归零', async ({ page }) => {
    await installPersonasMock(page, { chatReply: '已收到，正在为您测算……' })
    await installApiMocks(page)

    await page.goto('/v3/personas/tax_finance_advisor')
    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })

    await page.getByPlaceholder(/和 财税顾问 说点什么/).fill('测试一下')
    await page.getByRole('button', { name: /^发送$/ }).click()

    await expect(page.getByText(/对话\s*·\s*2\s*条/)).toBeVisible({
      timeout: 10000,
    })

    await page.getByRole('button', { name: '清空' }).click()
    await expect(page.getByText(/对话\s*·\s*0\s*条/)).toBeVisible()
    await expect(page.getByText('和 财税顾问 开始对话')).toBeVisible()
  })
})
