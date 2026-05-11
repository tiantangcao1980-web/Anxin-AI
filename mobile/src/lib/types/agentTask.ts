/**
 * Agent Task 类型定义（V3 任务中心 P17-B 移动端）
 *
 * ⚠️ STUB（待 P17-A 收敛）：当前文件由 P17-B 临时创建以让 tsc 通过。
 * P17-A 完成后应当将此文件替换为与 web 端 (`frontend/src/lib/api/agentTasks.ts`)
 * 完全一致的类型定义，并由 P17-A 统一维护。
 *
 * 与后端契约对齐：
 *   GET    /api/v1/agent-tasks
 *   POST   /api/v1/agent-tasks
 *   GET    /api/v1/agent-tasks/:id
 *   POST   /api/v1/agent-tasks/:id/cancel
 *   POST   /api/v1/agent-tasks/:id/approve
 *   POST   /api/v1/agent-tasks/:id/reject
 *   GET    /api/v1/agent-tasks/:id/result
 *   GET    /api/v1/agent-tasks/:id/events  (SSE，移动端暂不接，改 5s 轮询)
 */

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
