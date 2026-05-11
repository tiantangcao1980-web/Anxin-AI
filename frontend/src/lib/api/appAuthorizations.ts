/**
 * App Authorizations API Client (V3 应用授权 P4-F)
 *
 * 5 endpoint REST 封装，参考 P3-C imChannels 的"真 API + Mock 双轨"模式
 *
 * 通过环境变量 `VITE_APP_AUTH_MOCK=true` 可切换到 mock 适配层
 * （便于在后端 P4-A/B/C/D/E 尚未就绪时跑通前端联调）。
 */

import { getTokenStorage } from '@/lib/platform/storage'

// ===== 类型定义（与后端 contract 对齐） =====

export type AppCategory =
  | 'office'
  | 'office_storage'
  | 'crm'
  | 'ecommerce'
  | 'info_source'
  | 'design'
  | 'compliance'
  | 'finance'

export type AppAuthorizationStatus = 'connected' | 'expired' | 'revoked' | 'error'

export interface AppProvider {
  /** "feishu", "dingtalk", "notion", "shopify" 等 */
  provider_id: string
  display_name: string
  description: string
  category: AppCategory
  icon_url: string | null
  default_scopes: string[]
  documentation_url?: string
}

export interface AppAuthorization {
  id: string
  user_id: string
  provider_id: string
  status: AppAuthorizationStatus
  scopes: string[]
  connected_at: string
  last_refresh_at: string | null
  error_message: string | null
  /** 例如 "wenyu@example.com" 或 "shop1.myshopify.com" */
  account_label?: string
}

export interface StartConnectResponse {
  authorize_url: string
  state: string
}

// ===== Mock 切换开关 =====

const USE_MOCK = import.meta.env.VITE_APP_AUTH_MOCK === 'true'

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

async function okOrThrow(res: Response): Promise<void> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`)
  }
}

// ===== 真实 API 实现 =====

async function realListProviders(): Promise<AppProvider[]> {
  const res = await authFetch('/app-authorizations/providers')
  return jsonOrThrow<AppProvider[]>(res)
}

async function realListAuthorizations(): Promise<AppAuthorization[]> {
  const res = await authFetch('/app-authorizations')
  return jsonOrThrow<AppAuthorization[]>(res)
}

async function realStartConnect(providerId: string): Promise<StartConnectResponse> {
  const res = await authFetch(`/app-authorizations/${providerId}/start`, {
    method: 'POST',
  })
  return jsonOrThrow<StartConnectResponse>(res)
}

async function realRefresh(id: string): Promise<AppAuthorization> {
  const res = await authFetch(`/app-authorizations/${id}/refresh`, { method: 'POST' })
  return jsonOrThrow<AppAuthorization>(res)
}

async function realDisconnect(id: string): Promise<void> {
  const res = await authFetch(`/app-authorizations/${id}`, { method: 'DELETE' })
  await okOrThrow(res)
}

// ===== Mock 适配（懒加载） =====

type MockApi = typeof import('./__mocks__/appAuthorizations.mock')

let mockPromise: Promise<MockApi> | null = null
async function mock(): Promise<MockApi> {
  if (!mockPromise) {
    mockPromise = import('./__mocks__/appAuthorizations.mock')
  }
  return mockPromise
}

// ===== 对外导出（根据 USE_MOCK 路由到 mock 或真实实现） =====

export async function listProviders(): Promise<AppProvider[]> {
  if (USE_MOCK) return (await mock()).mockListProviders()
  return realListProviders()
}

export async function listAuthorizations(): Promise<AppAuthorization[]> {
  if (USE_MOCK) return (await mock()).mockListAuthorizations()
  return realListAuthorizations()
}

export async function startConnect(providerId: string): Promise<StartConnectResponse> {
  if (USE_MOCK) return (await mock()).mockStartConnect(providerId)
  return realStartConnect(providerId)
}

export async function refreshAuthorization(id: string): Promise<AppAuthorization> {
  if (USE_MOCK) return (await mock()).mockRefresh(id)
  return realRefresh(id)
}

export async function disconnectAuthorization(id: string): Promise<void> {
  if (USE_MOCK) return (await mock()).mockDisconnect(id)
  return realDisconnect(id)
}

export const appAuthorizationsApi = {
  listProviders,
  listAuthorizations,
  startConnect,
  refresh: refreshAuthorization,
  disconnect: disconnectAuthorization,
}
