// -*- coding: utf-8 -*-
/**
 * Skills API（小程序 V3 真实客户端，对标 mobile/src/lib/api/skills.ts）。
 *
 * 走真实后端（已实测端点）：
 *   - GET  /skills                 列表（backend/src/api/routes/skills.py:92，返回 {items,total}）
 *   - PUT  /skills/{name}/toggle   启停（skills.py:265，请求体 {enabled}）
 *
 * ⚠️ 小程序 apiClient.get/put 已 unwrap，返回的是裸 body（非 {data} 包装）。
 *    GET /skills 后端用 SkillListOut（{items,total}）包装，故此处读 .items。
 *
 * 仅暴露能力中心当前用到的 list / toggle，并 re-export 页面所需的域常量
 * （DOMAIN_LABELS / DOMAIN_ORDER），让页面只换 import 路径即可去 mock。
 */

import { apiClient } from './client'

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

/** 页面渲染所需的最小 Skill 形状（后端 SkillSummaryOut 字段更多，此处取子集）。 */
export interface Skill {
  name: string
  display_name: string
  description: string
  category: SkillCategory
  enabled: boolean
  triggers: string[]
  requires_apps: string[]
}

interface SkillListOut {
  items?: Skill[]
  total?: number
}

export async function listSkills(): Promise<Skill[]> {
  // 后端返回 SkillListOut（{items,total}）；兼容裸数组。
  const res = await apiClient.get<Skill[] | SkillListOut>('/skills')
  if (Array.isArray(res)) return res
  return res?.items ?? []
}

export async function toggleSkill(name: string, enabled: boolean): Promise<Skill> {
  return apiClient.put<Skill>(`/skills/${encodeURIComponent(name)}/toggle`, {
    enabled,
  })
}

export const skillsApi = {
  list: listSkills,
  toggle: toggleSkill,
}

// ===== 页面所需的域显示常量（原置于 _mock，迁出以便去 mock）=====

export const DOMAIN_LABELS: Record<SkillCategory, string> = {
  legal: '法律',
  tax_finance: '财税',
  operations: '运营',
  research: '调研',
  marketing: '营销',
  content: '内容',
  design: '设计',
  office: '办公',
  ecommerce: '电商',
  sales: '销售',
  intelligence: '情报',
  decision: '决策',
  system: '系统',
}

export const DOMAIN_ORDER: SkillCategory[] = [
  'legal',
  'tax_finance',
  'operations',
  'research',
  'marketing',
  'content',
  'design',
  'office',
  'ecommerce',
  'sales',
  'intelligence',
  'decision',
  'system',
]
