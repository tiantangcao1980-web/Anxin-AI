/**
 * LoadingState — 全站统一加载态组件
 *
 * 三种变体：
 *   <LoadingState />                      — 默认 spinner（小区域内联使用）
 *   <LoadingState variant="skeleton" />   — 骨架屏（卡片/列表占位）
 *   <LoadingState variant="page" />       — 全页加载（首次进入页面）
 *
 * 设计规范 (DESIGN.md §6 Motion):
 * - spinner 使用 Loader2 + animate-spin
 * - 骨架屏使用 animate-pulse + bg-muted 中性占位
 * - 文案使用 muted-foreground
 */

import { icons } from '@/lib/icons'
import { iconSize } from '@/lib/design-tokens'

interface LoadingStateProps {
  variant?: 'spinner' | 'skeleton' | 'page'
  text?: string
  rows?: number
  className?: string
}

export function LoadingState({
  variant = 'spinner',
  text,
  rows = 3,
  className = '',
}: LoadingStateProps) {
  if (variant === 'skeleton') {
    return (
      <div className={`space-y-3 ${className}`}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="space-y-2">
            <div className={`h-4 bg-muted animate-pulse rounded-lg ${i === 0 ? 'w-3/4' : i === rows - 1 ? 'w-1/2' : 'w-full'}`} />
          </div>
        ))}
      </div>
    )
  }

  if (variant === 'page') {
    return (
      <div className={`flex flex-col items-center justify-center py-20 ${className}`}>
        <icons.Loader2 className={`${iconSize.xl} text-primary animate-spin mb-4`} />
        <p className="text-sm text-muted-foreground">{text || '加载中...'}</p>
      </div>
    )
  }

  // Default: inline spinner
  return (
    <div className={`flex items-center justify-center gap-2 py-8 ${className}`}>
      <icons.Loader2 className={`${iconSize.md} text-primary animate-spin`} />
      {text && <span className="text-sm text-muted-foreground">{text}</span>}
    </div>
  )
}
