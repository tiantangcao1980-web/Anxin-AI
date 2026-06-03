// -*- coding: utf-8 -*-
/**
 * IM Channels API（与 web/frontend/src/lib/api/imChannels.ts 契约对齐）
 *
 * 对应后端 6 端点（已实测 200）：
 *   GET  /im/channels                       backend im_channels.py:57  列出当前组织全部渠道（裸 IMChannel[]）
 *   POST /im/channels/{channelType}/setup   backend im_channels.py:73  配置/重配某类型渠道
 *   PUT  /im/channels/{id}/agent            backend im_channels.py:108 绑定 agent persona
 *   PUT  /im/channels/{id}/enable           backend im_channels.py:133 启用渠道
 *   PUT  /im/channels/{id}/disable          backend im_channels.py:150 停用渠道
 *   GET  /im/channels/{id}/test             backend im_channels.py:172 连接自检
 *
 * 路由前缀：api/routes/__init__.py:155 以 prefix="/im" 注册 →
 *           baseUrl 已含 /api/v1，故 path 传相对 /im/channels。
 *
 * ⚠️ apiClient.get 返回的是直接 body（经 unwrap 兼容 {code,data} 包装；
 *    后端 GET /im/channels 返回裸数组，无 {items} 外层），按裸数组解析。
 */

import { apiClient } from './client'

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
  config: Record<string, unknown>
  enabled: boolean
  status: IMChannelStatus
  bound_agent_persona: string | null
  stats: IMChannelStats
  created_at: string
}

export interface SetupChannelRequest {
  config: Record<string, unknown>
}

export interface BindAgentRequest {
  agent_persona: string
}

export interface TestConnectionResult {
  ok: boolean
  message?: string
  detail?: Record<string, unknown>
}

// ===== API 实现 =====

export async function listChannels(): Promise<IMChannel[]> {
  // 后端 GET /im/channels 返回裸 IMChannel[]（非 {items} 包装），直接解析。
  const res = await apiClient.get<IMChannel[]>('/im/channels')
  return res ?? []
}

export async function setupChannel(
  channelType: IMChannelType,
  body: SetupChannelRequest,
): Promise<IMChannel> {
  return apiClient.post<IMChannel>(`/im/channels/${channelType}/setup`, body)
}

export async function bindAgent(
  id: string,
  body: BindAgentRequest,
): Promise<IMChannel> {
  return apiClient.put<IMChannel>(`/im/channels/${id}/agent`, body)
}

export async function enableChannel(id: string): Promise<IMChannel> {
  return apiClient.put<IMChannel>(`/im/channels/${id}/enable`)
}

export async function disableChannel(id: string): Promise<IMChannel> {
  return apiClient.put<IMChannel>(`/im/channels/${id}/disable`)
}

export async function testConnection(id: string): Promise<TestConnectionResult> {
  return apiClient.get<TestConnectionResult>(`/im/channels/${id}/test`)
}

/** 渠道类型 → emoji 图标（能力中心卡片用，原置于 capabilities/_mock）。 */
const IM_CHANNEL_ICONS: Record<IMChannelType, string> = {
  feishu: '🪶',
  wechat: '💬',
  dingtalk: '🟦',
  telegram: '✈️',
  discord: '🎮',
  slack: '💬',
}

export function iconOf(channelType: IMChannelType): string {
  return IM_CHANNEL_ICONS[channelType] ?? '💬'
}

export const imChannelsApi = {
  listChannels,
  // 页面以 `imChannelsApi.list()` 调用（与原 mock 同名），保持兼容。
  list: listChannels,
  setupChannel,
  bindAgent,
  enableChannel,
  disableChannel,
  testConnection,
  iconOf,
}
