import { useEffect, useRef, useState, type ReactNode, type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface ScrollShellProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  /** 是否在内容未触底时显示渐变遮罩提示可滚动（默认 true） */
  showShadows?: boolean
  /** 水平(默认) / 垂直 */
  orientation?: 'horizontal' | 'vertical'
  /** 额外的滚动容器类名（传给内部 overflow 容器） */
  scrollClassName?: string
}

/**
 * ScrollShell — 带边缘渐变遮罩的滚动容器
 *
 * 业务场景：
 * - 案件/合同列表横向滚动的表格
 * - 知识库分类标签横向滚动
 * - 长历史对话列表纵向滚动到边缘的提示
 *
 * 渐变遮罩仅在"该方向还有内容未显示"时出现，自动响应滚动位置。
 */
export function ScrollShell({
  children,
  showShadows = true,
  orientation = 'horizontal',
  scrollClassName,
  className,
  ...rest
}: ScrollShellProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [shadows, setShadows] = useState({ start: false, end: false })

  useEffect(() => {
    const el = scrollRef.current
    if (!el || !showShadows) return

    const update = () => {
      if (orientation === 'horizontal') {
        const { scrollLeft, scrollWidth, clientWidth } = el
        setShadows({
          start: scrollLeft > 2,
          end: scrollLeft + clientWidth < scrollWidth - 2,
        })
      } else {
        const { scrollTop, scrollHeight, clientHeight } = el
        setShadows({
          start: scrollTop > 2,
          end: scrollTop + clientHeight < scrollHeight - 2,
        })
      }
    }

    update()
    el.addEventListener('scroll', update, { passive: true })
    const ro = new ResizeObserver(update)
    ro.observe(el)
    window.addEventListener('resize', update)
    return () => {
      el.removeEventListener('scroll', update)
      ro.disconnect()
      window.removeEventListener('resize', update)
    }
  }, [showShadows, orientation])

  const isH = orientation === 'horizontal'

  return (
    <div
      className={cn('relative', className)}
      {...rest}
    >
      {showShadows && (
        <>
          <div
            aria-hidden
            className={cn(
              'pointer-events-none absolute z-sticky transition-opacity duration-fast ease-standard',
              isH ? 'inset-y-0 left-0 w-6 bg-gradient-to-r from-background to-transparent' :
                    'inset-x-0 top-0 h-6 bg-gradient-to-b from-background to-transparent',
              shadows.start ? 'opacity-100' : 'opacity-0',
            )}
          />
          <div
            aria-hidden
            className={cn(
              'pointer-events-none absolute z-sticky transition-opacity duration-fast ease-standard',
              isH ? 'inset-y-0 right-0 w-6 bg-gradient-to-l from-background to-transparent' :
                    'inset-x-0 bottom-0 h-6 bg-gradient-to-t from-background to-transparent',
              shadows.end ? 'opacity-100' : 'opacity-0',
            )}
          />
        </>
      )}
      <div
        ref={scrollRef}
        className={cn(
          isH ? 'overflow-x-auto overflow-y-hidden' : 'overflow-y-auto overflow-x-hidden',
          'scroll-momentum scrollbar-hide',
          scrollClassName,
        )}
      >
        {children}
      </div>
    </div>
  )
}
