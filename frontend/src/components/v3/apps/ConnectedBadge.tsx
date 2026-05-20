/**
 * ConnectedBadge — 应用授权状态徽章
 *
 * 4 种状态：connected / expired / revoked / error；以及第 5 态 "未关联"
 * （由调用方传 status="none" 渲染，便于卡片"无授权"场景统一）。
 */

import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/components/ui/utils'

import type { AppAuthorizationStatus } from '@/lib/api/appAuthorizations'

export type ConnectedBadgeStatus = AppAuthorizationStatus | 'none'

interface ConnectedBadgeProps {
  status: ConnectedBadgeStatus
  className?: string
}

interface StatusConfig {
  label: string
  className: string
  icon?: 'check' | 'clock' | 'slash' | 'alert'
}

const STATUS_MAP: Record<ConnectedBadgeStatus, StatusConfig> = {
  none: {
    label: '未关联',
    className: 'bg-muted text-muted-foreground border-transparent',
  },
  connected: {
    label: '已连接',
    className:
      'bg-emerald-50 text-emerald-700 border-transparent dark:bg-emerald-500/10 dark:text-emerald-300',
    icon: 'check',
  },
  expired: {
    label: '已过期',
    className:
      'bg-amber-50 text-amber-700 border-transparent dark:bg-amber-500/10 dark:text-amber-300',
    icon: 'clock',
  },
  revoked: {
    label: '已撤销',
    className:
      'bg-zinc-100 text-zinc-600 border-transparent dark:bg-zinc-500/10 dark:text-zinc-300',
    icon: 'slash',
  },
  error: {
    label: '异常',
    className:
      'bg-red-50 text-red-700 border-transparent dark:bg-red-500/10 dark:text-red-300',
    icon: 'alert',
  },
}

export function ConnectedBadge({ status, className }: ConnectedBadgeProps) {
  const cfg = STATUS_MAP[status]
  return (
    <Badge variant="outline" className={cn(cfg.className, className)}>
      {cfg.icon === 'check' && <icons.CheckCircle2 className="size-3" />}
      {cfg.icon === 'clock' && <icons.Clock3 className="size-3" />}
      {cfg.icon === 'slash' && <icons.Slash className="size-3" />}
      {cfg.icon === 'alert' && <icons.AlertCircle className="size-3" />}
      <span>{cfg.label}</span>
    </Badge>
  )
}
