// -*- coding: utf-8 -*-
/**
 * Plugins API（V3 移动端镜像）。
 *
 * 走真实后端（D-2，backend/src/api/routes/plugins.py）：
 *   - GET  /plugins                    列表（registry + mcp 投影）
 *   - PUT  /plugins/{id}/toggle        启停，body { enabled }
 *
 * 返回形状与 mobile/src/lib/api/__mocks__/capabilities.mock.ts 的
 * Plugin 1:1 对齐（后端 PluginOut schema 亦同形）。
 * 仅暴露能力中心当前用到的 list / toggle。
 */

import { getApiClient } from './client'

// 与后端 schemas/plugin.py 的 PluginSource / PluginStatus 对齐
export type PluginSource = 'official' | 'private' | 'mcp'
export type PluginStatus = 'enabled' | 'disabled' | 'pending_review'

export interface Plugin {
  id: string
  name: string
  display_name: string
  source: PluginSource
  status: PluginStatus
  description: string
  publisher: string
  icon?: string
}

export async function listPlugins(): Promise<Plugin[]> {
  const client = getApiClient()
  const res = await client.get<Plugin[]>('/plugins')
  return res.data ?? []
}

export async function togglePlugin(id: string, enabled: boolean): Promise<Plugin> {
  const client = getApiClient()
  const res = await client.put<Plugin>(
    `/plugins/${encodeURIComponent(id)}/toggle`,
    { enabled },
  )
  return res.data
}

export const pluginsApi = {
  list: listPlugins,
  toggle: togglePlugin,
}
