import type { ComponentType, ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import type { LucideIcon } from '@/lib/icons'
import { cn } from '@/lib/utils'

export type PageState = 'loading' | 'empty' | 'error' | 'content'

interface StateViewProps<T> {
  /** 当前状态 */
  state: PageState
  /** 数据（content 态必须） */
  data?: T
  /** 骨架占位（默认通用列表骨架） */
  loading?: ReactNode
  /** 空态节点 */
  empty: ReactNode
  /** 错误态节点 */
  error: ReactNode
  /** 渲染数据 */
  children: (data: T) => ReactNode
  className?: string
}

/**
 * StateView — 统一的页面/模块状态切换器
 *
 * 规范化了 loading → empty / content / error 四态的切换动画与无抖动过渡。
 * 所有业务页的列表/详情/数据模块都应通过它渲染，避免各自实现状态分支。
 *
 * 示例：
 *   <StateView
 *     state={isLoading ? 'loading' : error ? 'error' : items.length === 0 ? 'empty' : 'content'}
 *     data={items}
 *     empty={<EmptyState title="暂无案件" action={...} />}
 *     error={<ErrorState onRetry={refetch} />}
 *   >
 *     {(items) => <CaseList items={items} />}
 *   </StateView>
 */
export function StateView<T>({
  state,
  data,
  loading,
  empty,
  error,
  children,
  className,
}: StateViewProps<T>) {
  return (
    <div className={cn('relative min-h-[200px]', className)}>
      <AnimatePresence mode="wait">
        <motion.div
          key={state}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.2, ease: [0.2, 0, 0, 1] }}
          className="w-full"
        >
          {state === 'loading' && (loading ?? <DefaultLoadingSkeleton />)}
          {state === 'empty' && empty}
          {state === 'error' && error}
          {state === 'content' && data !== undefined && children(data)}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

/**
 * DefaultLoadingSkeleton — 通用列表骨架占位
 * 3-5 行，柔和 shimmer，符合 DesignDNA §12A.6 暖色调
 */
export function DefaultLoadingSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3 py-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="rounded-dd_lg border border-border-subtle bg-card p-4 shadow-elev-1"
        >
          <div className="flex items-center gap-3">
            <div className="skeleton skeleton-avatar" />
            <div className="flex-1">
              <div className="skeleton skeleton-title !w-1/3" />
              <div className="skeleton skeleton-text !w-2/3 !mb-0" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

/**
 * StatCardSkeleton — 指标卡网格骨架
 */
export function StatCardSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-dd_xl border border-border bg-card p-4 shadow-elev-1">
          <div className="flex items-center justify-between">
            <div className="skeleton skeleton-caption !w-20 !mb-0" />
            <div className="skeleton skeleton-avatar !size-9 !rounded-dd" />
          </div>
          <div className="mt-3 skeleton skeleton-title !w-24 !h-8" />
          <div className="skeleton skeleton-caption !w-16" />
        </div>
      ))}
    </div>
  )
}

/**
 * TableSkeleton — 表格骨架
 */
export function TableSkeleton({
  rows = 6,
  cols = 5,
}: {
  rows?: number
  cols?: number
}) {
  return (
    <div className="overflow-hidden rounded-dd_lg border border-border">
      <div className="border-b border-border bg-surface-2 p-3">
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
          {Array.from({ length: cols }).map((_, i) => (
            <div key={i} className="skeleton skeleton-caption !mb-0 !w-20" />
          ))}
        </div>
      </div>
      <div className="divide-y divide-border-subtle">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="p-3">
            <div
              className="grid gap-4"
              style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
            >
              {Array.from({ length: cols }).map((_, c) => (
                <div key={c} className="skeleton skeleton-text !mb-0" style={{ width: `${70 - c * 8}%` }} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * InlineLoader — 小型按钮内/行内加载指示器
 */
export function InlineLoader({
  icon: Icon,
  label,
  className,
}: {
  icon?: LucideIcon | ComponentType<{ className?: string }>
  label?: string
  className?: string
}) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-caption text-foreground-tertiary', className)}>
      {Icon ? (
        <Icon className="size-3.5 animate-spin" />
      ) : (
        <span className="inline-flex items-center gap-0.5">
          <span className="size-1 rounded-pill bg-ai-thinking animate-ai-thinking-dot [animation-delay:-0.3s]" />
          <span className="size-1 rounded-pill bg-ai-thinking animate-ai-thinking-dot [animation-delay:-0.15s]" />
          <span className="size-1 rounded-pill bg-ai-thinking animate-ai-thinking-dot" />
        </span>
      )}
      {label && <span>{label}</span>}
    </span>
  )
}
