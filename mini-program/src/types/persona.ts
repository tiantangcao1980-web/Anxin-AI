// -*- coding: utf-8 -*-
/**
 * Persona 类型（与 frontend/src/lib/api/personas.ts、backend/schemas/persona.py 对齐）
 */

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
