/**
 * P14-B · 合同管家 (contract_steward) — Capability 触发
 *
 * 验证：
 *   1. 选择"合同起草" → 在右侧能力面板触发器中可见 → 触发并发送
 *   2. assistant 应答可见，包含合同正文 + (mock 包含) docx 下载入口暗示 + 风险评估提示
 *   3. 切换到"合同审查" → 触发 → 看到 issues 列表 + 评分提示
 *
 * 注：当前 PersonaCapabilityRunner 走通用 chat endpoint
 *     （不是专属 /contracts API），所以这里 mock chat 返回针对性内容。
 *     如未来引入专属 endpoint + DocxDownloadButton + RiskScoreCard 组件，
 *     需补充对应 testid 检查并扩充本 spec。
 */

import { test, expect, type Page, type Route } from '@playwright/test'
import { installApiMocks, seedAuthState } from '../../helpers/session'

const PERSONA_ID = 'contract_steward'

const personaPayload = {
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
  supported_apps: ['法大大', 'e签宝'],
}

const DRAFT_REPLY = [
  '📜 **合同管家**：已为您生成《服务合同》初稿。',
  '',
  '**合同正文**：',
  '第一条 合同主体：甲方 上海安心法务，乙方 张三。',
  '第二条 服务范围：法律咨询、合同审查与归档。',
  '',
  '📎 [下载 docx](https://example.com/contract-e2e.docx)',
  '',
  '**风险评估**：风险等级 中等 · 风险评分 0.42 · 主要风险：付款期限较长。',
].join('\n')

const REVIEW_REPLY = [
  '📜 **合同管家**：合同审查完成。',
  '',
  '**问题清单 (issues)**：',
  '- [高] 第三条 违约条款过严',
  '- [中] 第五条 解除条件不明',
  '- [低] 第七条 通知地址未写明',
  '',
  '**整体评分**：72 / 100',
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
        backed_by_agents: ['contract_reviewer', 'document_drafter'],
      }),
    })
  })

  // 根据请求体里的 message 关键字返回不同的应答（起草 vs 审查）
  await page.route(`**/api/v1/personas/${PERSONA_ID}/chat`, async (route: Route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    const body = route.request().postDataJSON?.() ?? {}
    const message = String(body.message ?? '')
    let content = DRAFT_REPLY
    if (message.includes('合同审查')) content = REVIEW_REPLY
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
    email: 'admin@anxinfawu.com',
  })
}

test.describe('合同管家 · Capability 触发', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await page.goto(`/v3/personas/${PERSONA_ID}`)
    await expect(page.getByText('合同管家').first()).toBeVisible({ timeout: 15000 })
  })

  test('触发"合同起草" → 看到合同正文 + docx 下载 + 风险评估', async ({ page }) => {
    // 在右侧能力清单点击 "合同起草"（带"模板库"字样的能力按钮，区别于左侧 EmptyHint sample）
    await page.getByRole('button', { name: /合同起草.*模板库/ }).click()

    // 触发提示出现
    await expect(page.getByText(/将触发：/)).toBeVisible()

    // 触发并发送
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    // assistant 应答中可见的核心元素
    await expect(page.getByText(/合同正文/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/下载 docx/)).toBeVisible()
    await expect(page.getByText(/风险评估/)).toBeVisible()
    await expect(page.getByText(/风险等级 中等/)).toBeVisible()
  })

  test('触发"合同审查" → 看到 issues 列表 + 评分', async ({ page }) => {
    await page.getByRole('button', { name: /合同审查.*逐条审查/ }).click()
    await expect(page.getByText(/将触发：/)).toBeVisible()
    await page.getByRole('button', { name: /触发并发送到对话/ }).click()

    // issues 列表
    await expect(page.getByText(/问题清单/)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/违约条款过严/)).toBeVisible()
    // 评分
    await expect(page.getByText(/72 \/ 100/)).toBeVisible()
  })

  test('未选 capability 时触发按钮禁用', async ({ page }) => {
    const trigger = page.getByRole('button', { name: /触发并发送到对话/ })
    await expect(trigger).toBeDisabled()
  })

  test('能力清单显示全部 5 项', async ({ page }) => {
    // 完整名称可唯一定位 capability 列表里的 5 个 button
    await expect(page.getByRole('button', { name: /合同起草.*模板库/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /合同审查.*逐条审查/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /合同谈判.*让步空间/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /合同管理.*到期提醒/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /合规校验.*红线/ })).toBeVisible()
  })
})
