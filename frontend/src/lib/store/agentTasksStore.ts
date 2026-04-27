/**
 * Agent Tasks zustand store (V3 任务中心 P2)
 *
 * 集中管理任务列表 / 选中状态 / 事件流缓存。
 */

import { create } from 'zustand'

import {
  agentTasksApi,
  type AgentTask,
  type CreateTaskRequest,
  type TaskEvent,
} from '@/lib/api/agentTasks'

interface AgentTasksState {
  tasks: AgentTask[]
  loading: boolean
  loadError: string | null

  selectedTaskId: string | null
  events: Record<string, TaskEvent[]>

  // actions
  loadTasks: () => Promise<void>
  createTask: (body: CreateTaskRequest) => Promise<AgentTask>
  cancelTask: (id: string) => Promise<void>
  approveTask: (id: string) => Promise<void>
  rejectTask: (id: string, reason: string) => Promise<void>
  selectTask: (id: string | null) => void
  appendEvent: (taskId: string, event: TaskEvent) => void
  clearEvents: (taskId: string) => void
  upsertTask: (task: AgentTask) => void
}

export const useAgentTasksStore = create<AgentTasksState>((set, get) => ({
  tasks: [],
  loading: false,
  loadError: null,
  selectedTaskId: null,
  events: {},

  loadTasks: async () => {
    set({ loading: true, loadError: null })
    try {
      const tasks = await agentTasksApi.listTasks({ limit: 100 })
      set({ tasks, loading: false })
    } catch (e) {
      set({
        loading: false,
        loadError: e instanceof Error ? e.message : '加载失败',
      })
    }
  },

  createTask: async (body) => {
    const task = await agentTasksApi.createTask(body)
    set((s) => ({ tasks: [task, ...s.tasks] }))
    return task
  },

  cancelTask: async (id) => {
    const updated = await agentTasksApi.cancelTask(id)
    get().upsertTask(updated)
  },

  approveTask: async (id) => {
    const updated = await agentTasksApi.approveTask(id)
    get().upsertTask(updated)
  },

  rejectTask: async (id, reason) => {
    const updated = await agentTasksApi.rejectTask(id, { reason })
    get().upsertTask(updated)
  },

  selectTask: (id) => set({ selectedTaskId: id }),

  appendEvent: (taskId, event) =>
    set((s) => {
      const prev = s.events[taskId] ?? []
      // 去重保护：相同 timestamp+event_type 视为同一条
      const dup = prev.some(
        (e) => e.timestamp === event.timestamp && e.event_type === event.event_type,
      )
      if (dup) return s
      return { events: { ...s.events, [taskId]: [...prev, event] } }
    }),

  clearEvents: (taskId) =>
    set((s) => {
      const next = { ...s.events }
      delete next[taskId]
      return { events: next }
    }),

  upsertTask: (task) =>
    set((s) => {
      const idx = s.tasks.findIndex((t) => t.id === task.id)
      if (idx === -1) return { tasks: [task, ...s.tasks] }
      const next = s.tasks.slice()
      next[idx] = task
      return { tasks: next }
    }),
}))
