// -*- coding: utf-8 -*-
/**
 * Personas API（V3 移动端镜像）。
 *
 * 与 frontend/src/lib/api/personas.ts 类型一一对应：
 *   - GET    /personas                       列表
 *   - GET    /personas/{persona_id}          详情
 *   - POST   /personas/{persona_id}/chat     通用对话
 *
 * 后端契约：backend/src/api/routes/personas.py
 */

import { getApiClient } from './client'

/** V3 已规划 10 个 persona */
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

export type PersonaDomain = '综合协调' | '合规经营' | '增长获客' | '出海跨境'

export interface Persona {
  persona_id: string
  display_name: string
  emoji: string
  description: string
  capabilities: string[]
  backed_by_skills: string[]
  supported_apps: string[]
  enabled?: boolean
  is_implemented?: boolean
  domain?: PersonaDomain
}

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

export async function listPersonas(): Promise<Persona[]> {
  const client = getApiClient()
  const res = await client.get<PersonaListOut>('/personas')
  return res.data?.items ?? []
}

export async function getPersona(personaId: string): Promise<PersonaDetail> {
  const client = getApiClient()
  const res = await client.get<PersonaDetail>(`/personas/${encodeURIComponent(personaId)}`)
  return res.data
}

export async function chatWithPersona(
  personaId: string,
  body: ChatRequest,
): Promise<ChatResponse> {
  const client = getApiClient()
  const res = await client.post<ChatResponse>(
    `/personas/${encodeURIComponent(personaId)}/chat`,
    {
      message: body.message,
      history: body.history ?? [],
      extra: body.extra ?? {},
    },
  )
  return res.data
}

export const personasApi = {
  list: listPersonas,
  get: getPersona,
  chat: chatWithPersona,
}
