// -*- coding: utf-8 -*-
/**
 * Agent Tasks API（V3 移动端镜像）。
 *
 * 与 frontend/src/lib/api/agentTasks.ts 同形契约：
 *   - GET    /agent-tasks                    列表
 *   - POST   /agent-tasks                    创建
 *   - GET    /agent-tasks/{id}               详情
 *   - POST   /agent-tasks/{id}/cancel        取消
 *   - POST   /agent-tasks/{id}/approve       审批通过
 *   - POST   /agent-tasks/{id}/reject        审批驳回
 *   - GET    /agent-tasks/{id}/result        最终结果
 *   - GET    /agent-tasks/{id}/events        SSE 事件流
 *
 * 移动端 SSE：RN 没有原生 EventSource。我们用「轮询事件指针」作 fallback：
 * P17-A 阶段先实现请求级 API；SSE/轮询订阅在 P17-B/C/D 接入时再决定方案。
 */

import { getApiClient } from './client'

export type AgentTaskStatus =
  | 'queued'
  | 'provisioning'
  | 'running'
  | 'reporting'
  | 'done'
  | 'failed'
  | 'needs_approval'
  | 'cancelled'

export interface AgentTask {
  id: string
  user_id: string
  agent_persona: string
  status: AgentTaskStatus
  priority: number
  payload: Record<string, any>
  result: Record<string, any> | null
  error: { message: string; code?: string } | null
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
  parent_task_id: string | null
  sandbox_id: string | null
}

export type TaskEventType =
  | 'status_changed'
  | 'progress'
  | 'tool_call'
  | 'tool_result'
  | 'error'
  | 'done'

export interface TaskEvent {
  task_id: string
  event_type: TaskEventType
  payload: Record<string, any>
  timestamp: string
  /** Redis Streams entry id；轮询续传游标 */
  stream_id?: string | null
}

export interface ListTasksParams {
  status?: AgentTaskStatus
  limit?: number
  offset?: number
}

export interface CreateTaskRequest {
  agent_persona: string
  payload: Record<string, any>
  priority?: number
}

export interface RejectTaskRequest {
  reason: string
}

export async function listTasks(params: ListTasksParams = {}): Promise<AgentTask[]> {
  const client = getApiClient()
  // 后端 GET /agent-tasks 返回 AgentTaskListOut { items, limit, offset }，不是裸数组。
  const res = await client.get<{ items: AgentTask[]; limit: number; offset: number }>(
    '/agent-tasks',
    { params },
  )
  return res.data?.items ?? []
}

export async function createTask(body: CreateTaskRequest): Promise<AgentTask> {
  const client = getApiClient()
  const res = await client.post<AgentTask>('/agent-tasks', body)
  return res.data
}

export async function getTask(id: string): Promise<AgentTask> {
  const client = getApiClient()
  const res = await client.get<AgentTask>(`/agent-tasks/${encodeURIComponent(id)}`)
  return res.data
}

export async function cancelTask(id: string): Promise<AgentTask> {
  const client = getApiClient()
  const res = await client.post<AgentTask>(`/agent-tasks/${encodeURIComponent(id)}/cancel`)
  return res.data
}

export async function approveTask(id: string): Promise<AgentTask> {
  const client = getApiClient()
  const res = await client.post<AgentTask>(`/agent-tasks/${encodeURIComponent(id)}/approve`)
  return res.data
}

export async function rejectTask(id: string, body: RejectTaskRequest): Promise<AgentTask> {
  const client = getApiClient()
  const res = await client.post<AgentTask>(`/agent-tasks/${encodeURIComponent(id)}/reject`, body)
  return res.data
}

export async function getTaskResult(id: string): Promise<Record<string, any> | null> {
  const client = getApiClient()
  const res = await client.get<Record<string, any> | null>(
    `/agent-tasks/${encodeURIComponent(id)}/result`,
  )
  return res.data ?? null
}

/**
 * 增量拉取任务事件流（轮询替代 SSE）。
 *
 * RN 无原生 EventSource，改打后端轮询端点
 * `GET /agent-tasks/{id}/events/poll?after_ts=<stream_id>`：
 * 后端复用 `replay_events` 做非阻塞增量回放，返回 JSON 数组（TaskEvent[]）。
 * 这里以 2s 轮询模拟订阅：仅把"新增"事件推给 `onEvent`，
 * 用每批最后一条事件的 `stream_id`（Redis Streams entry id）作续传游标。
 * 返回值：取消订阅函数。
 */
export function subscribeTaskEvents(
  id: string,
  onEvent: (event: TaskEvent) => void,
  options: { intervalMs?: number } = {},
): () => void {
  const interval = options.intervalMs ?? 2000
  let stopped = false
  let timer: ReturnType<typeof setTimeout> | null = null
  let afterTs: string | null = null

  const tick = async () => {
    if (stopped) return
    try {
      const client = getApiClient()
      const res = await client.get<TaskEvent[]>(
        `/agent-tasks/${encodeURIComponent(id)}/events/poll`,
        { params: afterTs ? { after_ts: afterTs } : {} },
      )
      const events = res.data ?? []
      for (const ev of events) {
        onEvent(ev)
        if (ev.stream_id) afterTs = ev.stream_id
      }
    } catch {
      // 静默重试
    }
    if (!stopped) {
      timer = setTimeout(tick, interval)
    }
  }

  tick()

  return () => {
    stopped = true
    if (timer) clearTimeout(timer)
  }
}

export const agentTasksApi = {
  listTasks,
  createTask,
  getTask,
  cancelTask,
  approveTask,
  rejectTask,
  getTaskResult,
  subscribeTaskEvents,
}
