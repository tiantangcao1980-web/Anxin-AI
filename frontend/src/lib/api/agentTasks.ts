/**
 * Agent Tasks API Client (V3 任务中心 P2)
 *
 * 8 endpoint REST 封装 + SSE 事件订阅
 *
 * 通过环境变量 `VITE_AGENT_TASKS_MOCK=true` 可切换到 mock 适配层
 * （便于在后端尚未就绪时跑通前端联调）。
 */

import { getTokenStorage } from '@/lib/platform/storage'

// ===== 类型定义（与后端 contract 对齐） =====

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

// ===== Mock 切换开关 =====

const USE_MOCK = import.meta.env.VITE_AGENT_TASKS_MOCK === 'true'

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

async function realListTasks(params: ListTasksParams = {}): Promise<AgentTask[]> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  if (params.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString()
  const res = await authFetch(`/agent-tasks${query ? `?${query}` : ''}`)
  // 后端 GET /agent-tasks 返回 AgentTaskListOut { items, limit, offset }，不是裸数组。
  const data = await jsonOrThrow<{ items: AgentTask[]; limit: number; offset: number }>(res)
  return data.items ?? []
}

async function realCreateTask(body: CreateTaskRequest): Promise<AgentTask> {
  const res = await authFetch('/agent-tasks', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return jsonOrThrow<AgentTask>(res)
}

async function realGetTask(id: string): Promise<AgentTask> {
  const res = await authFetch(`/agent-tasks/${id}`)
  return jsonOrThrow<AgentTask>(res)
}

async function realCancelTask(id: string): Promise<AgentTask> {
  const res = await authFetch(`/agent-tasks/${id}/cancel`, { method: 'POST' })
  return jsonOrThrow<AgentTask>(res)
}

async function realApproveTask(id: string): Promise<AgentTask> {
  const res = await authFetch(`/agent-tasks/${id}/approve`, { method: 'POST' })
  return jsonOrThrow<AgentTask>(res)
}

async function realRejectTask(id: string, body: RejectTaskRequest): Promise<AgentTask> {
  const res = await authFetch(`/agent-tasks/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return jsonOrThrow<AgentTask>(res)
}

async function realGetTaskResult(id: string): Promise<Record<string, any> | null> {
  const res = await authFetch(`/agent-tasks/${id}/result`)
  return jsonOrThrow<Record<string, any> | null>(res)
}

/**
 * SSE 订阅任务事件流。返回一个 cleanup 函数用于关闭连接。
 *
 * 注意：浏览器原生 EventSource 不支持自定义 header（无法塞 Authorization）。
 * 后端约定：可通过 query string 传 token，或后端使用同源 cookie 鉴权。
 */
function realSubscribeTaskEvents(
  taskId: string,
  onEvent: (event: TaskEvent) => void,
  onError?: (err: Event) => void,
): () => void {
  let closed = false
  let es: EventSource | null = null

  ;(async () => {
    const storage = getTokenStorage()
    const token = await storage.getAccessToken()
    if (closed) return
    const url = new URL(
      `${API_BASE_URL}/agent-tasks/${taskId}/events`,
      window.location.origin,
    )
    if (token) {
      url.searchParams.set('access_token', token)
    }
    es = new EventSource(url.toString())
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as TaskEvent
        onEvent(data)
      } catch (err) {
        // ignore malformed payloads
      }
    }
    if (onError) {
      es.onerror = onError
    }
  })()

  return () => {
    closed = true
    es?.close()
  }
}

// ===== Mock 适配（懒加载，避免 build 把 mock 数据打入正式产物） =====

type MockApi = typeof import('./__mocks__/agentTasks.mock')

let mockPromise: Promise<MockApi> | null = null
async function mock(): Promise<MockApi> {
  if (!mockPromise) {
    mockPromise = import('./__mocks__/agentTasks.mock')
  }
  return mockPromise
}

// ===== 对外导出（根据 USE_MOCK 路由到 mock 或真实实现） =====

export async function listTasks(params?: ListTasksParams): Promise<AgentTask[]> {
  if (USE_MOCK) return (await mock()).mockListTasks(params)
  return realListTasks(params)
}

export async function createTask(body: CreateTaskRequest): Promise<AgentTask> {
  if (USE_MOCK) return (await mock()).mockCreateTask(body)
  return realCreateTask(body)
}

export async function getTask(id: string): Promise<AgentTask> {
  if (USE_MOCK) return (await mock()).mockGetTask(id)
  return realGetTask(id)
}

export async function cancelTask(id: string): Promise<AgentTask> {
  if (USE_MOCK) return (await mock()).mockCancelTask(id)
  return realCancelTask(id)
}

export async function approveTask(id: string): Promise<AgentTask> {
  if (USE_MOCK) return (await mock()).mockApproveTask(id)
  return realApproveTask(id)
}

export async function rejectTask(id: string, body: RejectTaskRequest): Promise<AgentTask> {
  if (USE_MOCK) return (await mock()).mockRejectTask(id, body)
  return realRejectTask(id, body)
}

export async function getTaskResult(id: string): Promise<Record<string, any> | null> {
  if (USE_MOCK) return (await mock()).mockGetTaskResult(id)
  return realGetTaskResult(id)
}

/**
 * 订阅任务事件流。
 *
 * mock 模式：每 2s 推一条 progress 事件，约 6 条后推 done 事件。
 * 返回 cleanup 函数。
 */
export function subscribeTaskEvents(
  taskId: string,
  onEvent: (event: TaskEvent) => void,
  onError?: (err: Event) => void,
): () => void {
  if (USE_MOCK) {
    let cleanupFn: (() => void) | null = null
    let cancelled = false
    mock().then((m) => {
      if (cancelled) return
      cleanupFn = m.mockSubscribeTaskEvents(taskId, onEvent)
    })
    return () => {
      cancelled = true
      cleanupFn?.()
    }
  }
  return realSubscribeTaskEvents(taskId, onEvent, onError)
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
