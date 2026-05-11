// -*- coding: utf-8 -*-
/**
 * IM Channels API（V3 移动端镜像）。
 *
 * 与 frontend/src/lib/api/imChannels.ts 同形契约：
 *   - GET    /im/channels                       列表
 *   - POST   /im/channels/{type}/setup          初始化
 *   - PUT    /im/channels/{id}/agent            绑定 agent
 *   - PUT    /im/channels/{id}/enable           启用
 *   - PUT    /im/channels/{id}/disable          停用
 *   - GET    /im/channels/{id}/test             连通性测试
 */

import { getApiClient } from './client'

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

export async function listChannels(): Promise<IMChannel[]> {
  const client = getApiClient()
  const res = await client.get<IMChannel[]>('/im/channels')
  return res.data ?? []
}

export async function setupChannel(
  channelType: IMChannelType,
  body: SetupChannelRequest,
): Promise<IMChannel> {
  const client = getApiClient()
  const res = await client.post<IMChannel>(`/im/channels/${channelType}/setup`, body)
  return res.data
}

export async function bindAgent(id: string, body: BindAgentRequest): Promise<IMChannel> {
  const client = getApiClient()
  const res = await client.put<IMChannel>(`/im/channels/${encodeURIComponent(id)}/agent`, body)
  return res.data
}

export async function enableChannel(id: string): Promise<IMChannel> {
  const client = getApiClient()
  const res = await client.put<IMChannel>(`/im/channels/${encodeURIComponent(id)}/enable`)
  return res.data
}

export async function disableChannel(id: string): Promise<IMChannel> {
  const client = getApiClient()
  const res = await client.put<IMChannel>(`/im/channels/${encodeURIComponent(id)}/disable`)
  return res.data
}

export async function testConnection(id: string): Promise<TestConnectionResult> {
  const client = getApiClient()
  const res = await client.get<TestConnectionResult>(`/im/channels/${encodeURIComponent(id)}/test`)
  return res.data
}

export const imChannelsApi = {
  listChannels,
  setupChannel,
  bindAgent,
  enableChannel,
  disableChannel,
  testConnection,
}
