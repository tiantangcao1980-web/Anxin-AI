// -*- coding: utf-8 -*-
/**
 * Skills API（V3 移动端镜像）。
 *
 * 与 frontend/src/lib/api/skills.ts 同形契约，走真实后端：
 *   - GET  /skills                       列表（依据 backend/src/api/routes/skills.py:92）
 *   - PUT  /skills/{name}/toggle         启停（依据 skills.py:265）
 *
 * 仅暴露移动端能力中心当前用到的 list / toggle。
 */

import { getApiClient } from './client'

export type SkillCategory =
  | 'legal'
  | 'tax_finance'
  | 'operations'
  | 'research'
  | 'marketing'
  | 'content'
  | 'design'
  | 'office'
  | 'ecommerce'
  | 'sales'
  | 'intelligence'
  | 'decision'
  | 'system'

export type SkillType = 'tool' | 'workflow' | 'agent'

export interface Skill {
  name: string
  display_name: string
  description: string
  version: string
  category: SkillCategory
  type: SkillType
  author: string
  triggers: string[]
  personas: string[]
  requires_apps: string[]
  dependencies: string[]
  keywords: string[]
  enabled: boolean
  icon?: string
  body_excerpt?: string
  body?: string
}

export interface ListSkillsParams {
  category?: SkillCategory | string
  persona?: string
  enabled?: boolean
}

function buildParams(params: ListSkillsParams): Record<string, string> {
  const out: Record<string, string> = {}
  if (params.category) out.category = String(params.category)
  if (params.persona) out.persona = params.persona
  if (params.enabled !== undefined) out.enabled = String(params.enabled)
  return out
}

export async function listSkills(params: ListSkillsParams = {}): Promise<Skill[]> {
  const client = getApiClient()
  const res = await client.get<Skill[]>('/skills', { params: buildParams(params) })
  return res.data ?? []
}

export async function toggleSkill(name: string, enabled: boolean): Promise<Skill> {
  const client = getApiClient()
  const res = await client.put<Skill>(`/skills/${encodeURIComponent(name)}/toggle`, {
    enabled,
  })
  return res.data
}

export const skillsApi = {
  list: listSkills,
  toggle: toggleSkill,
}
