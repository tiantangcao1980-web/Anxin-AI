/**
 * TaskCard — 任务列表中的单条卡片
 */

import { useMemo } from 'react'
import { icons } from '@/lib/icons'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/components/ui/utils'

import type { AgentTask, TaskEvent } from '@/lib/api/agentTasks'

import { TaskStatusBadge } from './TaskStatusBadge'

interface TaskCardProps {
  task: AgentTask
  events?: TaskEvent[]
  selected?: boolean
  onClick?: () => void
}

const PERSONA_AVATAR: Record<string, { emoji: string; label: string; bg: string }> = {
  contract_steward: { emoji: '📑', label: '合同管家', bg: 'bg-blue-100 dark:bg-blue-500/15' },
  anxin_assistant: { emoji: '🤖', label: '安心助手', bg: 'bg-amber-100 dark:bg-amber-500/15' },
  investigator: { emoji: '🔎', label: '调查员', bg: 'bg-purple-100 dark:bg-purple-500/15' },
  litigator: { emoji: '⚖️', label: '诉讼专员', bg: 'bg-emerald-100 dark:bg-emerald-500/15' },
}

function getPersona(key: string) {
  return PERSONA_AVATAR[key] ?? { emoji: '🧠', label: key, bg: 'bg-muted' }
}

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 60_000) return '刚刚'
  const min = Math.floor(ms / 60_000)
  if (min < 60) return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

function deriveTitle(task: AgentTask): string {
  if (typeof task.payload?.title === 'string' && task.payload.title.trim()) {
    return task.payload.title
  }
  const input = task.payload?.user_input
  if (typeof input === 'string' && input.trim()) {
    return input.length > 60 ? `${input.slice(0, 60)}…` : input
  }
  return `任务 ${task.id.slice(0, 8)}`
}

function lastProgressPercent(events?: TaskEvent[]): number | null {
  if (!events || events.length === 0) return null
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const ev = events[i]
    if (ev.event_type === 'progress' && typeof ev.payload?.percent === 'number') {
      return Math.max(0, Math.min(100, ev.payload.percent))
    }
  }
  return null
}

export function TaskCard({ task, events, selected, onClick }: TaskCardProps) {
  const persona = getPersona(task.agent_persona)
  const title = useMemo(() => deriveTitle(task), [task])
  const percent = useMemo(() => lastProgressPercent(events), [events])
  const showProgress =
    task.status === 'running' || task.status === 'reporting' || task.status === 'provisioning'

  return (
    <Card
      onClick={onClick}
      className={cn(
        'group cursor-pointer p-4 transition-all hover:border-primary/50 hover:shadow-sm',
        selected && 'border-primary bg-primary/5 ring-1 ring-primary/30',
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex size-10 shrink-0 items-center justify-center rounded-full text-lg',
            persona.bg,
          )}
          aria-label={persona.label}
        >
          <span>{persona.emoji}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="line-clamp-2 text-sm font-medium leading-snug text-foreground">
              {title}
            </h3>
            <TaskStatusBadge status={task.status} className="shrink-0" />
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <span>{persona.label}</span>
            <span aria-hidden>·</span>
            <span>{relativeTime(task.created_at)}</span>
            {task.priority >= 7 && (
              <>
                <span aria-hidden>·</span>
                <span className="font-medium text-amber-600 dark:text-amber-400">优先级高</span>
              </>
            )}
          </div>
          {showProgress && (
            <div className="mt-3">
              {percent === null ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <icons.Loader2 className="size-3 animate-spin" />
                  <span>正在执行...</span>
                </div>
              ) : (
                <div className="space-y-1">
                  <Progress value={percent} className="h-1.5" />
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>进度</span>
                    <span>{percent}%</span>
                  </div>
                </div>
              )}
            </div>
          )}
          {task.status === 'failed' && task.error?.message && (
            <p className="mt-2 line-clamp-2 text-xs text-red-600 dark:text-red-400">
              {task.error.message}
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}
