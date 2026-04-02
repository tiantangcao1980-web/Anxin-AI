/**
 * PullToRefresh - 下拉刷新组件
 *
 * 移动端通用下拉刷新，支持自定义刷新动画和回调。
 */

import { useState, useRef, useCallback, type ReactNode } from 'react'

interface PullToRefreshProps {
  onRefresh: () => Promise<void>
  children: ReactNode
  threshold?: number
  disabled?: boolean
}

export function PullToRefresh({
  onRefresh,
  children,
  threshold = 80,
  disabled = false,
}: PullToRefreshProps) {
  const [pullDistance, setPullDistance] = useState(0)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const startY = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (disabled || isRefreshing) return
      const scrollTop = containerRef.current?.scrollTop ?? 0
      if (scrollTop > 0) return
      startY.current = e.touches[0].clientY
    },
    [disabled, isRefreshing]
  )

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (disabled || isRefreshing || startY.current === 0) return
      const scrollTop = containerRef.current?.scrollTop ?? 0
      if (scrollTop > 0) return

      const currentY = e.touches[0].clientY
      const diff = currentY - startY.current
      if (diff > 0) {
        // 阻尼效果：拉得越远，阻力越大
        const dampedDiff = diff * (1 - Math.min(diff / (threshold * 4), 0.6))
        setPullDistance(dampedDiff)
      }
    },
    [disabled, isRefreshing, threshold]
  )

  const handleTouchEnd = useCallback(async () => {
    if (disabled || isRefreshing) return
    startY.current = 0

    if (pullDistance >= threshold) {
      setIsRefreshing(true)
      setPullDistance(threshold * 0.6)
      try {
        await onRefresh()
      } finally {
        setIsRefreshing(false)
        setPullDistance(0)
      }
    } else {
      setPullDistance(0)
    }
  }, [disabled, isRefreshing, pullDistance, threshold, onRefresh])

  const progress = Math.min(pullDistance / threshold, 1)

  return (
    <div
      ref={containerRef}
      className="relative overflow-y-auto h-full"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* 下拉指示器 */}
      <div
        className="flex items-center justify-center overflow-hidden transition-[height] duration-200"
        style={{
          height: pullDistance > 0 ? `${pullDistance}px` : '0px',
          transition: pullDistance > 0 ? 'none' : 'height 0.3s ease',
        }}
      >
        <div className="flex flex-col items-center gap-1">
          <svg
            className={`w-5 h-5 text-muted-foreground transition-transform ${
              isRefreshing ? 'animate-spin' : ''
            }`}
            style={{
              transform: isRefreshing ? undefined : `rotate(${progress * 180}deg)`,
            }}
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            {isRefreshing ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3"
              />
            )}
          </svg>
          <span className="text-[11px] text-muted-foreground">
            {isRefreshing
              ? '刷新中...'
              : progress >= 1
                ? '释放刷新'
                : '下拉刷新'}
          </span>
        </div>
      </div>

      {children}
    </div>
  )
}
