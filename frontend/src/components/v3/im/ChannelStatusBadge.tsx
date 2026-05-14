/**
 * ChannelStatusBadge — IM 渠道连接状态徽章
 *
 * 4 种状态：unconfigured / connecting / connected / error
 */

import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/components/ui/utils'

import type { IMChannelStatus } from '@/lib/api/imChannels'

interface ChannelStatusBadgeProps {
  status: IMChannelStatus
  className?: string
}

interface StatusConfig {
  label: string
  className: string
  icon?: 'check' | 'spin' | 'alert'
}

const STATUS_MAP: Record<IMChannelStatus, StatusConfig> = {
  unconfigured: {
    label: '未关联',
    className: 'bg-muted text-muted-foreground border-transparent',
  },
  connecting: {
    label: '连接中',
    className:
      'bg-blue-50 text-blue-700 border-transparent dark:bg-blue-500/10 dark:text-blue-300',
    icon: 'spin',
  },
  connected: {
    label: '已连接',
    className:
      'bg-emerald-50 text-emerald-700 border-transparent dark:bg-emerald-500/10 dark:text-emerald-300',
    icon: 'check',
  },
  error: {
    label: '异常',
    className: 'bg-red-50 text-red-700 border-transparent dark:bg-red-500/10 dark:text-red-300',
    icon: 'alert',
  },
}

export function ChannelStatusBadge({ status, className }: ChannelStatusBadgeProps) {
  const cfg = STATUS_MAP[status]
  return (
    <Badge variant="outline" className={cn(cfg.className, className)}>
      {cfg.icon === 'check' && <icons.CheckCircle2 className="size-3" />}
      {cfg.icon === 'spin' && <icons.Loader2 className="size-3 animate-spin" />}
      {cfg.icon === 'alert' && <icons.AlertCircle className="size-3" />}
      <span>{cfg.label}</span>
    </Badge>
  )
}
