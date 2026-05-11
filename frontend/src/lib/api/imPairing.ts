/**
 * IM Pairing API Client (V3 配对授权 P3)
 *
 * 5 endpoint REST 封装,管理 IM 渠道用户与智能体之间的配对授权关系。
 *
 * 业务流:
 *   1. 用户在 IM 渠道触发 agent → 系统创建 PairingRequest (24h 有效)
 *   2. 管理员审批 (approve / reject)
 *   3. 通过后写入 IMBinding (已授权用户)
 *
 * 通过环境变量 `VITE_PAIRING_MOCK=true` 可切换到 mock 适配层
 * (便于在后端 P3-B 尚未就绪时跑通前端联调)。
 */

import { getTokenStorage } from '@/lib/platform/storage'

// ===== 类型定义(与后端 contract 对齐) =====

export type ChannelType = 'feishu' | 'wechat' | 'dingtalk' | 'telegram' | 'discord'

export type PairingStatus = 'pending' | 'approved' | 'rejected' | 'expired'

/**
 * 配对请求(待审批,24h 内有效)
 */
export interface PairingRequest {
  id: string
  channel_id: string
  channel_type: ChannelType
  channel_name: string // 渠道显示名,如 "市场部飞书"
  external_user_id: string
  external_user_name: string // 外部用户显示名(飞书/钉钉昵称)
  external_user_avatar?: string
  external_group_name?: string // 群聊场景:群名
  status: PairingStatus
  expires_at: string // ISO 时间,24h 后过期
  created_at: string
  approved_at: string | null
  approved_by: string | null
  rejection_reason: string | null
}

/**
 * 已授权绑定(approve 后落表)
 */
export interface IMBinding {
  id: string
  channel_id: string
  channel_type: ChannelType
  channel_name: string
  external_user_id: string
  external_user_name: string
  external_user_avatar?: string
  internal_user_id: string
  bound_at: string
  last_active_at: string | null
}

export interface RejectPairingRequest {
  reason: string
}

// ===== Mock 切换开关 =====

const USE_MOCK = import.meta.env.VITE_PAIRING_MOCK === 'true'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// ===== 通用 fetch 封装 =====

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const storage = getTokenStorage()
  const token = await storage.getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
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

async function realListPending(): Promise<PairingRequest[]> {
  const res = await authFetch('/im/pairing/pending')
  return jsonOrThrow<PairingRequest[]>(res)
}

async function realApprovePairing(id: string): Promise<PairingRequest> {
  const res = await authFetch(`/im/pairing/${id}/approve`, { method: 'POST' })
  return jsonOrThrow<PairingRequest>(res)
}

async function realRejectPairing(
  id: string,
  body: RejectPairingRequest,
): Promise<PairingRequest> {
  const res = await authFetch(`/im/pairing/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return jsonOrThrow<PairingRequest>(res)
}

async function realListAuthorized(): Promise<IMBinding[]> {
  const res = await authFetch('/im/pairing/authorized')
  return jsonOrThrow<IMBinding[]>(res)
}

async function realRevokeBinding(id: string): Promise<void> {
  const res = await authFetch(`/im/bindings/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`)
  }
}

// ===== Mock 适配(懒加载,避免 build 把 mock 数据打入正式产物) =====

type MockApi = typeof import('./__mocks__/imPairing.mock')

let mockPromise: Promise<MockApi> | null = null
async function mock(): Promise<MockApi> {
  if (!mockPromise) {
    mockPromise = import('./__mocks__/imPairing.mock')
  }
  return mockPromise
}

// ===== 对外导出(根据 USE_MOCK 路由到 mock 或真实实现) =====

export async function listPending(): Promise<PairingRequest[]> {
  if (USE_MOCK) return (await mock()).mockListPending()
  return realListPending()
}

export async function approvePairing(id: string): Promise<PairingRequest> {
  if (USE_MOCK) return (await mock()).mockApprovePairing(id)
  return realApprovePairing(id)
}

export async function rejectPairing(
  id: string,
  body: RejectPairingRequest,
): Promise<PairingRequest> {
  if (USE_MOCK) return (await mock()).mockRejectPairing(id, body)
  return realRejectPairing(id, body)
}

export async function listAuthorized(): Promise<IMBinding[]> {
  if (USE_MOCK) return (await mock()).mockListAuthorized()
  return realListAuthorized()
}

export async function revokeBinding(id: string): Promise<void> {
  if (USE_MOCK) return (await mock()).mockRevokeBinding(id)
  return realRevokeBinding(id)
}

export const imPairingApi = {
  listPending,
  approvePairing,
  rejectPairing,
  listAuthorized,
  revokeBinding,
}
