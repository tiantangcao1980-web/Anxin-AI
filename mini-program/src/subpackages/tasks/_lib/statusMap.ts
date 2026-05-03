// -*- coding: utf-8 -*-
/**
 * 8 个任务状态 → 文本 / 颜色 / 是否进行中
 *
 * 颜色与 web/frontend/src/components/v3/tasks/TaskCard.tsx 对齐：
 *   queued       灰
 *   provisioning 蓝
 *   running      蓝（脉冲）
 *   reporting    紫
 *   done         绿
 *   failed       红
 *   needs_approval 黄
 *   cancelled    灰
 */

import type { AgentTaskStatus } from '../../../types/agentTask'
import { palette } from '../../../utils/theme/colors'

export interface StatusMeta {
  label: string
  bg: string
  fg: string
  border: string
  pulse?: boolean
}

const NEUTRAL_BG = palette.ink100
const NEUTRAL_FG = palette.ink700

export const STATUS_META: Record<AgentTaskStatus, StatusMeta> = {
  queued: { label: '排队中', bg: NEUTRAL_BG, fg: NEUTRAL_FG, border: '#D6D9DD' },
  provisioning: { label: '准备中', bg: '#E0EAFE', fg: '#1D4ED8', border: '#C4D7FB' },
  running: { label: '运行中', bg: '#E0EAFE', fg: '#1D4ED8', border: '#C4D7FB', pulse: true },
  reporting: { label: '汇报中', bg: '#EDE9FE', fg: '#6D28D9', border: '#D8CFFB' },
  done: { label: '已完成', bg: '#DCFCE7', fg: '#15803D', border: '#BBF7D0' },
  failed: { label: '失败', bg: '#FEE2E2', fg: '#B91C1C', border: '#FECACA' },
  needs_approval: { label: '待审批', bg: '#FEF3C7', fg: '#B45309', border: '#FDE68A' },
  cancelled: { label: '已取消', bg: NEUTRAL_BG, fg: NEUTRAL_FG, border: '#D6D9DD' },
}

export const ACTIVE_STATUSES: AgentTaskStatus[] = ['queued', 'provisioning', 'running', 'reporting']
export const APPROVAL_STATUSES: AgentTaskStatus[] = ['needs_approval']
export const FINISHED_STATUSES: AgentTaskStatus[] = ['done', 'failed', 'cancelled']

export type TaskTab = 'active' | 'approval' | 'finished'

export const TAB_BUCKETS: Record<TaskTab, AgentTaskStatus[]> = {
  active: ACTIVE_STATUSES,
  approval: APPROVAL_STATUSES,
  finished: FINISHED_STATUSES,
}

export function bucketOf(status: AgentTaskStatus): TaskTab {
  if (ACTIVE_STATUSES.includes(status)) return 'active'
  if (APPROVAL_STATUSES.includes(status)) return 'approval'
  return 'finished'
}

/** 相对时间（中文，自包含，避免引入 dayjs 增加分包体积） */
export function relativeTime(iso: string): string {
  const ts = new Date(iso).getTime()
  if (!ts || Number.isNaN(ts)) return ''
  const diff = Date.now() - ts
  const sec = Math.round(diff / 1000)
  if (sec < 60) return sec <= 5 ? '刚刚' : `${sec} 秒前`
  const min = Math.round(sec / 60)
  if (min < 60) return `${min} 分钟前`
  const hr = Math.round(min / 60)
  if (hr < 24) return `${hr} 小时前`
  const d = Math.round(hr / 24)
  if (d < 30) return `${d} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

export function taskTitleOf(payload: Record<string, unknown> | undefined, fallbackId?: string): string {
  if (payload && typeof payload.title === 'string' && payload.title.trim()) return payload.title.trim()
  if (payload && typeof payload.user_input === 'string') {
    const s = payload.user_input.trim()
    if (s.length === 0) return fallbackId ?? '未命名任务'
    return s.length > 28 ? `${s.slice(0, 28)}…` : s
  }
  return fallbackId ?? '未命名任务'
}
