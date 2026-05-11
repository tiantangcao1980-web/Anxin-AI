// -*- coding: utf-8 -*-
/**
 * Agent Task 类型（与 frontend/src/lib/api/agentTasks.ts 对齐）
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
  payload: Record<string, unknown>
  result: Record<string, unknown> | null
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
  payload: Record<string, unknown>
  timestamp: string
}

export interface CreateTaskRequest {
  agent_persona: string
  payload: Record<string, unknown>
  priority?: number
}

export interface RejectTaskRequest {
  reason: string
}
