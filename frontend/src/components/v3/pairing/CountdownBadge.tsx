/**
 * CountdownBadge — 配对请求的倒计时徽章
 *
 * - 基于 props.expiresAt(ISO 时间戳)计算剩余时长
 * - 自身不维护 setInterval(避免每秒重渲);由父组件通过 nowMs 触发更新
 *   (页面级 5s tick 即可,显示"剩余 X 小时"精度足够)
 * - 剩余 <2h 红色,2-6h 琥珀色,>6h 默认色
 */

import { Clock } from 'lucide-react'

import { cn } from '@/components/ui/utils'

interface CountdownBadgeProps {
  /** ISO 字符串,过期时间 */
  expiresAt: string
  /** 当前时间(ms),由父组件 tick 注入。不传则用 Date.now() 一次性渲染 */
  nowMs?: number
  className?: string
}

interface RemainingDisplay {
  text: string
  level: 'normal' | 'warn' | 'danger'
}

function computeRemaining(expiresAt: string, nowMs: number): RemainingDisplay {
  const diffMs = new Date(expiresAt).getTime() - nowMs
  if (diffMs <= 0) return { text: '已过期', level: 'danger' }

  const totalMin = Math.floor(diffMs / 60_000)
  const hr = Math.floor(totalMin / 60)
  const min = totalMin % 60

  let text: string
  if (hr >= 1) {
    text = min > 0 ? `剩余 ${hr} 小时 ${min} 分` : `剩余 ${hr} 小时`
  } else {
    text = `剩余 ${min} 分钟`
  }

  let level: RemainingDisplay['level'] = 'normal'
  if (hr < 2) level = 'danger'
  else if (hr < 6) level = 'warn'

  return { text, level }
}

const LEVEL_CLASS: Record<RemainingDisplay['level'], string> = {
  normal:
    'bg-muted text-muted-foreground border-transparent',
  warn:
    'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-900/60',
  danger:
    'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-300 dark:border-red-900/60',
}

export function CountdownBadge({ expiresAt, nowMs, className }: CountdownBadgeProps) {
  const remaining = computeRemaining(expiresAt, nowMs ?? Date.now())
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium',
        LEVEL_CLASS[remaining.level],
        className,
      )}
      title={`过期时间:${new Date(expiresAt).toLocaleString('zh-CN')}`}
    >
      <Clock className="size-3" />
      {remaining.text}
    </span>
  )
}
