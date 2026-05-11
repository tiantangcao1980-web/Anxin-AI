// -*- coding: utf-8 -*-
/**
 * Agent Tasks API（与 web/frontend/src/lib/api/agentTasks.ts 契约对齐）
 *
 * 给 P21-B 使用 —— 它在 subpackages/tasks/ 下做列表 / 详情 / 创建。
 *
 * ⚠️ 微信小程序无 EventSource，SSE 订阅在小程序端走 polling 适配
 * （由 P21-B 在订阅 hook 里实现 setInterval(getTask)；后端短连接也可用
 * `/agent-tasks/{id}/events` 改 long polling，由 P21-B 决定）。
 */

import { apiClient } from './client'
import type {
  AgentTask,
  AgentTaskStatus,
  CreateTaskRequest,
  RejectTaskRequest,
} from '../../types/agentTask'

export interface ListTasksParams {
  status?: AgentTaskStatus
  limit?: number
  offset?: number
}

export async function listTasks(params: ListTasksParams = {}): Promise<AgentTask[]> {
  return apiClient.get<AgentTask[]>('/agent-tasks', {
    status: params.status,
    limit: params.limit,
    offset: params.offset,
  })
}

export async function createTask(body: CreateTaskRequest): Promise<AgentTask> {
  return apiClient.post<AgentTask>('/agent-tasks', body)
}

export async function getTask(id: string): Promise<AgentTask> {
  return apiClient.get<AgentTask>(`/agent-tasks/${id}`)
}

export async function cancelTask(id: string): Promise<AgentTask> {
  return apiClient.post<AgentTask>(`/agent-tasks/${id}/cancel`)
}

export async function approveTask(id: string): Promise<AgentTask> {
  return apiClient.post<AgentTask>(`/agent-tasks/${id}/approve`)
}

export async function rejectTask(
  id: string,
  body: RejectTaskRequest,
): Promise<AgentTask> {
  return apiClient.post<AgentTask>(`/agent-tasks/${id}/reject`, body)
}

export async function getTaskResult(
  id: string,
): Promise<Record<string, unknown> | null> {
  return apiClient.get<Record<string, unknown> | null>(`/agent-tasks/${id}/result`)
}

export const agentTasksApi = {
  listTasks,
  createTask,
  getTask,
  cancelTask,
  approveTask,
  rejectTask,
  getTaskResult,
}
