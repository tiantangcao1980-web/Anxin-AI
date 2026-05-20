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
  const res = await client.get<AgentTask[]>('/agent-tasks', { params })
  return res.data ?? []
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
 * 后端 `GET /agent-tasks/{id}/events?after_ts=` 支持按时间戳分页，
 * 这里以 2s 轮询模拟订阅：仅把"新增"事件推给 `onEvent`。
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
        `/agent-tasks/${encodeURIComponent(id)}/events`,
        { params: afterTs ? { after_ts: afterTs } : {} },
      )
      const events = res.data ?? []
      for (const ev of events) {
        onEvent(ev)
        afterTs = ev.timestamp
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

/**
 * 移动端临时事件订阅：固定间隔轮询任务状态。
 * P17-B 接入任务详情时可替换为 RN-EventSource polyfill 或 WebSocket。
 */
export function pollTaskUntilDone(
  id: string,
  onUpdate: (task: AgentTask) => void,
  options: { intervalMs?: number; signal?: AbortSignal } = {},
): () => void {
  const interval = options.intervalMs ?? 3000
  let stopped = false
  let timer: ReturnType<typeof setTimeout> | null = null

  const tick = async () => {
    if (stopped) return
    try {
      const task = await getTask(id)
      onUpdate(task)
      if (['done', 'failed', 'cancelled'].includes(task.status)) {
        stopped = true
        return
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

/**
 * 事件订阅：基于 `pollTaskUntilDone` 合成 TaskEvent 流。
 *
 * 设计取舍：后端 `/agent-tasks/{id}/events` 是 SSE，RN 无原生 EventSource。
 * P17-B 阶段会接入 RN-EventSource polyfill 直读 SSE；当前先通过轮询任务状态
 * 合成 `status_changed` / `done` / `error` 三种事件，保证详情页订阅 API 可用、
 * Store 的 `appendEvent` 去重逻辑（timestamp + event_type）正常工作。
 */
export function subscribeTaskEvents(
  id: string,
  onEvent: (ev: TaskEvent) => void,
  options: { intervalMs?: number } = {},
): () => void {
  let prevStatus: AgentTaskStatus | null = null
  return pollTaskUntilDone(
    id,
    (task) => {
      if (task.status === prevStatus) return
      prevStatus = task.status
      onEvent({
        task_id: task.id,
        event_type: 'status_changed',
        payload: { status: task.status },
        timestamp: task.updated_at,
      })
      if (task.status === 'done') {
        onEvent({
          task_id: task.id,
          event_type: 'done',
          payload: task.result ?? {},
          timestamp: task.finished_at ?? task.updated_at,
        })
      } else if (task.status === 'failed') {
        onEvent({
          task_id: task.id,
          event_type: 'error',
          payload: task.error ?? {},
          timestamp: task.finished_at ?? task.updated_at,
        })
      }
    },
    options,
  )
}

export const agentTasksApi = {
  listTasks,
  createTask,
  getTask,
  cancelTask,
  approveTask,
  rejectTask,
  getTaskResult,
  pollTaskUntilDone,
  subscribeTaskEvents,
}
