// -*- coding: utf-8 -*-
/**
 * Plugins API（小程序 V3 真实客户端，对标 utils/api/skills.ts）。
 *
 * 走真实后端（D-2 插件注册，backend/src/api/routes/plugins.py）：
 *   - GET  /plugins              列表（裸数组 list[PluginOut]）
 *   - PUT  /plugins/{id}/toggle  启停（请求体 {enabled}，PluginOut）
 *
 * ⚠️ 小程序 apiClient.get/put 已 unwrap，返回的是裸 body（非 {data} 包装）。
 *    GET /plugins 后端用 response_model=list[PluginOut] 直接返回裸数组；
 *    此处仍兼容 {items} 包装（与 skills 套路一致，防后端日后改包装）。
 *
 * 契约差异（D-2 PluginOut vs. 页面 mock Plugin）：
 *   - PluginOut 含 source、icon?（可空），不含 skill_count。
 *   - 页面渲染需要 skill_count / icon（必填）。故 normalizePlugin 补默认：
 *     skill_count ?? 0；icon ?? '🧩'（保证 UI 不空）。
 */

import { apiClient } from './client'

/** 插件来源（与后端 PluginSource 对齐）。 */
export type PluginSource = 'official' | 'private' | 'mcp'

/** 插件状态（与后端 PluginStatus + 页面 mock 对齐）。 */
export type PluginStatus = 'enabled' | 'disabled' | 'pending_review'

/** 后端 PluginOut 原始形状（icon 可空、无 skill_count）。 */
interface PluginRaw {
  id: string
  name: string
  display_name: string
  source?: string
  status: PluginStatus
  description: string
  publisher: string
  icon?: string | null
  skill_count?: number | null
}

/** 页面渲染所需的 Plugin 形状（icon / skill_count 必填，由 normalize 补齐）。 */
export interface Plugin {
  id: string
  name: string
  display_name: string
  description: string
  status: PluginStatus
  publisher: string
  skill_count: number
  icon: string
}

interface PluginListOut {
  items?: PluginRaw[]
  total?: number
}

/** 把后端 PluginOut 补齐为页面所需形状（icon / skill_count 兜底）。 */
function normalizePlugin(p: PluginRaw): Plugin {
  return {
    id: p.id,
    name: p.name,
    display_name: p.display_name,
    description: p.description ?? '',
    status: p.status,
    publisher: p.publisher ?? '',
    skill_count: p.skill_count ?? 0,
    icon: p.icon ?? '🧩',
  }
}

export async function listPlugins(): Promise<Plugin[]> {
  // 后端返回裸数组；兼容 {items,total} 包装。
  const res = await apiClient.get<PluginRaw[] | PluginListOut>('/plugins')
  const arr = Array.isArray(res) ? res : (res?.items ?? [])
  return arr.map(normalizePlugin)
}

export async function togglePlugin(id: string, enabled: boolean): Promise<Plugin> {
  const res = await apiClient.put<PluginRaw>(
    `/plugins/${encodeURIComponent(id)}/toggle`,
    { enabled },
  )
  return normalizePlugin(res)
}

export const pluginsApi = {
  list: listPlugins,
  toggle: togglePlugin,
}
