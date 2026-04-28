/**
 * 💰 财税顾问 — Capability 触发器 E2E
 *
 * P14-C：覆盖 PersonaCapabilityRunner 的能力清单 → 触发 → chat 端点的链路。
 *
 * 注：当前 P8-C 阶段所有 capability 都通过通用 /personas/{id}/chat 端点触发，
 * 这里 mock 不同关键词的回复以验证：
 *   - 增值税计算 → 销售额 / 税额 / 法规依据
 *   - 跨境 VAT 指引 → 国家 / VAT 率 / disclaimer
 *   - 财报分析 → 关键指标 / 健康度
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
    '增值税计算（含进项 / 销项 / 应纳税额）',
    '跨境 VAT 指引（欧盟 / 英国 / 美国 sales tax）',
    '财报分析（现金流 / 资产负债 / 利润 关键指标）',
    '节税筹划（合规节税方案 + 风险等级）',
    '稽查预警（高频稽查指标自检）',
  ],
  backed_by_skills: [
    'tax_finance/tax-plan',
    'tax_finance/tax-check',
    'tax_finance/legal-calc',
    'tax_finance/financial-analysis',
  ],
  supported_apps: ['金蝶', '用友', 'xero', 'quickbooks', '国家税务总局'],
}

interface CapabilityReply {
  matchKeyword: string
  content: string
}

async function installPersonasMock(
  page: Page,
  replies: CapabilityReply[],
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
      }),
    })
  })
  await page.route('**/api/v1/personas/tax_finance_advisor/chat', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    const body = (route.request().postDataJSON?.() ?? {}) as {
      message?: string
    }
    const msg = body.message ?? ''
    const matched = replies.find((r) => msg.includes(r.matchKeyword))
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'tax_finance_advisor',
        content: matched?.content ?? '已收到您的请求，正在处理……',
        metadata: { mock: true, capability: matched?.matchKeyword },
      }),
    })
  })
}

async function pickCapabilityAndTrigger(
  page: Page,
  capabilityKeyword: string,
  detail: string,
) {
  // 在能力清单中点击对应能力
  await page
    .getByRole('button', { name: new RegExp(capabilityKeyword) })
    .first()
    .click()

  // 顶部出现 "将触发：..." 提示
  await expect(page.getByText(/将触发：/)).toBeVisible()

  // 在 capability runner 的 textarea 填入详细输入
  await page
    .getByPlaceholder(/可选：贴入你的输入/)
    .fill(detail)

  await page.getByRole('button', { name: /触发并发送到对话|执行中/ }).click()
}

test.describe('💰 财税顾问 — Capability 触发器', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-finance-user',
      name: '财税用户',
      email: 'finance@example.com',
    })
  })

  test('增值税计算 — 输入销售额，看到税额 + 法规依据', async ({ page }) => {
    await installPersonasMock(page, [
      {
        matchKeyword: '增值税计算',
        content: [
          '💰 **增值税测算**',
          '',
          '- 销售额（不含税）：100,000 元',
          '- 适用税率：13%',
          '- **应纳增值税额：13,000 元**',
          '',
          '**法规依据**：《中华人民共和国增值税暂行条例》第二条；财税〔2019〕39 号公告。',
        ].join('\n'),
      },
    ])
    await installApiMocks(page)

    await page.goto('/v3/personas/tax_finance_advisor')
    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })

    await pickCapabilityAndTrigger(
      page,
      '增值税计算',
      '销售额 100,000 元，适用税率 13%',
    )

    await expect(page.getByText(/应纳增值税额[：:]\s*13,?000\s*元/)).toBeVisible({
      timeout: 10000,
    })
    await expect(page.getByText(/法规依据/)).toBeVisible()
    await expect(page.getByText(/增值税暂行条例/)).toBeVisible()
  })

  test('跨境 VAT 指引 — 选国家德国，看到 VAT 率 + 申报建议 + disclaimer', async ({
    page,
  }) => {
    await installPersonasMock(page, [
      {
        matchKeyword: '跨境 VAT 指引',
        content: [
          '🌍 **德国 VAT 指引**',
          '',
          '- 国家：德国 (DE)',
          '- **标准 VAT 率：19%**',
          '- 减按税率：7%（食品 / 书籍）',
          '- **申报建议**：年销售额超 €100,000 须本地注册 VAT；可使用 OSS 一站式申报覆盖欧盟其他成员国。',
          '',
          '⚠️ **免责声明 / disclaimer**：本指引仅供参考，正式申报前请咨询当地持牌税务师。',
        ].join('\n'),
      },
    ])
    await installApiMocks(page)

    await page.goto('/v3/personas/tax_finance_advisor')
    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })

    await pickCapabilityAndTrigger(
      page,
      '跨境 VAT 指引',
      '目标国家：德国，电商独立站',
    )

    await expect(page.getByText(/标准 VAT 率[：:]\s*19%/)).toBeVisible({
      timeout: 10000,
    })
    await expect(page.getByText(/申报建议/)).toBeVisible()
    await expect(page.getByText(/免责声明|disclaimer/i)).toBeVisible()
  })

  test('财报分析 — 提交财务数据，看到关键指标 + 健康度评分', async ({ page }) => {
    await installPersonasMock(page, [
      {
        matchKeyword: '财报分析',
        content: [
          '📊 **财报分析报告**',
          '',
          '**关键指标**：',
          '- 流动比率：2.3（健康）',
          '- 资产负债率：42%（合理）',
          '- 净利率：12.5%（行业 avg 9%）',
          '- 经营性现金流：+ 1,200 万元',
          '',
          '**财务健康度评分：82 / 100（B+ 级）**',
          '建议：关注应收账款回收周期。',
        ].join('\n'),
      },
    ])
    await installApiMocks(page)

    await page.goto('/v3/personas/tax_finance_advisor')
    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })

    await pickCapabilityAndTrigger(
      page,
      '财报分析',
      '附 2025 年报数据：营收 1.2 亿，净利 1500 万，资产 5000 万',
    )

    await expect(page.getByText(/关键指标/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/流动比率[：:]\s*2\.3/)).toBeVisible()
    await expect(page.getByText(/财务健康度评分[：:]?\s*82/)).toBeVisible()
  })

  test('未选能力直接点触发 — 按钮 disabled', async ({ page }) => {
    await installPersonasMock(page, [])
    await installApiMocks(page)

    await page.goto('/v3/personas/tax_finance_advisor')
    await expect(page.getByRole('heading', { name: '财税顾问' })).toBeVisible({
      timeout: 15000,
    })

    const triggerBtn = page.getByRole('button', { name: /触发并发送到对话/ })
    await expect(triggerBtn).toBeDisabled()
    await expect(
      page.getByText(/在上方选一项能力，然后填写输入并触发/),
    ).toBeVisible()
  })
})
