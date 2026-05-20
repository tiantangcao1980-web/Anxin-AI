/**
 * ErrorState — 全站统一错误态组件
 *
 * 用法：
 *   <ErrorState message="加载失败" onRetry={refetch} />
 *   <ErrorState variant="inline" message="请求超时" />
 *   <ErrorState variant="card" title="数据加载失败" message={error.message} onRetry={retry} />
 *
 * 设计规范 (DESIGN.md §2 Semantic):
 * - 使用 destructive 语义色
 * - icon 使用 AlertTriangle
 * - 操作按钮使用 buttonStyle.secondary
 */

import { icons } from '@/lib/icons'
import { buttonStyle, iconSize, statusColor } from '@/lib/design-tokens'

interface ErrorStateProps {
  variant?: 'page' | 'card' | 'inline'
  title?: string
  message: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({
  variant = 'page',
  title,
  message,
  onRetry,
  className = '',
}: ErrorStateProps) {
  if (variant === 'inline') {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 rounded-xl ${statusColor.error} ${className}`}>
        <icons.AlertTriangle className={iconSize.sm} />
        <span className="text-sm">{message}</span>
        {onRetry && (
          <button onClick={onRetry} className="ml-auto text-xs font-medium underline hover:no-underline">
            重试
          </button>
        )}
      </div>
    )
  }

  if (variant === 'card') {
    return (
      <div className={`rounded-2xl border border-destructive/20 bg-destructive/5 p-5 ${className}`}>
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-destructive/10">
            <icons.AlertTriangle className={`${iconSize.md} text-destructive`} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-foreground">{title || '出现错误'}</p>
            <p className="text-sm text-muted-foreground mt-1">{message}</p>
            {onRetry && (
              <button onClick={onRetry} className={`${buttonStyle.sm} mt-3 border border-destructive/20 text-destructive hover:bg-destructive/10`}>
                <icons.RefreshCw className={iconSize.xs} />
                <span className="ml-1.5">重试</span>
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Default: full-page error
  return (
    <div className={`flex items-center justify-center py-16 ${className}`}>
      <div className="text-center max-w-sm px-4">
        <div className="mx-auto mb-4 w-16 h-16 flex items-center justify-center rounded-2xl bg-destructive/10">
          <icons.AlertTriangle className={`${iconSize.xl} text-destructive`} />
        </div>
        <p className="font-medium text-foreground">{title || '出现错误'}</p>
        <p className="mt-1.5 text-sm text-muted-foreground">{message}</p>
        {onRetry && (
          <button onClick={onRetry} className={`${buttonStyle.secondary} mt-4 inline-flex items-center gap-2`}>
            <icons.RefreshCw className={iconSize.sm} />
            重试
          </button>
        )}
      </div>
    </div>
  )
}
