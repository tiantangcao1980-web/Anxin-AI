import type { ComponentType, ReactNode } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import type { LucideIcon } from '@/lib/icons'
import { cn } from '@/lib/utils'

type Tone = 'default' | 'primary' | 'success' | 'warning' | 'destructive' | 'ai'

const TONE_ICON_BG: Record<Tone, string> = {
  default: 'bg-surface-2 text-foreground-tertiary',
  primary: 'bg-primary-50 text-primary dark:bg-primary-100/30',
  success: 'bg-success/10 text-success',
  warning: 'bg-warning/10 text-warning',
  destructive: 'bg-destructive/10 text-destructive',
  ai: 'bg-ai-surface text-ai',
}

export interface StatCardProps {
  /** 主数据值（如数字、货币、时间） */
  value: ReactNode
  /** 标签（如 "待审核"、"本月收入"） */
  label: string
  /** 辅助说明 / 单位（如 "件"、"本周 +12%"） */
  hint?: ReactNode
  /** 左上图标（lucide-react 组件） */
  icon?: LucideIcon | ComponentType<{ className?: string }>
  /** 图标背景色调 */
  tone?: Tone
  /** 趋势：上升 / 下降 / 持平 */
  trend?: 'up' | 'down' | 'flat'
  /** 趋势数值（如 "+12%" 或 "-3"） */
  trendValue?: ReactNode
  /** 点击事件（设置后卡片变为可交互态） */
  onClick?: () => void
  /** 加载占位态 */
  loading?: boolean
  /** 索引（用于 Stagger 顺延） */
  index?: number
  className?: string
}

const TREND_ICON = { up: icons.TrendingUp, down: icons.TrendingDown, flat: icons.Minus }
const TREND_CLS = {
  up: 'text-success bg-success/10',
  down: 'text-destructive bg-destructive/10',
  flat: 'text-foreground-tertiary bg-surface-2',
}

/**
 * StatCard — 统一指标数据卡片
 *
 * 特性：
 * - 8 种业务色调（default / primary / success / warning / destructive / ai）
 * - 内置趋势徽章（上升/下降/持平）
 * - 可交互模式（传入 onClick 后获得悬浮抬升 + focus 态）
 * - 骨架加载占位
 * - 入场动画（通过 index 错峰延迟）
 *
 * 典型场景：
 * - 管理中心：待审核/审核中/高风险/已完成
 * - 案件中心：活跃案件/待办任务/本月结案
 * - 订阅中心：当前额度/剩余配额
 */
export function StatCard({
  value,
  label,
  hint,
  icon: Icon,
  tone = 'default',
  trend,
  trendValue,
  onClick,
  loading = false,
  index = 0,
  className,
}: StatCardProps) {
  const interactive = Boolean(onClick)
  const TrendIcon = trend ? TREND_ICON[trend] : null

  const content = loading ? (
    <>
      <div className="flex items-center justify-between">
        <div className="skeleton-caption !mb-0 w-20" />
        {Icon && <div className="skeleton-avatar !size-9 !rounded-dd" />}
      </div>
      <div className="mt-3 skeleton-title !w-24 !h-8" />
      <div className="skeleton-caption !w-16" />
    </>
  ) : (
    <>
      <div className="flex items-start justify-between gap-3">
        <span className="text-caption text-foreground-tertiary font-medium">{label}</span>
        {Icon && (
          <span
            className={cn(
              'inline-flex size-9 shrink-0 items-center justify-center rounded-dd',
              TONE_ICON_BG[tone],
            )}
          >
            <Icon className="size-[18px]" />
          </span>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2 min-w-0">
        <span className="text-[28px] font-medium leading-tight tracking-heading-md text-foreground num-tabular truncate">
          {value}
        </span>
      </div>
      <div className="mt-1 flex items-center gap-2 min-h-[18px]">
        {trend && TrendIcon && (
          <span
            className={cn(
              'inline-flex items-center gap-0.5 rounded-pill px-1.5 py-0.5 text-[11px] font-medium',
              TREND_CLS[trend],
            )}
          >
            <TrendIcon className="size-3" />
            {trendValue}
          </span>
        )}
        {hint && <span className="text-caption text-foreground-tertiary truncate">{hint}</span>}
      </div>
    </>
  )

  const base = cn(
    'relative overflow-hidden rounded-dd_xl border border-border bg-card p-4 shadow-elev-1',
    'transition-[transform,box-shadow,border-color] duration-fast ease-standard',
    interactive && 'cursor-pointer hover:-translate-y-0.5 hover:shadow-elev-2 hover:border-primary/30',
    interactive && 'focus-visible:outline-none focus-visible:shadow-focus-ring',
    interactive && 'active:translate-y-0 active:shadow-elev-1',
    className,
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.06, ease: [0.2, 0, 0, 1] }}
      className={base}
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick?.()
              }
            }
          : undefined
      }
    >
      {content}
    </motion.div>
  )
}

interface StatGridProps {
  children: ReactNode
  /** 每行列数，默认响应式 sm:2 md:3 lg:4 */
  cols?: 2 | 3 | 4 | 5
  className?: string
}

/**
 * StatGrid — StatCard 的响应式网格容器
 */
export function StatGrid({ children, cols = 4, className }: StatGridProps) {
  const colsCls = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
    5: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5',
  }[cols]
  return <div className={cn('grid gap-3 sm:gap-4', colsCls, className)}>{children}</div>
}
