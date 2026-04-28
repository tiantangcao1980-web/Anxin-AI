/**
 * 📋 流程管家 — Capability 触发器 E2E
 *
 * P14-C：覆盖 OKR / 周报 / 会议纪要 三个核心能力的触发链路。
 * 当前 P8-C 阶段所有 capability 走通用 chat 端点；mock 按关键词路由不同响应。
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
    'OKR 看板（quarter view + 进度条）',
    '会议纪要（录音 → 转写 → 提炼 → 分发待办）',
    '生成本周周报（OKR + 飞书 + 日历 自动聚合）',
    '审批流程（报销 / 请假 / 采购 智能审批）',
    '日程协调（多人会议时间协调 + 议程起草）',
  ],
  backed_by_skills: [
    'operations/okr-plan',
    'operations/meeting-minutes',
    'operations/weekly-report',
    'office/transcribe',
  ],
  supported_apps: ['feishu', 'dingtalk', 'wecom', 'notion'],
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
        backed_by_agents: ['requirement_analyst', 'okr_agent', 'meeting_minutes_agent'],
      }),
    })
  })
  await page.route('**/api/v1/personas/operations_manager/chat', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    const body = (route.request().postDataJSON?.() ?? {}) as { message?: string }
    const msg = body.message ?? ''
    const matched = replies.find((r) => msg.includes(r.matchKeyword))
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: 'operations_manager',
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
  await page
    .getByRole('button', { name: new RegExp(capabilityKeyword) })
    .first()
    .click()

  await expect(page.getByText(/将触发：/)).toBeVisible()

  await page
    .getByPlaceholder(/可选：贴入你的输入/)
    .fill(detail)

  await page.getByRole('button', { name: /触发并发送到对话|执行中/ }).click()
}

test.describe('📋 流程管家 — Capability 触发器', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await seedAuthState(page, {
      role: 'enterprise_user',
      userId: 'e2e-ops-user',
      name: '运营经理',
      email: 'ops@example.com',
    })
  })

  test('生成本周周报 — 选数据源，看到周报 docx 下载入口', async ({ page }) => {
    await installPersonasMock(page, [
      {
        matchKeyword: '生成本周周报',
        content: [
          '📝 **本周周报已生成（2026-W17）**',
          '',
          '**亮点**：',
          '- OKR 进度 68%（vs 上周 +12%）',
          '- 关键里程碑：完成 P14 测试',
          '',
          '**风险**：',
          '- O2 KR3 进度仅 30%，需调拨资源',
          '',
          '📎 [下载周报 docx](https://example.com/weekly-2026-W17.docx)',
        ].join('\n'),
      },
    ])
    await installApiMocks(page)

    await page.goto('/v3/personas/operations_manager')
    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })

    await pickCapabilityAndTrigger(
      page,
      '生成本周周报',
      '数据源：飞书日历 + Notion OKR + Jira tickets',
    )

    await expect(page.getByText(/本周周报已生成/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/下载周报 docx/)).toBeVisible()
    await expect(page.getByText(/OKR 进度 68%/)).toBeVisible()
  })

  test('会议纪要 — 输入文本，看到 todo 提取列表', async ({ page }) => {
    await installPersonasMock(page, [
      {
        matchKeyword: '会议纪要',
        content: [
          '🗒️ **会议纪要 — 2026-04-26 产品周会**',
          '',
          '**议程要点**：',
          '- P14 进入 E2E 阶段',
          '- 财税 / 流程两个 persona 优先级提升',
          '',
          '**Todo 列表（提取自纪要）**：',
          '1. ✅ 张三：周五前完成 finance-capability spec — DDL 04-30',
          '2. ✅ 李四：跟进 operations 后端 OKR 看板 endpoint — DDL 05-02',
          '3. ✅ 王五：评审周报 docx 模板 — DDL 04-28',
        ].join('\n'),
      },
    ])
    await installApiMocks(page)

    await page.goto('/v3/personas/operations_manager')
    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })

    await pickCapabilityAndTrigger(
      page,
      '会议纪要',
      '会议文本：今天讨论了 P14 进度和 persona 优先级，张三负责 finance spec...',
    )

    await expect(page.getByText(/会议纪要/).nth(0)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/Todo 列表/)).toBeVisible()
    await expect(page.getByText(/张三：.*finance-capability spec/)).toBeVisible()
    await expect(page.getByText(/李四：.*OKR 看板/)).toBeVisible()
  })

  test('OKR 看板 — 看到 quarter view + 进度条', async ({ page }) => {
    await installPersonasMock(page, [
      {
        matchKeyword: 'OKR 看板',
        content: [
          '🎯 **OKR 看板 — 2026 Q2（quarter view）**',
          '',
          '**O1：发布 V3 智能体**',
          '- KR1 上线 10 personas — 进度 [████████░░] 80%',
          '- KR2 用户激活 1000 — 进度 [██████░░░░] 60%',
          '',
          '**O2：构建 Harness**',
          '- KR1 完成 verification 层 — 进度 [██████████] 100%',
          '- KR2 完成 observability — 进度 [███░░░░░░░] 30%',
          '',
          '_总体季度进度：68%_',
        ].join('\n'),
      },
    ])
    await installApiMocks(page)

    await page.goto('/v3/personas/operations_manager')
    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })

    await pickCapabilityAndTrigger(
      page,
      'OKR 看板',
      'quarter: 2026Q2，团队：智能体团队',
    )

    await expect(page.getByText(/OKR 看板/).nth(0)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/quarter view/)).toBeVisible()
    // 进度条用 ASCII 块字符渲染
    await expect(page.getByText(/████████░░/)).toBeVisible()
    await expect(page.getByText(/总体季度进度[：:]?\s*68%/)).toBeVisible()
  })

  test('能力清单展示 5 项（已实装 persona）', async ({ page }) => {
    await installPersonasMock(page, [])
    await installApiMocks(page)

    await page.goto('/v3/personas/operations_manager')
    await expect(page.getByRole('heading', { name: '流程管家' })).toBeVisible({
      timeout: 15000,
    })

    // 右侧能力清单标题（含计数）
    await expect(page.getByText(/能力清单（5）/)).toBeVisible()
    await expect(page.getByText(/集成应用（4）/)).toBeVisible()
  })
})
