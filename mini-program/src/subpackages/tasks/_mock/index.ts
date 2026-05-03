// -*- coding: utf-8 -*-
/**
 * P21-B Mock 数据 —— 8 个任务覆盖 8 状态 + event polling
 *
 * 由 subpackages/tasks/* 在 BASE_URL 未配置或显式开启 mock 时使用：
 *   - 不依赖后端
 *   - 模拟 list/get/cancel/approve/reject + event 增量轮询
 *
 * 真接口接入：把 useMockApi() 从 'true' 改为 false 即可，业务页代码不动。
 */

import type {
  AgentTask,
  AgentTaskStatus,
  CreateTaskRequest,
  RejectTaskRequest,
  TaskEvent,
  TaskEventType,
} from '../../../types/agentTask'

/** mock 总开关：env 没配 BASE_URL 就走 mock */
export function useMockApi(): boolean {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const envBase = (process as unknown as { env?: Record<string, string> }).env?.TARO_APP_API_BASE_URL
  if (!envBase || envBase === '' || envBase.includes('mock')) return true
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return Boolean((process as unknown as { env?: Record<string, string> }).env?.TARO_APP_AGENT_TASKS_MOCK)
}

const NOW = Date.now()
const MIN = 60_000
const HOUR = 60 * MIN

function iso(offsetMs: number): string {
  return new Date(NOW + offsetMs).toISOString()
}

function makeEvent(
  taskId: string,
  type: TaskEventType,
  payload: Record<string, unknown>,
  offsetMs: number,
): TaskEvent {
  return {
    task_id: taskId,
    event_type: type,
    payload,
    timestamp: iso(offsetMs),
  }
}

/** 8 个任务覆盖 8 状态 */
const seedTasks: AgentTask[] = [
  {
    id: 'task-001-queued',
    user_id: 'u-mock',
    agent_persona: 'anxin_assistant',
    status: 'queued',
    priority: 5,
    payload: { title: '整理本周客户跟进清单', user_input: '把本周新加的客户线索按优先级整理一下' },
    result: null,
    error: null,
    created_at: iso(-30 * MIN),
    updated_at: iso(-30 * MIN),
    started_at: null,
    finished_at: null,
    parent_task_id: null,
    sandbox_id: null,
  },
  {
    id: 'task-002-provisioning',
    user_id: 'u-mock',
    agent_persona: 'due_diligence_expert',
    status: 'provisioning',
    priority: 7,
    payload: { title: '尽调 ABC 科技', user_input: '查 ABC 科技有限公司的工商 + 司法风险' },
    result: null,
    error: null,
    created_at: iso(-25 * MIN),
    updated_at: iso(-2 * MIN),
    started_at: iso(-2 * MIN),
    finished_at: null,
    parent_task_id: null,
    sandbox_id: 'sbx-002',
  },
  {
    id: 'task-003-running',
    user_id: 'u-mock',
    agent_persona: 'market_researcher',
    status: 'running',
    priority: 6,
    payload: { title: '调研储能行业 Q1 玩家', user_input: '梳理国内储能赛道 Q1 融资事件 + 头部玩家' },
    result: null,
    error: null,
    created_at: iso(-1 * HOUR),
    updated_at: iso(-1 * MIN),
    started_at: iso(-50 * MIN),
    finished_at: null,
    parent_task_id: null,
    sandbox_id: 'sbx-003',
  },
  {
    id: 'task-004-reporting',
    user_id: 'u-mock',
    agent_persona: 'content_director',
    status: 'reporting',
    priority: 5,
    payload: { title: '改写公众号《制造业 AI 落地》', user_input: '把那篇 5000 字稿改写成 3 个平台版' },
    result: null,
    error: null,
    created_at: iso(-2 * HOUR),
    updated_at: iso(-30 * 1000),
    started_at: iso(-1.8 * HOUR),
    finished_at: null,
    parent_task_id: null,
    sandbox_id: 'sbx-004',
  },
  {
    id: 'task-005-done',
    user_id: 'u-mock',
    agent_persona: 'contract_steward',
    status: 'done',
    priority: 8,
    payload: { title: '审查 NDA - 美方供应商', user_input: '看看这份 NDA 有没有不利条款' },
    result: { summary: '识别 3 处风险条款，详见时间线', risk_count: 3 },
    error: null,
    created_at: iso(-3 * HOUR),
    updated_at: iso(-1 * HOUR),
    started_at: iso(-2.9 * HOUR),
    finished_at: iso(-1 * HOUR),
    parent_task_id: null,
    sandbox_id: 'sbx-005',
  },
  {
    id: 'task-006-failed',
    user_id: 'u-mock',
    agent_persona: 'lead_hunter',
    status: 'failed',
    priority: 4,
    payload: { title: '抓取潜在客户名单', user_input: '抓 5 家光伏相关企业联系人' },
    result: null,
    error: { message: '目标站点反爬封锁，重试 3 次失败', code: 'CRAWL_BLOCKED' },
    created_at: iso(-4 * HOUR),
    updated_at: iso(-2 * HOUR),
    started_at: iso(-3.9 * HOUR),
    finished_at: iso(-2 * HOUR),
    parent_task_id: null,
    sandbox_id: 'sbx-006',
  },
  {
    id: 'task-007-needs-approval',
    user_id: 'u-mock',
    agent_persona: 'tax_finance_advisor',
    status: 'needs_approval',
    priority: 7,
    payload: {
      title: '提交本月增值税申报',
      user_input: '本月销项 88 万、进项 65 万，已生成申报草稿，待你确认',
      approval_summary: '准备代为提交税务申报，请审批',
    },
    result: null,
    error: null,
    created_at: iso(-5 * HOUR),
    updated_at: iso(-30 * MIN),
    started_at: iso(-4.9 * HOUR),
    finished_at: null,
    parent_task_id: null,
    sandbox_id: 'sbx-007',
  },
  {
    id: 'task-008-cancelled',
    user_id: 'u-mock',
    agent_persona: 'operations_manager',
    status: 'cancelled',
    priority: 3,
    payload: { title: '生成本月 OKR 进度', user_input: '从飞书项目里拉 OKR 数据生成日报' },
    result: null,
    error: null,
    created_at: iso(-1 * 24 * HOUR),
    updated_at: iso(-23 * HOUR),
    started_at: null,
    finished_at: iso(-23 * HOUR),
    parent_task_id: null,
    sandbox_id: null,
  },
]

const seedEventsMap: Record<string, TaskEvent[]> = {
  'task-001-queued': [
    makeEvent('task-001-queued', 'status_changed', { from: null, to: 'queued', reason: '已加入队列' }, -30 * MIN),
    makeEvent('task-001-queued', 'progress', { thought: '排队中，等待沙箱配额释放' }, -28 * MIN),
  ],
  'task-002-provisioning': [
    makeEvent('task-002-provisioning', 'status_changed', { from: 'queued', to: 'provisioning' }, -2 * MIN),
    makeEvent('task-002-provisioning', 'progress', { thought: '正在拉起隔离沙箱…' }, -90 * 1000),
    makeEvent('task-002-provisioning', 'progress', { thought: '加载尽调 skills + 工商接口凭证' }, -60 * 1000),
  ],
  'task-003-running': [
    makeEvent('task-003-running', 'status_changed', { from: 'provisioning', to: 'running' }, -50 * MIN),
    makeEvent('task-003-running', 'progress', { thought: '检索行业研报数据库' }, -45 * MIN),
    makeEvent(
      'task-003-running',
      'tool_call',
      { tool: 'industry_search', arguments: { keyword: '储能 Q1 融资', limit: 30 } },
      -40 * MIN,
    ),
    makeEvent(
      'task-003-running',
      'tool_result',
      { tool: 'industry_search', summary: '获取 27 条融资事件，覆盖 19 家企业' },
      -38 * MIN,
    ),
    makeEvent(
      'task-003-running',
      'tool_call',
      { tool: 'company_profile', arguments: { name: '宁德时代', dimensions: ['财务', '技术', '渠道'] } },
      -30 * MIN,
    ),
    makeEvent(
      'task-003-running',
      'tool_result',
      { tool: 'company_profile', summary: '画像生成完成，附 Top 3 优势 + Top 3 短板' },
      -25 * MIN,
    ),
    makeEvent('task-003-running', 'progress', { thought: '合成 Top 5 玩家对比矩阵中…' }, -1 * MIN),
  ],
  'task-004-reporting': [
    makeEvent('task-004-reporting', 'status_changed', { from: 'running', to: 'reporting' }, -2 * MIN),
    makeEvent('task-004-reporting', 'progress', { thought: '生成公众号 / 知乎 / 小红书三个版本' }, -90 * 1000),
    makeEvent(
      'task-004-reporting',
      'tool_call',
      { tool: 'multiplatform_rewrite', arguments: { source: '原文链接', platforms: ['wechat', 'zhihu', 'redbook'] } },
      -60 * 1000,
    ),
    makeEvent('task-004-reporting', 'progress', { thought: '正在校对最后一稿' }, -30 * 1000),
  ],
  'task-005-done': [
    makeEvent('task-005-done', 'status_changed', { from: 'queued', to: 'running' }, -2.9 * HOUR),
    makeEvent('task-005-done', 'tool_call', { tool: 'contract_review', arguments: { doc: 'NDA-v3.docx' } }, -2.5 * HOUR),
    makeEvent('task-005-done', 'tool_result', { tool: 'contract_review', summary: '识别 3 处风险条款' }, -2 * HOUR),
    makeEvent(
      'task-005-done',
      'progress',
      { thought: '关键风险：单方解除权 / 竞业期 24 个月 / 仲裁地 NY' },
      -1.5 * HOUR,
    ),
    makeEvent('task-005-done', 'status_changed', { from: 'running', to: 'reporting' }, -1.2 * HOUR),
    makeEvent('task-005-done', 'done', { summary: '审查完成，建议修订 3 条', file: 'NDA-marked.docx' }, -1 * HOUR),
  ],
  'task-006-failed': [
    makeEvent('task-006-failed', 'status_changed', { from: 'queued', to: 'running' }, -3.9 * HOUR),
    makeEvent('task-006-failed', 'tool_call', { tool: 'web_crawl', arguments: { keyword: '光伏厂商' } }, -3 * HOUR),
    makeEvent('task-006-failed', 'tool_result', { tool: 'web_crawl', summary: '触发 Cloudflare 反爬' }, -2.5 * HOUR),
    makeEvent('task-006-failed', 'progress', { thought: '切换 IP 池重试' }, -2.4 * HOUR),
    makeEvent(
      'task-006-failed',
      'error',
      { message: '目标站点反爬封锁，重试 3 次失败', traceback: 'CrawlError: Blocked by Cloudflare\n  at crawler.fetch (crawler.ts:88)' },
      -2 * HOUR,
    ),
  ],
  'task-007-needs-approval': [
    makeEvent('task-007-needs-approval', 'status_changed', { from: 'queued', to: 'running' }, -4.9 * HOUR),
    makeEvent('task-007-needs-approval', 'tool_call', { tool: 'tax_calc', arguments: { period: '2026-04' } }, -4 * HOUR),
    makeEvent(
      'task-007-needs-approval',
      'tool_result',
      { tool: 'tax_calc', summary: '应纳税额 ¥299,000，已生成申报草稿' },
      -3 * HOUR,
    ),
    makeEvent(
      'task-007-needs-approval',
      'progress',
      { thought: '准备提交至税务系统，需要你确认申报金额' },
      -1 * HOUR,
    ),
    makeEvent('task-007-needs-approval', 'status_changed', { from: 'running', to: 'needs_approval' }, -30 * MIN),
  ],
  'task-008-cancelled': [
    makeEvent('task-008-cancelled', 'status_changed', { from: null, to: 'queued' }, -24 * HOUR),
    makeEvent('task-008-cancelled', 'status_changed', { from: 'queued', to: 'cancelled', reason: '用户手动取消' }, -23 * HOUR),
  ],
}

// 内部状态：列表 + events，可在生命周期内增量
const tasksDb: AgentTask[] = seedTasks.map((t) => ({ ...t }))
const eventsDb: Record<string, TaskEvent[]> = Object.fromEntries(
  Object.entries(seedEventsMap).map(([k, v]) => [k, v.map((e) => ({ ...e }))]),
)

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

export const mockApi = {
  async listTasks(params: { status?: AgentTaskStatus } = {}): Promise<AgentTask[]> {
    await delay(120)
    const list = tasksDb.filter((t) => !params.status || t.status === params.status)
    // 按 created_at 倒序
    return clone(list).sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
  },

  async getTask(id: string): Promise<AgentTask> {
    await delay(80)
    const task = tasksDb.find((t) => t.id === id)
    if (!task) throw new Error(`未找到任务：${id}`)
    return clone(task)
  },

  async getEvents(id: string): Promise<TaskEvent[]> {
    await delay(60)
    return clone(eventsDb[id] ?? [])
  },

  async createTask(body: CreateTaskRequest): Promise<AgentTask> {
    await delay(150)
    const id = `task-${Date.now()}-new`
    const task: AgentTask = {
      id,
      user_id: 'u-mock',
      agent_persona: body.agent_persona,
      status: 'queued',
      priority: body.priority ?? 5,
      payload: body.payload || {},
      result: null,
      error: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      started_at: null,
      finished_at: null,
      parent_task_id: null,
      sandbox_id: null,
    }
    tasksDb.unshift(task)
    eventsDb[id] = [
      makeEvent(id, 'status_changed', { from: null, to: 'queued', reason: '任务已创建' }, 0),
    ]
    return clone(task)
  },

  async cancelTask(id: string): Promise<AgentTask> {
    await delay(100)
    const task = tasksDb.find((t) => t.id === id)
    if (!task) throw new Error('任务不存在')
    task.status = 'cancelled'
    task.updated_at = new Date().toISOString()
    task.finished_at = new Date().toISOString()
    eventsDb[id] = (eventsDb[id] || []).concat(
      makeEvent(id, 'status_changed', { from: 'running', to: 'cancelled', reason: '用户取消' }, 0),
    )
    return clone(task)
  },

  async approveTask(id: string): Promise<AgentTask> {
    await delay(120)
    const task = tasksDb.find((t) => t.id === id)
    if (!task) throw new Error('任务不存在')
    task.status = 'running'
    task.updated_at = new Date().toISOString()
    eventsDb[id] = (eventsDb[id] || []).concat(
      makeEvent(id, 'status_changed', { from: 'needs_approval', to: 'running', reason: '已批准' }, 0),
      makeEvent(id, 'progress', { thought: '已收到批准，继续执行后续步骤' }, 100),
    )
    return clone(task)
  },

  async rejectTask(id: string, body: RejectTaskRequest): Promise<AgentTask> {
    await delay(120)
    const task = tasksDb.find((t) => t.id === id)
    if (!task) throw new Error('任务不存在')
    task.status = 'cancelled'
    task.updated_at = new Date().toISOString()
    task.finished_at = new Date().toISOString()
    eventsDb[id] = (eventsDb[id] || []).concat(
      makeEvent(id, 'status_changed', {
        from: 'needs_approval',
        to: 'cancelled',
        reason: `审批驳回：${body.reason}`,
      }, 0),
    )
    return clone(task)
  },

  /** 模拟 polling 增量：每次调用给 running/reporting 任务追加一个 progress event */
  pollEventTick(id: string): TaskEvent | null {
    const task = tasksDb.find((t) => t.id === id)
    if (!task) return null
    if (!['running', 'reporting', 'provisioning'].includes(task.status)) return null
    const tick = (eventsDb[id]?.length ?? 0) + 1
    const ev = makeEvent(id, 'progress', { thought: `轮询 tick #${tick}：仍在处理中…` }, 0)
    eventsDb[id] = (eventsDb[id] || []).concat(ev)
    task.updated_at = new Date().toISOString()
    return clone(ev)
  },
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}
