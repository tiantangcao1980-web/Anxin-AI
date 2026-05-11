/**
 * V3 personas E2E 共享 helper（P14-A）
 *
 * 职责：
 *   1. 复用 frontend/e2e/helpers/session.ts 的 installApiMocks + seedAuthState
 *   2. 在它们之上，叠加 V3 personas 专用 API mock：
 *        GET  /personas              → 10 个 persona 列表
 *        GET  /personas/{id}         → 单个 persona 详情
 *        POST /personas/{id}/chat    → mock 应答（含 emoji + display_name + 免责声明）
 *
 * 注：不修改 helpers/session.ts（严格文件边界）；persona route 必须在
 * installApiMocks 之前注册，让它先匹配（Playwright route 按"先注册先匹配"）。
 */

import type { Page } from '@playwright/test'

import { installApiMocks, seedAuthState } from '../../helpers/session'

// ===== 与 frontend/src/lib/api/__mocks__/personas.mock.ts 对齐的 10 个 persona =====

export interface MockPersona {
  persona_id: string
  display_name: string
  emoji: string
  description: string
  capabilities: string[]
  backed_by_skills: string[]
  supported_apps: string[]
  enabled: boolean
  is_implemented: boolean
  domain: string
}

export const MOCK_PERSONAS: MockPersona[] = [
  {
    persona_id: 'anxin_assistant',
    display_name: '安心助理',
    emoji: '🤖',
    description: '通用入口 + 任务编排，不知道找谁就找它',
    domain: '综合协调',
    enabled: true,
    is_implemented: false,
    capabilities: [
      '意图识别（自然语言路由到正确 persona）',
      '任务拆解（复杂请求 → 多 persona 协作 DAG）',
      '多 agent 协商（分歧时 consensus_agent 投票）',
      '统一收件箱（聚合所有 persona 进度 / 结果）',
      '上下文续接（跨 persona 共享会话）',
    ],
    backed_by_skills: ['system/intent-router', 'system/task-graph'],
    supported_apps: ['feishu', 'dingtalk', 'wecom'],
  },
  {
    persona_id: 'legal_advisor',
    display_name: '法律顾问',
    emoji: '⚖️',
    description: '你的随身法律大脑，问法条、判例、风险，全靠我',
    domain: '合规经营',
    enabled: true,
    is_implemented: false,
    capabilities: [
      '法规检索（北大法宝 / 威科 / 国务院政策库，带源链接）',
      '法律咨询（基于业务上下文给可执行建议）',
      '风险评估（5 级风险分级 + 量化评分）',
      '法规监测（自动追踪相关法规变更并推送）',
      '判例检索（33,102 条文书库 + 类案推送）',
    ],
    backed_by_skills: ['legal/regulation-search', 'legal/case-search'],
    supported_apps: ['北大法宝', '威科先行'],
  },
  // 剩余 8 个用占位骨架补齐 —— E2E 只需要 list 长度 = 10，不用全字段
  ...['contract_steward', 'due_diligence_expert', 'tax_finance_advisor'].map<MockPersona>((id) => ({
    persona_id: id,
    display_name: id,
    emoji: '📜',
    description: 'mock 占位（合规域）',
    domain: '合规经营',
    enabled: true,
    is_implemented: false,
    capabilities: ['mock 能力 1', 'mock 能力 2'],
    backed_by_skills: [],
    supported_apps: [],
  })),
  ...[
    'operations_manager',
    'market_researcher',
    'lead_hunter',
    'content_director',
    'ecommerce_assistant',
  ].map<MockPersona>((id) => ({
    persona_id: id,
    display_name: id,
    emoji: '📋',
    description: 'mock 占位（已实装）',
    domain: '综合协调',
    enabled: true,
    is_implemented: true,
    capabilities: ['mock 已实装能力 A', 'mock 已实装能力 B'],
    backed_by_skills: [],
    supported_apps: [],
  })),
]

export function getMockPersona(personaId: string): MockPersona {
  const p = MOCK_PERSONAS.find((x) => x.persona_id === personaId)
  if (!p) throw new Error(`mock: persona 不存在 ${personaId}`)
  return p
}

interface SetupOptions {
  /** 默认 enterprise_user；可覆盖 */
  role?: string
  /** chat 端点的自定义应答（按 personaId 匹配）；不传则走默认 mock */
  chatOverrides?: Record<string, (message: string) => string>
  /** 强制 list 接口报错以测错误态 */
  failList?: boolean
  /** 强制 chat 接口报错以测错误态 */
  failChat?: boolean
}

/**
 * 安装 V3 personas E2E 的完整 mock 环境：
 *   - persona list / get / chat
 *   - 通用 API mock（auth/me、notifications、harness……）
 *   - 已 seed 的 localStorage 鉴权
 *
 * 用法：
 *   test.beforeEach(async ({ page }) => {
 *     await setupPersonaSession(page, { role: 'enterprise_user' })
 *     await page.goto('/agents')
 *   })
 */
export async function setupPersonaSession(page: Page, options: SetupOptions = {}) {
  const { role = 'enterprise_user', chatOverrides, failList, failChat } = options

  // 1) 先注册 personas 专用路由（先注册 = 先匹配）
  await page.route('**/api/v1/personas', async (route) => {
    if (failList) {
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'mock: list 失败' }),
      })
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: MOCK_PERSONAS, total: MOCK_PERSONAS.length }),
    })
  })

  await page.route('**/api/v1/personas/*', async (route) => {
    const url = new URL(route.request().url())
    const segments = url.pathname.split('/').filter(Boolean)
    const personaId = decodeURIComponent(segments[segments.length - 1] ?? '')
    const persona = MOCK_PERSONAS.find((p) => p.persona_id === personaId)
    if (!persona) {
      return route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: `persona 不存在 ${personaId}` }),
      })
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...persona,
        backed_by_agents: [],
        system_prompt_excerpt: `你是「${persona.display_name}」persona — ${persona.description}`,
      }),
    })
  })

  await page.route('**/api/v1/personas/*/chat', async (route) => {
    const url = new URL(route.request().url())
    const segments = url.pathname.split('/').filter(Boolean)
    // .../personas/{id}/chat → 倒数第二段
    const personaId = decodeURIComponent(segments[segments.length - 2] ?? '')

    if (failChat) {
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'mock: chat 失败' }),
      })
    }

    const persona = MOCK_PERSONAS.find((p) => p.persona_id === personaId)
    if (!persona) {
      return route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: `persona 不存在 ${personaId}` }),
      })
    }

    const body = route.request().postDataJSON() as { message?: string } | null
    const message = body?.message ?? ''

    let content: string
    const overrideFn = chatOverrides?.[personaId]
    if (overrideFn) {
      content = overrideFn(message)
    } else {
      content = defaultChatResponse(persona, message)
    }

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        persona_id: personaId,
        content,
        metadata: {
          mock: true,
          is_implemented: persona.is_implemented,
          display_name: persona.display_name,
        },
      }),
    })
  })

  // 2) 再装通用 mock（覆盖 auth/me、notifications 等）
  await installApiMocks(page)

  // 3) seed 鉴权状态（addInitScript，必须在 goto 前）
  await seedAuthState(page, {
    role,
    name: 'E2E 用户',
    email: 'e2e@anxin-assistant.com',
  })
}

function defaultChatResponse(persona: MockPersona, message: string): string {
  const lines: string[] = []
  if (persona.persona_id === 'legal_advisor') {
    // 法律顾问：必含免责声明 + 法条引用样式
    lines.push(`${persona.emoji} **${persona.display_name}**：收到「${message.slice(0, 60)}」`)
    lines.push('')
    lines.push('**初步法律意见：**')
    lines.push('根据《劳动合同法》第十九条，试用期最长不得超过六个月。')
    lines.push('')
    lines.push(
      '**免责声明：** 本回答仅供参考，不构成正式法律意见。具体案件请咨询执业律师。',
    )
  } else if (persona.persona_id === 'anxin_assistant') {
    // 安心助理：必含意图分类 + 推荐 persona 列表
    lines.push(`${persona.emoji} **${persona.display_name}**：识别到您的意图`)
    lines.push('')
    lines.push('**推荐 persona：**')
    lines.push('- ⚖️ 法律顾问 — 适合「法规咨询」类问题')
    lines.push('- 📜 合同管家 — 适合「合同条款」类问题')
    lines.push('- 🔍 尽调专家 — 适合「背调风险」类问题')
  } else {
    lines.push(`${persona.emoji} **${persona.display_name}**：收到「${message.slice(0, 60)}」`)
  }
  return lines.join('\n')
}
