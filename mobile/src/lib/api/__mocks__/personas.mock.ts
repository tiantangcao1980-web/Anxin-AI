/**
 * Personas API mock 适配（移动端 P17-C）
 *
 * 在 P17-A foundation 真接入前可以走这层让前端跑起来：
 * - listPersonas: 返回 registry 内 10 个 persona
 * - chatWithPersona: 接收 message,假 stream（每 200ms 吐 1 个字 token）
 * - runCapability: 返回结构化 mock 数据
 */

import { PERSONAS, getPersonaMeta, type PersonaCapability, type PersonaMeta } from '../../personas/registry'

export interface MockChatHistoryItem {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface MockChatRequest {
  message: string
  history?: MockChatHistoryItem[]
}

export interface MockChatResponse {
  persona_id: string
  content: string
  metadata: Record<string, unknown>
}

export interface MockCapabilityResult {
  persona_id: string
  capability_id: string
  /** Markdown 渲染的结构化结果 */
  content: string
  metadata: Record<string, unknown>
}

const TOKEN_DELAY_MS = 200

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ---------- list / get ----------

export async function mockListPersonas(): Promise<PersonaMeta[]> {
  await delay(120)
  return PERSONAS
}

export async function mockGetPersona(personaId: string): Promise<PersonaMeta | undefined> {
  await delay(80)
  return getPersonaMeta(personaId)
}

// ---------- chat（单次） ----------

function fakeAnswer(persona: PersonaMeta, message: string): string {
  const lines = [
    `你好,我是 ${persona.emoji} **${persona.display_name}**。`,
    '',
    `我收到你的请求:"${message.slice(0, 80)}${message.length > 80 ? '...' : ''}"。`,
    '',
    persona.is_implemented
      ? `根据你的描述,我的初步建议如下:`
      : `> ⚠️ 当前 persona 尚在 P9+ 规划中,我先用通用智能体回答,正式能力即将上线。`,
    '',
    '1. 先理清核心诉求和约束条件',
    '2. 调用相关数据源（参考"能力"标签页可点击的能力卡片）',
    '3. 给出可执行的下一步建议',
    '',
    `如果你想直接尝试我的具体能力,可以切到 **能力** 标签页一键触发。`,
  ]
  return lines.join('\n')
}

export async function mockChatWithPersona(
  personaId: string,
  body: MockChatRequest,
): Promise<MockChatResponse> {
  const persona = getPersonaMeta(personaId)
  if (!persona) {
    throw new Error(`未知 persona: ${personaId}`)
  }
  // 模拟一个全文耗时
  await delay(500)
  return {
    persona_id: personaId,
    content: fakeAnswer(persona, body.message),
    metadata: {
      mock: true,
      is_implemented: persona.is_implemented,
      tokens: 128,
    },
  }
}

/**
 * 假 stream：每 TOKEN_DELAY_MS 吐 1 个字。
 *
 * 调用方在 onToken 里追加渲染,在 onDone 里收尾。
 */
export async function mockStreamChat(
  personaId: string,
  body: MockChatRequest,
  callbacks: {
    onToken: (chunk: string) => void
    onDone: (resp: MockChatResponse) => void
    onError?: (err: Error) => void
  },
): Promise<void> {
  try {
    const persona = getPersonaMeta(personaId)
    if (!persona) {
      throw new Error(`未知 persona: ${personaId}`)
    }
    const full = fakeAnswer(persona, body.message)
    let acc = ''
    for (const ch of full) {
      await delay(TOKEN_DELAY_MS / 8) // 每 25ms 吐一字符,避免太慢
      acc += ch
      callbacks.onToken(ch)
    }
    callbacks.onDone({
      persona_id: personaId,
      content: acc,
      metadata: { mock: true, streamed: true, is_implemented: persona.is_implemented },
    })
  } catch (e) {
    if (callbacks.onError) {
      callbacks.onError(e instanceof Error ? e : new Error(String(e)))
    }
  }
}

// ---------- capability 触发 ----------

const CAPABILITY_DATA_TEMPLATES: Record<string, (cap: PersonaCapability, persona: PersonaMeta) => string> = {
  // 流程管家
  okr_dashboard: () =>
    [
      '## 本季度 OKR 进度（mock）',
      '',
      '| 编号 | 目标 | 关键结果 | 进度 |',
      '|---|---|---|---|',
      '| O1 | 增长营收 30% | KR1 新客户 80 家 | 🟢 62/80 (77%) |',
      '|    |             | KR2 老客复购率 ≥ 45% | 🟡 41% |',
      '| O2 | 出海首单 | KR1 注册英国子公司 | 🟢 已完成 |',
      '|    |             | KR2 独立站 GMV $50k | 🔴 $12k (24%) |',
    ].join('\n'),
  weekly_report: () =>
    [
      '## 本周周报草稿（已聚合飞书任务 23 项 + 日历 18 个 + OKR 5 项）',
      '',
      '### 本周亮点',
      '- 完成 V3.2 用户中心改版评审（4/22）',
      '- 签下 XX 客户大单 ¥280 万（4/24）',
      '',
      '### 风险 / 求助',
      '- 性能优化人手不足,需借调 1 人',
      '',
      '### 下周计划',
      '- 启动 V3.3 排期评审',
      '- 完成出海独立站第一阶段验收',
    ].join('\n'),
  // 市场研究员
  industry_trends: () =>
    [
      '## LED 封装赛道 3 年趋势（mock）',
      '',
      '**市场容量**: 2026→2029 CAGR 12.4%',
      '',
      '### 三大趋势',
      '1. 小间距 LED 加速渗透 — P2.5→P1.5',
      '2. Mini/Micro LED 量产成本预计 2027 年降至 P1.0 等价',
      '3. 国产替代深化 — 国巨/隆达退出,三安/华灿接单',
      '',
      '### 风险提示',
      '- 上游芯片价格波动',
      '- 美国 BIS 出口管制 → 影响 Mini LED 设备进口',
    ].join('\n'),
  // 获客猎手
  discover_leads: () =>
    [
      '## 线索挖掘结果（mock,共 200 条）',
      '',
      '| 公司 | 行业 | 规模 | LeadScore |',
      '|---|---|---|---|',
      '| XX 精密 | 五金 | 200-500 | 🟢 87 |',
      '| YY 制造 | 五金 | 100-200 | 🟡 62 |',
      '| ZZ 工业 | 五金 | 500+   | 🟢 91 |',
      '| ... | ... | ... | ... |',
      '',
      '> 已按 LeadScore 排序,Top 50 已写入 HubSpot,可在 CRM 同步。',
    ].join('\n'),
  // 跨境电商
  analyze_niche: () =>
    [
      '## 选品分析:可折叠桌（mock,Accio Ecommerce Mind 范式）',
      '',
      '### ✅ 市场信号',
      '- TikTok #FoldableTable 30 天 +218% 播放',
      '- Amazon BSR 上升 47%（Garden & Outdoor）',
      '- Google Trends 北美区热度持续 4 周上扬',
      '',
      '### 🔴 风险信号',
      '- Top 10 卖家利润率压到 8%（红海化）',
      '- 专利风险:XX 公司持有折叠机构专利 → 必须避开',
      '',
      '### 🟢 差异化机会',
      '- 带 USB 插座的可折叠桌 — 搜索量上升、供给少',
      '- 碳纤维超轻款 — 客单价 $200+ 利润空间大',
      '',
      '> 多 agent 投票 3:2 → 建议做差异化款,首批 ≤ 500 件试水。',
    ].join('\n'),
}

function defaultCapabilityResult(cap: PersonaCapability, persona: PersonaMeta): string {
  return [
    `## ${persona.emoji} ${persona.display_name} · ${cap.label}（mock）`,
    '',
    `> 触发提示: \`${cap.prompt}\``,
    '',
    persona.is_implemented
      ? '✅ 该能力已在后端实装,真接入后将返回真实结构化数据。'
      : '🚧 该能力规划中,当前为占位 mock。',
    '',
    '### 步骤示例',
    '1. 解析请求并选择数据源',
    '2. 调用 specialized agent 协同',
    '3. 输出结构化结果（含引文）',
  ].join('\n')
}

export async function mockRunCapability(
  personaId: string,
  capabilityId: string,
): Promise<MockCapabilityResult> {
  const persona = getPersonaMeta(personaId)
  if (!persona) {
    throw new Error(`未知 persona: ${personaId}`)
  }
  const cap = persona.capabilities.find((c) => c.id === capabilityId)
  if (!cap) {
    throw new Error(`未知 capability: ${capabilityId}`)
  }
  await delay(600)
  const tpl = CAPABILITY_DATA_TEMPLATES[capabilityId]
  return {
    persona_id: personaId,
    capability_id: capabilityId,
    content: tpl ? tpl(cap, persona) : defaultCapabilityResult(cap, persona),
    metadata: { mock: true, capability_label: cap.label },
  }
}
