/**
 * Agent Tasks Mock 适配（移动端 P17-B）
 *
 * 在 EXPO_PUBLIC_AGENT_TASKS_MOCK=true 时启用，供 P17-B 在 P17-A/后端就绪前
 * 完成移动端联调。逻辑与 web 同名 mock 对齐，但用 setTimeout 而不是 EventSource，
 * 因为 React Native 没有 window/EventSource。
 */

import type {
  AgentTask,
  CreateTaskRequest,
  ListTasksParams,
  RejectTaskRequest,
  TaskEvent,
} from '@/lib/types/agentTask'

const now = () => new Date().toISOString()
const minutesAgo = (n: number) => new Date(Date.now() - n * 60_000).toISOString()
const secondsAgo = (n: number) => new Date(Date.now() - n * 1000).toISOString()

let nextId = 6
const createId = () => `mock-task-${nextId++}`

// 5 条假任务覆盖 8 状态：
//   running / needs_approval / done / failed / queued
// （provisioning / reporting / cancelled 通过交互动态生成 —— 创建任务时
//   会经过 queued -> provisioning -> running，取消时进入 cancelled，
//   接近完成时短暂为 reporting）
const seedTasks: AgentTask[] = [
  {
    id: 'mock-task-1',
    user_id: 'mock-user',
    agent_persona: 'contract_steward',
    status: 'running',
    priority: 5,
    payload: {
      title: '审查《深圳-A 公司技术服务合同》',
      user_input: '请帮我审查这份合同的违约责任与知识产权条款是否对我方有利。',
    },
    result: null,
    error: null,
    created_at: minutesAgo(8),
    updated_at: secondsAgo(15),
    started_at: minutesAgo(7),
    finished_at: null,
    parent_task_id: null,
    sandbox_id: 'sbx-001',
  },
  {
    id: 'mock-task-2',
    user_id: 'mock-user',
    agent_persona: 'anxin_assistant',
    status: 'needs_approval',
    priority: 7,
    payload: {
      title: '向 B 公司发出法律意见函',
      user_input: '已起草完成，请审批后由我代为发送邮件至 legal@b.com。',
    },
    result: null,
    error: null,
    created_at: minutesAgo(22),
    updated_at: minutesAgo(2),
    started_at: minutesAgo(20),
    finished_at: null,
    parent_task_id: null,
    sandbox_id: 'sbx-002',
  },
  {
    id: 'mock-task-3',
    user_id: 'mock-user',
    agent_persona: 'investigator',
    status: 'done',
    priority: 3,
    payload: {
      title: '尽调 C 公司股权穿透',
      user_input: '请基于工商数据生成 C 公司至最终受益人三层股权结构图。',
    },
    result: {
      summary: '完成 C 公司股权穿透，共识别 3 层架构 7 个主体，无明显风险。',
      report_url: '/mock/reports/mock-task-3.pdf',
    },
    error: null,
    created_at: minutesAgo(120),
    updated_at: minutesAgo(95),
    started_at: minutesAgo(118),
    finished_at: minutesAgo(95),
    parent_task_id: null,
    sandbox_id: 'sbx-003',
  },
  {
    id: 'mock-task-4',
    user_id: 'mock-user',
    agent_persona: 'contract_steward',
    status: 'failed',
    priority: 5,
    payload: {
      title: '批量比对 30 份 NDA 模板差异',
      user_input: '请对照基准模板找出每份的偏离条款。',
    },
    result: null,
    error: { message: '文件解析失败：第 12 份 NDA 加密无密码', code: 'DOC_PARSE_ERROR' },
    created_at: minutesAgo(180),
    updated_at: minutesAgo(170),
    started_at: minutesAgo(178),
    finished_at: minutesAgo(170),
    parent_task_id: null,
    sandbox_id: 'sbx-004',
  },
  {
    id: 'mock-task-5',
    user_id: 'mock-user',
    agent_persona: 'anxin_assistant',
    status: 'queued',
    priority: 2,
    payload: {
      title: '生成 Q2 法务月报',
      user_input: '从案件中心、合同库、风险预警三个数据源聚合 Q2 月报。',
    },
    result: null,
    error: null,
    created_at: secondsAgo(30),
    updated_at: secondsAgo(30),
    started_at: null,
    finished_at: null,
    parent_task_id: null,
    sandbox_id: null,
  },
]

const tasks: AgentTask[] = [...seedTasks]

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

export async function mockListTasks(params?: ListTasksParams): Promise<AgentTask[]> {
  await new Promise((r) => setTimeout(r, 120))
  let list = clone(tasks)
  if (params?.status) list = list.filter((t) => t.status === params.status)
  const offset = params?.offset ?? 0
  const limit = params?.limit ?? list.length
  return list.slice(offset, offset + limit)
}

export async function mockCreateTask(body: CreateTaskRequest): Promise<AgentTask> {
  await new Promise((r) => setTimeout(r, 200))
  const task: AgentTask = {
    id: createId(),
    user_id: 'mock-user',
    agent_persona: body.agent_persona,
    status: 'queued',
    priority: body.priority ?? 5,
    payload: body.payload,
    result: null,
    error: null,
    created_at: now(),
    updated_at: now(),
    started_at: null,
    finished_at: null,
    parent_task_id: null,
    sandbox_id: null,
  }
  tasks.unshift(task)
  // queued -> provisioning -> running，让 8 状态都出现过
  setTimeout(() => {
    const t = tasks.find((x) => x.id === task.id)
    if (t && t.status === 'queued') {
      t.status = 'provisioning'
      t.updated_at = now()
    }
  }, 800)
  setTimeout(() => {
    const t = tasks.find((x) => x.id === task.id)
    if (t && t.status === 'provisioning') {
      t.status = 'running'
      t.started_at = now()
      t.updated_at = now()
    }
  }, 2000)
  return clone(task)
}

export async function mockGetTask(id: string): Promise<AgentTask> {
  await new Promise((r) => setTimeout(r, 80))
  const t = tasks.find((x) => x.id === id)
  if (!t) throw new Error(`mock task not found: ${id}`)
  return clone(t)
}

export async function mockCancelTask(id: string): Promise<AgentTask> {
  await new Promise((r) => setTimeout(r, 100))
  const t = tasks.find((x) => x.id === id)
  if (!t) throw new Error(`mock task not found: ${id}`)
  t.status = 'cancelled'
  t.updated_at = now()
  t.finished_at = now()
  return clone(t)
}

export async function mockApproveTask(id: string): Promise<AgentTask> {
  await new Promise((r) => setTimeout(r, 100))
  const t = tasks.find((x) => x.id === id)
  if (!t) throw new Error(`mock task not found: ${id}`)
  t.status = 'running'
  t.updated_at = now()
  return clone(t)
}

export async function mockRejectTask(
  id: string,
  body: RejectTaskRequest,
): Promise<AgentTask> {
  await new Promise((r) => setTimeout(r, 100))
  const t = tasks.find((x) => x.id === id)
  if (!t) throw new Error(`mock task not found: ${id}`)
  t.status = 'cancelled'
  t.updated_at = now()
  t.finished_at = now()
  t.error = { message: `审批驳回：${body.reason}`, code: 'REJECTED' }
  return clone(t)
}

export async function mockGetTaskResult(id: string): Promise<Record<string, any> | null> {
  await new Promise((r) => setTimeout(r, 80))
  const t = tasks.find((x) => x.id === id)
  return t?.result ?? null
}

/**
 * Mock 事件流：每 2s 推一条事件，约 6 条后推 done。
 * RN 没有 window，使用全局 setInterval / clearInterval（Node 风格）。
 * 返回 cleanup 函数。
 */
export function mockSubscribeTaskEvents(
  taskId: string,
  onEvent: (event: TaskEvent) => void,
): () => void {
  let stopped = false
  let count = 0
  const phases = [
    { thought: '正在加载上下文...', percent: 12 },
    { thought: '检索相关法条与判例...', percent: 28 },
    { thought: '比对合同条款与基准模板...', percent: 46 },
    { thought: '生成审查意见草稿...', percent: 68 },
    { thought: '校验引用与编号一致性...', percent: 86 },
  ]

  const timer = setInterval(() => {
    if (stopped) return
    const idx = count
    count += 1

    if (idx === 0) {
      onEvent({
        task_id: taskId,
        event_type: 'status_changed',
        payload: { from: 'queued', to: 'running' },
        timestamp: now(),
      })
      return
    }

    if (idx <= phases.length) {
      const p = phases[idx - 1]
      onEvent({
        task_id: taskId,
        event_type: 'progress',
        payload: { thought: p.thought, percent: p.percent },
        timestamp: now(),
      })
      // 偶尔混一条 tool_call + tool_result
      if (idx === 2) {
        setTimeout(() => {
          if (stopped) return
          onEvent({
            task_id: taskId,
            event_type: 'tool_call',
            payload: {
              tool: 'legal.search_statutes',
              arguments: { query: '违约责任 知识产权 服务合同' },
            },
            timestamp: now(),
          })
        }, 400)
        setTimeout(() => {
          if (stopped) return
          onEvent({
            task_id: taskId,
            event_type: 'tool_result',
            payload: {
              tool: 'legal.search_statutes',
              summary: '命中《民法典》第 577 条等 6 条相关法条。',
            },
            timestamp: now(),
          })
        }, 900)
      }
      return
    }

    if (idx === phases.length + 1) {
      onEvent({
        task_id: taskId,
        event_type: 'done',
        payload: { summary: '已完成全部审查，共识别 3 处需关注条款。' },
        timestamp: now(),
      })
      stopped = true
      clearInterval(timer)
    }
  }, 2000)

  return () => {
    stopped = true
    clearInterval(timer)
  }
}
