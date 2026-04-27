/**
 * TaskStatusBadge — 8 种 status 的语义色彩徽章
 */

import { AlertTriangle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/components/ui/utils'

import type { AgentTaskStatus } from '@/lib/api/agentTasks'

interface TaskStatusBadgeProps {
  status: AgentTaskStatus
  className?: string
}

interface StatusConfig {
  label: string
  className: string
  pulse?: boolean
  icon?: 'warning'
}

const STATUS_MAP: Record<AgentTaskStatus, StatusConfig> = {
  queued: {
    label: '排队中',
    className: 'bg-muted text-muted-foreground border-transparent',
  },
  provisioning: {
    label: '准备中',
    className: 'bg-blue-50 text-blue-700 border-transparent dark:bg-blue-500/10 dark:text-blue-300',
  },
  running: {
    label: '运行中',
    className:
      'bg-blue-100 text-blue-800 border-transparent dark:bg-blue-500/15 dark:text-blue-200',
    pulse: true,
  },
  reporting: {
    label: '总结中',
    className:
      'bg-purple-50 text-purple-700 border-transparent dark:bg-purple-500/10 dark:text-purple-300',
  },
  done: {
    label: '已完成',
    className:
      'bg-emerald-50 text-emerald-700 border-transparent dark:bg-emerald-500/10 dark:text-emerald-300',
  },
  failed: {
    label: '失败',
    className: 'bg-red-50 text-red-700 border-transparent dark:bg-red-500/10 dark:text-red-300',
  },
  needs_approval: {
    label: '待审批',
    className:
      'bg-amber-50 text-amber-800 border-transparent dark:bg-amber-500/10 dark:text-amber-200',
    icon: 'warning',
  },
  cancelled: {
    label: '已取消',
    className: 'bg-muted text-muted-foreground border-transparent line-through',
  },
}

export function TaskStatusBadge({ status, className }: TaskStatusBadgeProps) {
  const cfg = STATUS_MAP[status]
  return (
    <Badge variant="outline" className={cn(cfg.className, className)}>
      {cfg.icon === 'warning' && <AlertTriangle className="size-3" />}
      {cfg.pulse && (
        <span className="relative flex size-1.5 items-center justify-center">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex size-1.5 rounded-full bg-blue-500" />
        </span>
      )}
      <span>{cfg.label}</span>
    </Badge>
  )
}

export const TASK_STATUS_LABEL: Record<AgentTaskStatus, string> = Object.fromEntries(
  Object.entries(STATUS_MAP).map(([k, v]) => [k, v.label]),
) as Record<AgentTaskStatus, string>
