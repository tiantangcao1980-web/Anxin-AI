// -*- coding: utf-8 -*-
/**
 * 任务中心 API 适配层 —— 屏蔽 mock / 真后端切换
 *
 * 真接口：mini-program/src/utils/api/agentTasks.ts (P21-A 提供)
 * Mock：subpackages/tasks/_mock
 *
 * 切换：mock 模式由 _mock/index.ts 的 useMockApi() 决定。业务页只需要
 * import { tasksApi } from '../_lib/tasksApi' 即可。
 */

import {
  listTasks as realListTasks,
  createTask as realCreateTask,
  getTask as realGetTask,
  cancelTask as realCancelTask,
  approveTask as realApproveTask,
  rejectTask as realRejectTask,
} from '../../../utils/api/agentTasks'
import type {
  AgentTask,
  AgentTaskStatus,
  CreateTaskRequest,
  RejectTaskRequest,
  TaskEvent,
} from '../../../types/agentTask'
import { mockApi, useMockApi } from '../_mock'

export interface ListTasksParams {
  status?: AgentTaskStatus
  limit?: number
  offset?: number
}

export const tasksApi = {
  async listTasks(params: ListTasksParams = {}): Promise<AgentTask[]> {
    if (useMockApi()) return mockApi.listTasks(params)
    return realListTasks(params)
  },

  async getTask(id: string): Promise<AgentTask> {
    if (useMockApi()) return mockApi.getTask(id)
    return realGetTask(id)
  },

  async createTask(body: CreateTaskRequest): Promise<AgentTask> {
    if (useMockApi()) return mockApi.createTask(body)
    return realCreateTask(body)
  },

  async cancelTask(id: string): Promise<AgentTask> {
    if (useMockApi()) return mockApi.cancelTask(id)
    return realCancelTask(id)
  },

  async approveTask(id: string): Promise<AgentTask> {
    if (useMockApi()) return mockApi.approveTask(id)
    return realApproveTask(id)
  },

  async rejectTask(id: string, body: RejectTaskRequest): Promise<AgentTask> {
    if (useMockApi()) return mockApi.rejectTask(id, body)
    return realRejectTask(id, body)
  },

  /**
   * 拉取 events
   *
   * 小程序无 EventSource，用轮询适配：
   *   - mock 时直接读 _mock 的 eventsDb（含 polling tick 增量）
   *   - 真接口时调 GET /agent-tasks/{id}/events?since=<ts>，由后端返回 events 数组
   */
  async getEvents(id: string, sinceISO?: string): Promise<TaskEvent[]> {
    if (useMockApi()) {
      // 模拟 polling tick：每次 getEvents 让 mock 自动追加一个 progress
      mockApi.pollEventTick(id)
      const all = await mockApi.getEvents(id)
      if (!sinceISO) return all
      return all.filter((e) => e.timestamp > sinceISO)
    }
    // 真接口：暂走 GET /events，可由后端实现 since 过滤
    // P21-A 的 agentTasks API 没暴露 events 接口，这里直接走 fetch fallback
    try {
      const { apiClient } = await import('../../../utils/api/client')
      const events = await apiClient.get<TaskEvent[]>(
        `/agent-tasks/${id}/events`,
        sinceISO ? { since: sinceISO } : undefined,
      )
      return Array.isArray(events) ? events : []
    } catch {
      return []
    }
  },
}
