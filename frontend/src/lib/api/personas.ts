/**
 * Personas API Client (V3 智能体 P8-C)
 *
 * 通用 endpoint REST 封装，沿用 P3-C / P5-F 的"真 API + Mock 双轨"模式。
 *
 * 通过环境变量 `VITE_PERSONAS_MOCK=true` 切换到 mock 适配层
 * （在后端 P7 5 个 persona 已实装、其余 5 个法务 persona 仍未实装时
 * 仍可前端联调）。
 *
 * 后端契约：参见 `backend/src/api/routes/personas.py`
 *   - GET    /api/v1/personas                        列出
 *   - GET    /api/v1/personas/{persona_id}           详情
 *   - POST   /api/v1/personas/{persona_id}/chat      通用对话
 *
 * 各 persona 专属 endpoint（如 /personas/operations/okr/dashboard）
 * 由各自 specialized hook / page 直接实现，不在此处统一封装。
 */

import { getTokenStorage } from '@/lib/platform/storage'

// ===== 类型（与后端 schemas/persona.py 对齐） =====

/** 后端已实装 5 个 persona + 待规划 5 个法务 persona */
export type PersonaId =
  | 'anxin_assistant'
  | 'legal_advisor'
  | 'contract_steward'
  | 'due_diligence_expert'
  | 'tax_finance_advisor'
  | 'operations_manager'
  | 'market_researcher'
  | 'lead_hunter'
  | 'content_director'
  | 'ecommerce_assistant'

export interface Persona {
  persona_id: string
  display_name: string
  emoji: string
  description: string
  capabilities: string[]
  backed_by_skills: string[]
  supported_apps: string[]
  enabled?: boolean
  /**
   * 前端扩展字段（非后端 schema）：标识该 persona 是否已在 P7 后端实装。
   * 未实装的（5 个法务 persona）仍可点击进入工作台，但会显示"规划中"提示
   * 并降级到通用 chat 端点（占位）。
   */
  is_implemented?: boolean
  /** 业务域分组：综合协调 / 合规经营 / 增长获客 / 出海跨境 */
  domain?: PersonaDomain
}

export type PersonaDomain = '综合协调' | '合规经营' | '增长获客' | '出海跨境'

export interface PersonaDetail extends Persona {
  backed_by_agents?: string[]
  system_prompt_excerpt?: string
}

export interface PersonaListOut {
  items: Persona[]
  total: number
}

export interface ChatHistoryItem {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatRequest {
  message: string
  history?: ChatHistoryItem[]
  extra?: Record<string, unknown>
}

export interface ChatResponse {
  persona_id: string
  content: string
  metadata: Record<string, unknown>
}

// ===== Mock 切换开关 =====

const USE_MOCK = import.meta.env.VITE_PERSONAS_MOCK === 'true'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// ===== 通用 fetch 封装 =====

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const storage = getTokenStorage()
  const token = await storage.getAccessToken()
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  }
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers })
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<T>
}

// ===== 真实 API 实现 =====

async function realListPersonas(): Promise<Persona[]> {
  const res = await authFetch('/personas')
  const data = await jsonOrThrow<PersonaListOut>(res)
  return data.items
}

async function realGetPersona(personaId: string): Promise<PersonaDetail> {
  const res = await authFetch(`/personas/${encodeURIComponent(personaId)}`)
  return jsonOrThrow<PersonaDetail>(res)
}

async function realChatWithPersona(
  personaId: string,
  body: ChatRequest,
): Promise<ChatResponse> {
  const res = await authFetch(`/personas/${encodeURIComponent(personaId)}/chat`, {
    method: 'POST',
    body: JSON.stringify({
      message: body.message,
      history: body.history ?? [],
      extra: body.extra ?? {},
    }),
  })
  return jsonOrThrow<ChatResponse>(res)
}

// ===== Mock 适配（懒加载） =====

type MockApi = typeof import('./__mocks__/personas.mock')

let mockPromise: Promise<MockApi> | null = null
async function mock(): Promise<MockApi> {
  if (!mockPromise) {
    mockPromise = import('./__mocks__/personas.mock')
  }
  return mockPromise
}

// ===== 对外导出（按 USE_MOCK 路由） =====

export async function listPersonas(): Promise<Persona[]> {
  if (USE_MOCK) return (await mock()).mockListPersonas()
  return realListPersonas()
}

export async function getPersona(personaId: string): Promise<PersonaDetail> {
  if (USE_MOCK) return (await mock()).mockGetPersona(personaId)
  return realGetPersona(personaId)
}

export async function chatWithPersona(
  personaId: string,
  body: ChatRequest,
): Promise<ChatResponse> {
  if (USE_MOCK) return (await mock()).mockChatWithPersona(personaId, body)
  return realChatWithPersona(personaId, body)
}

export const personasApi = {
  list: listPersonas,
  get: getPersona,
  chat: chatWithPersona,
}
