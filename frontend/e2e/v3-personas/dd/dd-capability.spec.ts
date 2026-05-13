/**
 * P14-B · 尽调专家 (due_diligence_expert) — Capability 触发
 *
 * 验证：
 *   1. 触发"工商尽调" → assistant 应答 = DueDiligenceReport 摘要
 *      (基本信息 / 诉讼 / 信用 / 评级)
 *   2. 应答附"切换关系图谱 / 舆情监控"两个 tab 提示
 *   3. 切到"关系图谱" tab → 看到节点 + 边可视化 (mock 文本)
 *   4. 切到"舆情监控" tab → 看到情绪分数
 *
 * 注：
 *   当前 persona 工作台只有通用 chat 面板 + CapabilityRunner，
 *   尚无独立的 DueDiligenceReport / RelationshipGraph / SentimentPanel
 *   挂载到工作台中（尽调组件在 src/components/due-diligence/ 但未接入）。
 *
 *   本 spec 通过 mock chat 返回中文 markdown 模拟"分 tab 报告"。
 *   后续接入真组件后，需替换为 data-testid 选择器（详见报告"缺 testid"清单）。
 */

import { test, expect, type Page, type Route } from '@playwright/test'
import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA_ID = 'due_diligence_expert'

const personaPayload = {
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
  backed_by_skills: ['intelligence/company-profile', 'intelligence/news-aggregate'],
  supported_apps: ['企查查', '天眼查'],
}

const COMPANY_REPORT = [
  '🔍 **尽调专家**：尽调报告（摘要）',
  '',
  '## 基本信息',
  '- 公司名称：上海某科技有限公司',
  '- 统一信用代码：91310000XXXXXXXXXX',
  '- 法定代表人：李四',
  '- 注册资本：500 万人民币',
  '',
  '## 诉讼记录',
  '- 共 3 起诉讼，2 起为原告，1 起为被告',
  '- 最近一起：合同纠纷（已结案）',
  '',
  '## 信用评级',
  '- 信用等级：B+',
  '- 经营异常：无',
  '- 失信被执行人：未发现',
  '',
  '## 综合风险评级',
  '- 评级：低风险（评分 78 / 100）',
  '',
  '> 切换 tab：[关系图谱] / [舆情监控]',
].join('\n')

const RELATIONSHIP_GRAPH_REPLY = [
  '🔍 **尽调专家**：关系图谱',
  '',
  '**节点**：',
  '- [核心] 上海某科技有限公司',
  '- [股东] 李四（持股 60%）',
  '- [股东] 王五（持股 40%）',
  '- [关联] 上海某贸易有限公司',
  '',
  '**边**：',
  '- 李四 ──持股──> 上海某科技',
  '- 王五 ──持股──> 上海某科技',
  '- 上海某科技 ──对外投资──> 上海某贸易',
].join('\n')

const SENTIMENT_REPLY = [
  '🔍 **尽调专家**：舆情监控',
  '',
  '**情绪分数**：0.62（正面偏中性）',
  '**舆情条数**：近 30 天 18 条',
  '- 正面：12',
  '- 中性：4',
  '- 负面：2',
  '',
  '**关键词**：技术突破 / 战略合作 / 数据合规',
].join('\n')

async function stubPersonaEndpoints(page: Page) {
  await page.route('**/api/v1/personas', async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [personaPayload], total: 1 }),
    })
  })

  await page.route(`**/api/v1/personas/${PERSONA_ID}`, async (route: Route) => {
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...personaPayload,
        backed_by_agents: ['due_diligence', 'evidence_analyst', 'sentiment_agent'],
      }),
    })
  })

  await page.route(`**/api/v1/personas/${PERSONA_ID}/chat`, async (route: Route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    const body = route.request().postDataJSON?.() ?? {}
    const message = String(body.message ?? '')

    let content = COMPANY_REPORT
    if (message.includes('舆情尽调')) content = SENTIMENT_REPLY
    else if (message.includes('法律尽调')) content = RELATIONSHIP_GRAPH_REPLY

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: PERSONA_ID,
        content,
        metadata: { is_implemented: false, mock: true },
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
    email: 'admin@anxinai.com',
  })
}

test.describe('尽调专家 · Capability 触发', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await page.goto(`/v3/personas/${PERSONA_ID}`)
    await expect(page.getByText('尽调专家').first()).toBeVisible({ timeout: 15000 })
  })

  test('触发"工商尽调" → 看到尽调报告摘要 (基本信息 / 诉讼 / 信用 / 评级)', async ({ page }) => {
    await page.getByRole('button', { name: /工商尽调.*股权/ }).click()
    await expect(page.getByText(/将触发：/)).toBeVisible()
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    // 4 个核心 section
    await expect(page.getByText(/基本信息/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/统一信用代码/)).toBeVisible()
    await expect(page.getByText(/诉讼记录/)).toBeVisible()
    await expect(page.getByText(/信用评级/)).toBeVisible()
    await expect(page.getByText(/综合风险评级/)).toBeVisible()
    await expect(page.getByText(/低风险.*78/)).toBeVisible()
  })

  test('切到"关系图谱" tab → 看到节点 + 边可视化', async ({ page }) => {
    // mock 中 "法律尽调" 触发关系图谱回复（替代独立 tab，因当前工作台无 tab 组件）
    await page.getByRole('button', { name: /法律尽调.*诉讼/ }).click()
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/关系图谱/)).toBeVisible({ timeout: 10000 })
    // 节点
    await expect(page.getByText(/节点/).first()).toBeVisible()
    await expect(page.getByText(/股东.*李四/)).toBeVisible()
    // 边
    await expect(page.getByText(/边/).first()).toBeVisible()
    await expect(page.getByText(/持股/).first()).toBeVisible()
  })

  test('切到"舆情监控" tab → 看到情绪分数', async ({ page }) => {
    await page.getByRole('button', { name: /舆情尽调.*新闻/ }).click()
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    await expect(page.getByText(/舆情监控/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/情绪分数.*0\.62/)).toBeVisible()
    await expect(page.getByText(/正面：12/)).toBeVisible()
    await expect(page.getByText(/负面：2/)).toBeVisible()
  })

  test('能力清单显示全部 5 项', async ({ page }) => {
    await expect(page.getByRole('button', { name: /工商尽调.*股权/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /法律尽调.*诉讼/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /财务尽调.*年报/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /舆情尽调.*新闻/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /专项报告.*PDF 导出/ })).toBeVisible()
  })

  test('未选 capability 时触发按钮禁用', async ({ page }) => {
    const trigger = page.getByRole('button', { name: /触发并发送到对话/ })
    await expect(trigger).toBeDisabled()
  })
})
