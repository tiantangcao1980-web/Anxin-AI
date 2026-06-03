// -*- coding: utf-8 -*-
/**
 * ScheduledTasks API（小程序 V3 真实客户端，对标 utils/api/skills.ts）。
 *
 * 走真实后端（D-1 定时任务管理，backend/src/api/routes/scheduled_tasks.py）：
 *   - GET  /scheduled-tasks              列表（裸数组 list[ScheduledTaskOut]）
 *   - PUT  /scheduled-tasks/{id}/toggle  切状态（请求体 {status}，ScheduledTaskOut）
 *
 * ⚠️ 小程序 apiClient.get/put 已 unwrap，返回的是裸 body（非 {data} 包装）。
 *    GET /scheduled-tasks 后端用 response_model=list[ScheduledTaskOut] 直接返回
 *    裸数组；此处仍兼容 {items} 包装（与 skills 套路一致，防后端日后改包装）。
 *
 * 契约差异（D-1 ScheduledTaskOut vs. 页面 mock ScheduledTask）：
 *   - ScheduledTaskOut 含 next_run_at / last_run_at / last_run_ok，不含
 *     description / icon；kind 为自由字符串（如 case_status_daily）。
 *   - 页面渲染需要 description / icon，并按 4 个 tab（daily/monitor/report/
 *     automation）过滤 kind。故 normalizeTask：icon 按 kind 兜底、description
 *     缺省回退、kind 归一到 4 个 tab（未知归 'automation'）。
 */

import { apiClient } from './client'

/** 调度分组（页面 4 个 tab；后端 kind 为自由字符串，normalize 时归一）。 */
export type ScheduleKind = 'daily' | 'monitor' | 'report' | 'automation'

/** 任务状态（与后端 ScheduleStatus + 页面 mock 对齐）。 */
export type ScheduleStatus = 'active' | 'paused' | 'failed'

/** 后端 ScheduledTaskOut 原始形状（无 description / icon，kind 自由）。 */
interface ScheduledTaskRaw {
  id: string
  name: string
  kind: string
  cron: string
  cron_human: string
  status: ScheduleStatus
  agent_persona: string
  description?: string | null
  icon?: string | null
  last_run_at?: string | null
  next_run_at?: string
  last_run_ok?: boolean | null
}

/** 页面渲染所需的 ScheduledTask 形状（description / icon 必填，由 normalize 补齐）。 */
export interface ScheduledTask {
  id: string
  name: string
  description: string
  kind: ScheduleKind
  cron: string
  cron_human: string
  status: ScheduleStatus
  icon: string
  agent_persona: string
}

interface ScheduledTaskListOut {
  items?: ScheduledTaskRaw[]
  total?: number
}

const KIND_ICON: Record<ScheduleKind, string> = {
  daily: '☀️',
  monitor: '🔭',
  report: '📊',
  automation: '🤖',
}

/** 把后端自由 kind 归一到页面 4 个 tab（未知归 'automation'）。 */
function normalizeKind(kind: string): ScheduleKind {
  if (kind === 'daily' || kind === 'monitor' || kind === 'report' || kind === 'automation') {
    return kind
  }
  // 后端可能返回业务 kind（如 case_status_daily）；按子串粗分组。
  if (kind.includes('daily')) return 'daily'
  if (kind.includes('monitor') || kind.includes('alert') || kind.includes('watch')) return 'monitor'
  if (kind.includes('report') || kind.includes('digest') || kind.includes('summary')) return 'report'
  return 'automation'
}

/** 把后端 ScheduledTaskOut 补齐为页面所需形状（icon / description 兜底）。 */
function normalizeTask(t: ScheduledTaskRaw): ScheduledTask {
  const kind = normalizeKind(t.kind)
  return {
    id: t.id,
    name: t.name,
    description: t.description ?? t.cron_human ?? '',
    kind,
    cron: t.cron,
    cron_human: t.cron_human ?? '',
    status: t.status,
    icon: t.icon ?? KIND_ICON[kind],
    agent_persona: t.agent_persona ?? '',
  }
}

export async function listScheduledTasks(): Promise<ScheduledTask[]> {
  // 后端返回裸数组；兼容 {items,total} 包装。
  const res = await apiClient.get<ScheduledTaskRaw[] | ScheduledTaskListOut>(
    '/scheduled-tasks',
  )
  const arr = Array.isArray(res) ? res : (res?.items ?? [])
  return arr.map(normalizeTask)
}

export async function toggleScheduledTask(
  id: string,
  status: ScheduleStatus,
): Promise<ScheduledTask> {
  const res = await apiClient.put<ScheduledTaskRaw>(
    `/scheduled-tasks/${encodeURIComponent(id)}/toggle`,
    { status },
  )
  return normalizeTask(res)
}

export const scheduledTasksApi = {
  list: listScheduledTasks,
  toggle: toggleScheduledTask,
}
