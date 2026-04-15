/**
 * PageContainer - 统一页面布局容器
 *
 * 所有业务页面的标准布局组件，确保：
 * 1. 统一的 padding 和间距（响应式）
 * 2. 统一的标题/描述/操作栏样式
 * 3. 统一的深浅色模式支持
 * 4. 统一的滚动和溢出处理
 *
 * 用法:
 *   <PageContainer title="合同管理" description="AI 智能审查" actions={<Button>新建</Button>}>
 *     {children}
 *   </PageContainer>
 */

import { type ReactNode } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { heading, spacing, cardStyle } from '@/lib/design-tokens'

interface PageContainerProps {
  /** 页面标题 */
  title?: string
  /** 页面描述 */
  description?: string
  /** 右侧操作按钮区域 */
  actions?: ReactNode
  /** 页面内容 */
  children: ReactNode
  /** 是否使用 ScrollArea 包裹（默认 true） */
  scrollable?: boolean
  /** 自定义 className */
  className?: string
  /** 是否显示标题区域（默认 true，title 存在时显示） */
  showHeader?: boolean
  /** 是否全高（占满父容器，默认 true） */
  fullHeight?: boolean
  /** 标题下方的筛选栏或 Tab 栏 */
  toolbar?: ReactNode
  /** 嵌入模式：当 PageContainer 嵌套在 CenterLayout 等外层容器内时，
   *  标题降为 heading.card (h3) 并去掉卡片外框，避免层级重复 */
  embedded?: boolean
}

export function PageContainer({
  title,
  description,
  actions,
  children,
  scrollable = true,
  className = '',
  showHeader = true,
  fullHeight = true,
  toolbar,
  embedded = false,
}: PageContainerProps) {
  const hasHeader = showHeader && (title || actions)

  // 当 scrollable=false 且 fullHeight=true 时，内容区需要 flex-1 + min-h-0 来支持子容器的内部滚动
  const contentClasses = [
    `${spacing.page} ${spacing.section}`,
    !scrollable && fullHeight ? 'flex-1 flex flex-col min-h-0' : '',
    className,
  ].filter(Boolean).join(' ')

  const content = (
    <div data-ui="page-shell" className={contentClasses}>
      {hasHeader && (
        <div
          data-ui="page-header"
          className={`flex flex-col justify-between gap-3 sm:flex-row sm:items-center shrink-0 ${
            embedded
              ? 'border-b border-border pb-3'                 /* embedded: 轻量分割线，不用卡片 */
              : `${cardStyle.base}`                           /* standalone: 完整卡片包裹 */
          }`}
        >
          <div className="min-w-0">
            {title && embedded ? (
              <h3 className={`${heading.card} truncate`}>{title}</h3>
            ) : title ? (
              <h1 className={`${heading.page} truncate`}>{title}</h1>
            ) : null}
            {description && (
              <p className={`${heading.muted} mt-1 line-clamp-2`}>{description}</p>
            )}
          </div>
          {actions && <div data-ui="page-actions" className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
      )}

      {toolbar && <div data-ui="page-toolbar" className={`flex flex-wrap items-center gap-2 ${cardStyle.compact} shrink-0`}>{toolbar}</div>}

      {children}
    </div>
  )

  if (!scrollable) {
    // 使用 min-h-0 允许子容器正确计算 flex 高度并启用内部滚动
    return <div className={fullHeight ? 'h-full flex flex-col min-h-0' : ''}>{content}</div>
  }

  return (
    <ScrollArea className={fullHeight ? 'h-full' : ''}>
      {content}
    </ScrollArea>
  )
}

/**
 * PageSection - 页面内分区组件
 *
 * 用于页面内的逻辑分组，带标题和可选操作。
 */
interface PageSectionProps {
  title?: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}

export function PageSection({ title, description, actions, children, className = '' }: PageSectionProps) {
  return (
    <section className={`space-y-3 ${className}`}>
      {(title || actions) && (
        <div className="flex items-center justify-between gap-3">
          <div>
            {title && <h2 className={heading.section}>{title}</h2>}
            {description && <p className={`${heading.muted} mt-0.5`}>{description}</p>}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  )
}

/**
 * PageGrid - 统一的响应式网格布局
 */
interface PageGridProps {
  children: ReactNode
  /** 列数配置 */
  cols?: {
    default?: number
    sm?: number
    md?: number
    lg?: number
    xl?: number
  }
  className?: string
}

const colsMap: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
}

export function PageGrid({
  children,
  cols = { default: 1, md: 2, lg: 3 },
  className = '',
}: PageGridProps) {
  const classes = [
    'grid gap-4 sm:gap-5 lg:gap-6',
    cols.default ? colsMap[cols.default] : 'grid-cols-1',
    cols.sm ? `sm:${colsMap[cols.sm]}` : '',
    cols.md ? `md:${colsMap[cols.md]}` : '',
    cols.lg ? `lg:${colsMap[cols.lg]}` : '',
    cols.xl ? `xl:${colsMap[cols.xl]}` : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return <div className={classes}>{children}</div>
}
