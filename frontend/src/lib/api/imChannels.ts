/**
 * IM Channels API Client (V3 消息渠道 P3-C)
 *
 * 6 endpoint REST 封装，参考 P2 agentTasks 的"真 API + Mock 双轨"模式
 *
 * 通过环境变量 `VITE_IM_MOCK=true` 可切换到 mock 适配层
 * （便于在后端 P3-A/B 尚未就绪时跑通前端联调）。
 */

import { getTokenStorage } from '@/lib/platform/storage'

// ===== 类型定义（与后端 contract 对齐） =====

export type IMChannelType =
  | 'feishu'
  | 'wechat'
  | 'dingtalk'
  | 'telegram'
  | 'discord'
  | 'slack'

export type IMChannelStatus = 'unconfigured' | 'connecting' | 'connected' | 'error'

export interface IMChannelStats {
  bound_users: number
  bound_groups: number
  pending_pairings: number
}

export interface IMChannel {
  id: string
  channel_type: IMChannelType
  name: string
  config: Record<string, any>
  enabled: boolean
  status: IMChannelStatus
  bound_agent_persona: string | null
  stats: IMChannelStats
  created_at: string
}

export interface SetupChannelRequest {
  config: Record<string, any>
}

export interface BindAgentRequest {
  agent_persona: string
}

export interface TestConnectionResult {
  ok: boolean
  message?: string
  detail?: Record<string, any>
}

// ===== Mock 切换开关 =====

const USE_MOCK = import.meta.env.VITE_IM_MOCK === 'true'

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

async function realListChannels(): Promise<IMChannel[]> {
  const res = await authFetch('/im/channels')
  return jsonOrThrow<IMChannel[]>(res)
}

async function realSetupChannel(
  channelType: IMChannelType,
  body: SetupChannelRequest,
): Promise<IMChannel> {
  const res = await authFetch(`/im/channels/${channelType}/setup`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return jsonOrThrow<IMChannel>(res)
}

async function realBindAgent(id: string, body: BindAgentRequest): Promise<IMChannel> {
  const res = await authFetch(`/im/channels/${id}/agent`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
  return jsonOrThrow<IMChannel>(res)
}

async function realEnableChannel(id: string): Promise<IMChannel> {
  const res = await authFetch(`/im/channels/${id}/enable`, { method: 'PUT' })
  return jsonOrThrow<IMChannel>(res)
}

async function realDisableChannel(id: string): Promise<IMChannel> {
  const res = await authFetch(`/im/channels/${id}/disable`, { method: 'PUT' })
  return jsonOrThrow<IMChannel>(res)
}

async function realTestConnection(id: string): Promise<TestConnectionResult> {
  const res = await authFetch(`/im/channels/${id}/test`)
  return jsonOrThrow<TestConnectionResult>(res)
}

// ===== Mock 适配（懒加载） =====

type MockApi = typeof import('./__mocks__/imChannels.mock')

let mockPromise: Promise<MockApi> | null = null
async function mock(): Promise<MockApi> {
  if (!mockPromise) {
    mockPromise = import('./__mocks__/imChannels.mock')
  }
  return mockPromise
}

// ===== 对外导出（根据 USE_MOCK 路由到 mock 或真实实现） =====

export async function listChannels(): Promise<IMChannel[]> {
  if (USE_MOCK) return (await mock()).mockListChannels()
  return realListChannels()
}

export async function setupChannel(
  channelType: IMChannelType,
  body: SetupChannelRequest,
): Promise<IMChannel> {
  if (USE_MOCK) return (await mock()).mockSetupChannel(channelType, body)
  return realSetupChannel(channelType, body)
}

export async function bindAgent(id: string, body: BindAgentRequest): Promise<IMChannel> {
  if (USE_MOCK) return (await mock()).mockBindAgent(id, body)
  return realBindAgent(id, body)
}

export async function enableChannel(id: string): Promise<IMChannel> {
  if (USE_MOCK) return (await mock()).mockEnableChannel(id)
  return realEnableChannel(id)
}

export async function disableChannel(id: string): Promise<IMChannel> {
  if (USE_MOCK) return (await mock()).mockDisableChannel(id)
  return realDisableChannel(id)
}

export async function testConnection(id: string): Promise<TestConnectionResult> {
  if (USE_MOCK) return (await mock()).mockTestConnection(id)
  return realTestConnection(id)
}

export const imChannelsApi = {
  listChannels,
  setupChannel,
  bindAgent,
  enableChannel,
  disableChannel,
  testConnection,
}
