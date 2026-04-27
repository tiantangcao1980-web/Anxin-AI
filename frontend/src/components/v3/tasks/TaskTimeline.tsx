/**
 * TaskTimeline — 任务详情时间线
 *
 * 顶部展示用户原指令 (task.payload),底部展示 task.result(若存在)。
 * 中间按时间倒序展示事件流。
 */

import { useMemo, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDot,
  PlayCircle,
  Wrench,
} from 'lucide-react'

import { cn } from '@/components/ui/utils'

import type { AgentTask, TaskEvent, TaskEventType } from '@/lib/api/agentTasks'

interface TaskTimelineProps {
  task: AgentTask
  events: TaskEvent[]
}

interface EventStyle {
  icon: typeof CircleDot
  iconClass: string
  cardClass: string
  title: string
}

const EVENT_STYLE: Record<TaskEventType, EventStyle> = {
  status_changed: {
    icon: PlayCircle,
    iconClass: 'text-slate-500',
    cardClass: 'border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/40',
    title: '状态变更',
  },
  progress: {
    icon: CircleDot,
    iconClass: 'text-slate-400',
    cardClass: 'border-slate-200 bg-muted/40 dark:border-slate-800',
    title: '进度更新',
  },
  tool_call: {
    icon: Wrench,
    iconClass: 'text-blue-500',
    cardClass: 'border-blue-200 bg-blue-50 dark:border-blue-900/60 dark:bg-blue-500/10',
    title: '工具调用',
  },
  tool_result: {
    icon: Wrench,
    iconClass: 'text-emerald-500',
    cardClass:
      'border-emerald-200 bg-emerald-50 dark:border-emerald-900/60 dark:bg-emerald-500/10',
    title: '工具返回',
  },
  error: {
    icon: AlertCircle,
    iconClass: 'text-red-500',
    cardClass: 'border-red-200 bg-red-50 dark:border-red-900/60 dark:bg-red-500/10',
    title: '错误',
  },
  done: {
    icon: CheckCircle2,
    iconClass: 'text-emerald-600',
    cardClass:
      'border-emerald-300 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-500/15',
    title: '任务完成',
  },
}

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}

function CollapsibleJson({ data, label }: { data: unknown; label: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground"
      >
        {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
        <span>{label}</span>
      </button>
      {open && (
        <pre className="mt-1 max-h-48 overflow-auto rounded-md border border-border/50 bg-background/60 p-2 text-[11px] leading-relaxed text-foreground">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}

function EventCard({ event }: { event: TaskEvent }) {
  const style = EVENT_STYLE[event.event_type]
  const Icon = style.icon

  let body: React.ReactNode = null
  switch (event.event_type) {
    case 'status_changed':
      body = (
        <p className="text-sm text-foreground">
          {event.payload.from ?? '?'} → <strong>{event.payload.to ?? '?'}</strong>
        </p>
      )
      break
    case 'progress':
      body = (
        <div className="space-y-1">
          {event.payload.thought && (
            <p className="text-sm leading-relaxed text-foreground">{event.payload.thought}</p>
          )}
          {typeof event.payload.percent === 'number' && (
            <p className="text-xs text-muted-foreground">进度 {event.payload.percent}%</p>
          )}
        </div>
      )
      break
    case 'tool_call':
      body = (
        <div>
          <p className="text-sm font-medium text-foreground">
            {event.payload.tool ?? '未知工具'}
          </p>
          {event.payload.arguments !== undefined && (
            <CollapsibleJson data={event.payload.arguments} label="参数" />
          )}
        </div>
      )
      break
    case 'tool_result':
      body = (
        <div>
          <p className="text-sm text-foreground">
            {event.payload.tool ?? '工具'} ·{' '}
            <span className="text-muted-foreground">
              {event.payload.summary ?? '已返回结果'}
            </span>
          </p>
          {event.payload.result !== undefined && (
            <CollapsibleJson data={event.payload.result} label="完整返回" />
          )}
        </div>
      )
      break
    case 'error':
      body = (
        <div>
          <p className="text-sm text-red-700 dark:text-red-300">
            {event.payload.message ?? '执行出错'}
          </p>
          {event.payload.traceback && (
            <CollapsibleJson data={event.payload.traceback} label="Traceback" />
          )}
        </div>
      )
      break
    case 'done':
      body = (
        <p className="text-sm text-emerald-800 dark:text-emerald-200">
          {event.payload.summary ?? '任务已完成'}
        </p>
      )
      break
    default:
      body = <CollapsibleJson data={event.payload} label="payload" />
  }

  return (
    <div className={cn('rounded-lg border p-3', style.cardClass)}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className={cn('size-4', style.iconClass)} />
          <span className="text-xs font-medium text-foreground">{style.title}</span>
        </div>
        <span className="text-[11px] text-muted-foreground">{fmtTime(event.timestamp)}</span>
      </div>
      <div>{body}</div>
    </div>
  )
}

export function TaskTimeline({ task, events }: TaskTimelineProps) {
  // 按时间倒序
  const sorted = useMemo(
    () => [...events].sort((a, b) => (b.timestamp > a.timestamp ? 1 : -1)),
    [events],
  )

  const userInput =
    typeof task.payload?.user_input === 'string' ? task.payload.user_input : null

  return (
    <div className="flex h-full flex-col gap-4">
      {/* 顶部：用户原指令 */}
      <section className="rounded-lg border border-border/60 bg-muted/40 p-3">
        <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          用户指令
        </div>
        {userInput ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{userInput}</p>
        ) : (
          <pre className="overflow-auto text-xs text-foreground">
            {JSON.stringify(task.payload, null, 2)}
          </pre>
        )}
      </section>

      {/* 中部：事件流 */}
      <section className="flex-1 space-y-2 overflow-auto pr-1">
        <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          执行时间线
        </div>
        {sorted.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            暂无事件,等待执行...
          </div>
        ) : (
          sorted.map((ev, idx) => <EventCard key={`${ev.timestamp}-${idx}`} event={ev} />)
        )}
      </section>

      {/* 底部：result */}
      {task.result && (
        <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-900/60 dark:bg-emerald-500/10">
          <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
            最终结果
          </div>
          {typeof task.result.summary === 'string' && (
            <p className="text-sm leading-relaxed text-foreground">{task.result.summary}</p>
          )}
          <CollapsibleJson data={task.result} label="完整 result" />
        </section>
      )}
    </div>
  )
}
