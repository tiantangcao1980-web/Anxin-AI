// -*- coding: utf-8 -*-
/**
 * Scheduled Tasks API（V3 移动端镜像）。
 *
 * 走真实后端（D-1，backend/src/api/routes/scheduled_tasks.py）：
 *   - GET  /scheduled-tasks                 列表
 *   - PUT  /scheduled-tasks/{id}/toggle     切换状态，body { status }
 *
 * 返回形状与 mobile/src/lib/api/__mocks__/capabilities.mock.ts 的
 * ScheduledTask 1:1 对齐（后端 ScheduledTaskOut schema 亦同形）。
 * 仅暴露能力中心当前用到的 list / toggle。
 */

import { getApiClient } from './client'

// 与后端 schemas/scheduled_task.py 的 ScheduleStatus 对齐
export type ScheduleStatus = 'active' | 'paused' | 'failed'

// kind / status 在后端 schema 为开放 str，但本页 UI（KIND_LABEL / STATUS_LABEL
// 穷举 Record）依赖 4 类预设契约，故沿用 mock 的字面量联合保持类型穷举与
// 既有 ScheduledTaskRow 兼容。
export type ScheduleKind =
  | 'contract_expiry_alert'
  | 'case_status_daily'
  | 'sentiment_weekly'
  | 'compliance_monthly'

export interface ScheduledTask {
  id: string
  name: string
  kind: ScheduleKind
  cron: string
  cron_human: string
  status: ScheduleStatus
  last_run_at: string | null
  next_run_at: string
  last_run_ok: boolean | null
  agent_persona: string
}

export async function listScheduledTasks(): Promise<ScheduledTask[]> {
  const client = getApiClient()
  const res = await client.get<ScheduledTask[]>('/scheduled-tasks')
  return res.data ?? []
}

export async function toggleScheduledTask(
  id: string,
  status: ScheduleStatus,
): Promise<ScheduledTask> {
  const client = getApiClient()
  const res = await client.put<ScheduledTask>(
    `/scheduled-tasks/${encodeURIComponent(id)}/toggle`,
    { status },
  )
  return res.data
}

export const scheduledTasksApi = {
  list: listScheduledTasks,
  toggle: toggleScheduledTask,
}
