/**
 * Skills API Client (V3 技能 P5-F)
 *
 * 6 endpoint REST 封装，沿用 P3-C / P4-F 的"真 API + Mock 双轨"模式。
 *
 * 通过环境变量 `VITE_SKILLS_MOCK=true` 切换到 mock 适配层
 * （在后端 P5-A 上线前完成前端联调）。
 */

import { getTokenStorage } from '@/lib/platform/storage'

// ===== 类型定义（与后端 P5-A contract 对齐） =====

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
  /** 唯一 ID，例如 "office/docx" */
  name: string
  display_name: string
  description: string
  version: string
  category: SkillCategory
  type: SkillType
  author: string
  triggers: string[]
  /** 适配的 user-facing personas（即可用于哪些 agent） */
  personas: string[]
  /** OAuth provider 依赖，例如 ["feishu", "notion"] */
  requires_apps: string[]
  /** 内部 skill 依赖，例如 ["office/docx", "legal/clause-extract"] */
  dependencies: string[]
  keywords: string[]
  enabled: boolean
  icon?: string
  /** 详情 body 前 200 字摘要（list 接口返回） */
  body_excerpt?: string
  /** 完整 body markdown（仅 detail 接口返回） */
  body?: string
}

export interface SkillExecuteResult {
  ok: boolean
  output: unknown
  duration_ms: number
  trace_id?: string
  error?: string
}

export interface SkillUploadResult {
  skill: Skill
  warnings: string[]
}

export interface ListSkillsParams {
  category?: SkillCategory | string
  persona?: string
  enabled?: boolean
}

// ===== Mock 切换开关 =====

const USE_MOCK = import.meta.env.VITE_SKILLS_MOCK === 'true'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// ===== 通用 fetch 封装 =====

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const storage = getTokenStorage()
  const token = await storage.getAccessToken()
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  }
  // 仅当 body 存在且不是 FormData 时设置 JSON content-type
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

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const usp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === '' || v === null) continue
    usp.set(k, String(v))
  }
  const s = usp.toString()
  return s ? `?${s}` : ''
}

// ===== 真实 API 实现 =====

async function realListSkills(params: ListSkillsParams = {}): Promise<Skill[]> {
  const qs = buildQuery({
    category: params.category,
    persona: params.persona,
    enabled: params.enabled,
  })
  const res = await authFetch(`/skills${qs}`)
  return jsonOrThrow<Skill[]>(res)
}

async function realGetSkill(name: string): Promise<Skill> {
  const res = await authFetch(`/skills/${encodeURIComponent(name)}`)
  return jsonOrThrow<Skill>(res)
}

async function realUploadSkill(file: File): Promise<SkillUploadResult> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await authFetch('/skills/upload', { method: 'POST', body: fd })
  return jsonOrThrow<SkillUploadResult>(res)
}

async function realToggleSkill(name: string, enabled: boolean): Promise<Skill> {
  const res = await authFetch(`/skills/${encodeURIComponent(name)}/toggle`, {
    method: 'PUT',
    body: JSON.stringify({ enabled }),
  })
  return jsonOrThrow<Skill>(res)
}

async function realExecuteSkill(
  name: string,
  payload: unknown,
): Promise<SkillExecuteResult> {
  const res = await authFetch(`/skills/${encodeURIComponent(name)}/execute`, {
    method: 'POST',
    body: JSON.stringify({ payload }),
  })
  return jsonOrThrow<SkillExecuteResult>(res)
}

async function realMatchTriggers(q: string): Promise<Skill[]> {
  const res = await authFetch(`/skills/triggers/match${buildQuery({ q })}`)
  return jsonOrThrow<Skill[]>(res)
}

// ===== Mock 适配（懒加载） =====

type MockApi = typeof import('./__mocks__/skills.mock')

let mockPromise: Promise<MockApi> | null = null
async function mock(): Promise<MockApi> {
  if (!mockPromise) {
    mockPromise = import('./__mocks__/skills.mock')
  }
  return mockPromise
}

// ===== 对外导出（按 USE_MOCK 路由） =====

export async function listSkills(params: ListSkillsParams = {}): Promise<Skill[]> {
  if (USE_MOCK) return (await mock()).mockListSkills(params)
  return realListSkills(params)
}

export async function getSkill(name: string): Promise<Skill> {
  if (USE_MOCK) return (await mock()).mockGetSkill(name)
  return realGetSkill(name)
}

export async function uploadSkill(file: File): Promise<SkillUploadResult> {
  if (USE_MOCK) return (await mock()).mockUploadSkill(file)
  return realUploadSkill(file)
}

export async function toggleSkill(name: string, enabled: boolean): Promise<Skill> {
  if (USE_MOCK) return (await mock()).mockToggleSkill(name, enabled)
  return realToggleSkill(name, enabled)
}

export async function executeSkill(
  name: string,
  payload: unknown,
): Promise<SkillExecuteResult> {
  if (USE_MOCK) return (await mock()).mockExecuteSkill(name, payload)
  return realExecuteSkill(name, payload)
}

export async function matchTriggers(q: string): Promise<Skill[]> {
  if (USE_MOCK) return (await mock()).mockMatchTriggers(q)
  return realMatchTriggers(q)
}

export const skillsApi = {
  list: listSkills,
  get: getSkill,
  upload: uploadSkill,
  toggle: toggleSkill,
  execute: executeSkill,
  matchTriggers,
}
