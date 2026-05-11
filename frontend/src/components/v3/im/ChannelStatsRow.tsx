/**
 * ChannelStatsRow — 渠道统计三列：已配对用户 / 已配对群聊 / 待处理请求
 */

import { cn } from '@/components/ui/utils'

import type { IMChannelStats } from '@/lib/api/imChannels'

interface ChannelStatsRowProps {
  stats: IMChannelStats
  className?: string
}

interface StatItem {
  label: string
  value: number
  highlight?: boolean
}

export function ChannelStatsRow({ stats, className }: ChannelStatsRowProps) {
  const items: StatItem[] = [
    { label: '已配对用户', value: stats.bound_users },
    { label: '已配对群聊', value: stats.bound_groups },
    { label: '待处理请求', value: stats.pending_pairings, highlight: stats.pending_pairings > 0 },
  ]

  return (
    <div className={cn('grid grid-cols-3 gap-2', className)}>
      {items.map((it) => (
        <div
          key={it.label}
          className="rounded-lg border border-border/40 bg-muted/30 px-3 py-2 text-center"
        >
          <div
            className={cn(
              'text-lg font-semibold tabular-nums',
              it.highlight ? 'text-amber-600 dark:text-amber-400' : 'text-foreground',
            )}
          >
            {it.value}
          </div>
          <div className="mt-0.5 text-[10px] leading-tight text-muted-foreground">
            {it.label}
          </div>
        </div>
      ))}
    </div>
  )
}
