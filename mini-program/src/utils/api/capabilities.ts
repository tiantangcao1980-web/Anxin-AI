// -*- coding: utf-8 -*-
/**
 * Capabilities API（V3 能力中心 — 给 P21-D 使用）
 *
 * 涵盖 7 个 capability 资源 endpoint，每个都遵循 REST 规范：
 *   - scheduled-tasks
 *   - app-authorizations
 *   - skills
 *   - plugins
 *   - message-channels (im-channels)
 *   - pairing-authorizations (im-pairing)
 *
 * 这里只提供通用的 CRUD 工厂；P21-D 可以直接用 capabilitiesApi.scheduledTasks.list()。
 */

import { apiClient } from './client'

interface ResourceListResult<T> {
  items: T[]
  total?: number
}

interface ListParams {
  status?: string
  limit?: number
  offset?: number
  [k: string]: string | number | boolean | undefined
}

function makeResource<T extends { id: string }>(path: string) {
  return {
    list: (params?: ListParams) =>
      apiClient.get<ResourceListResult<T> | T[]>(path, params).then((r) =>
        Array.isArray(r) ? r : r.items,
      ),
    get: (id: string) => apiClient.get<T>(`${path}/${encodeURIComponent(id)}`),
    create: (body: Partial<T>) => apiClient.post<T>(path, body),
    update: (id: string, body: Partial<T>) =>
      apiClient.put<T>(`${path}/${encodeURIComponent(id)}`, body),
    delete: (id: string) =>
      apiClient.delete<{ ok: boolean }>(`${path}/${encodeURIComponent(id)}`),
  }
}

export interface ScheduledTask {
  id: string
  name: string
  cron: string
  enabled: boolean
  next_run_at?: string
  payload?: Record<string, unknown>
  [k: string]: unknown
}
export interface AppAuthorization {
  id: string
  app_name: string
  status: string
  scopes?: string[]
  [k: string]: unknown
}
export interface Skill {
  id: string
  name: string
  description?: string
  enabled?: boolean
  [k: string]: unknown
}
export interface Plugin {
  id: string
  name: string
  version?: string
  enabled?: boolean
  [k: string]: unknown
}
export interface MessageChannel {
  id: string
  channel_type: string // wechat / dingtalk / feishu / wecom / sms / email
  status: string
  config?: Record<string, unknown>
  [k: string]: unknown
}
export interface PairingAuthorization {
  id: string
  pairing_code: string
  expires_at?: string
  status: string
  [k: string]: unknown
}

export const capabilitiesApi = {
  scheduledTasks: makeResource<ScheduledTask>('/scheduled-tasks'),
  appAuthorizations: makeResource<AppAuthorization>('/app-authorizations'),
  skills: makeResource<Skill>('/skills'),
  plugins: makeResource<Plugin>('/plugins'),
  messageChannels: makeResource<MessageChannel>('/im-channels'),
  pairingAuthorizations: makeResource<PairingAuthorization>('/im-pairing'),
}
