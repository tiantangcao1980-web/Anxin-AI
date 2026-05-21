/**
 * EditorialPageHeader — V3 Editorial Luxury 页面头部
 *
 * 业务页统一的页面头部（标题 + 描述 + 操作 + tracker），所有 *PageTemplate 共用。
 * 视觉对齐 docs/design/v3-prototype-editorial.html Screen 3「业务子页」头部。
 *
 * 用法：
 *   <EditorialPageHeader
 *     tracker={["Legal", "案件中心"]}        // micro UPPERCASE · 0.16em
 *     title="案件中心"                       // serif Display 32-48px
 *     description="案件全生命周期 · 团队协作" // serif italic
 *     actions={<button className="...">新建</button>}
 *   />
 *
 * 设计约束（继承 ui-design skill Editorial Luxury）：
 * - title 必用 font-serif（Noto Serif SC），32px/H1
 * - tracker 必为 micro UPPERCASE 0.16em
 * - 不用 cardStyle.base 卡片框（Editorial 不用卡）
 * - 底部 hairline border 分隔，不用 shadow
 * - 配色仅 ink + ink-2 + muted-foreground 暖灰阶梯
 */

import * as React from 'react'
import { cn } from './utils'

export interface EditorialPageHeaderProps {
  /**
   * Micro UPPERCASE tracker，用 · 连接多段；建议 1-3 段。
   * 例：["Legal", "案件中心"] → "LEGAL · 案件中心"
   */
  tracker?: ReadonlyArray<string>
  /** serif H1 主标题（32px 默认；hero 场景可上 display 用 size="display"）*/
  title: string
  /** serif italic 副标，承担"编辑感" */
  description?: string
  /** 右侧操作区（按钮 / 链接组）*/
  actions?: React.ReactNode
  /** 标题字号：'h1' (32px) 默认 / 'display' (48px) 仅 hero */
  size?: 'h1' | 'display'
  /** 顶部 padding：'normal' 默认 / 'compact' 用于 embedded 嵌套场景 */
  density?: 'normal' | 'compact'
  className?: string
}

export function EditorialPageHeader({
  tracker,
  title,
  description,
  actions,
  size = 'h1',
  density = 'normal',
  className,
}: EditorialPageHeaderProps) {
  const titleClasses = size === 'display'
    ? 'font-serif text-[48px] leading-[1.1] tracking-[-0.04em] font-medium text-foreground'
    : 'font-serif text-[32px] leading-[1.2] tracking-[-0.02em] font-medium text-foreground'

  const padBottom = density === 'compact' ? 'pb-5' : 'pb-8'
  const marginBottom = density === 'compact' ? 'mb-6' : 'mb-10'

  return (
    <header
      data-ui="editorial-page-header"
      className={cn(
        'flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between border-b border-border',
        padBottom,
        marginBottom,
        className,
      )}
    >
      <div className="min-w-0 flex-1">
        {tracker && tracker.length > 0 ? (
          <div
            data-ui="editorial-tracker"
            className="mb-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground"
          >
            {tracker.map((seg, i) => (
              <React.Fragment key={i}>
                {i > 0 && <span className="text-foreground/30 mx-1.5" aria-hidden>·</span>}
                <span className={i === tracker.length - 1 ? 'text-foreground/70 normal-case tracking-normal' : ''}>
                  {seg}
                </span>
              </React.Fragment>
            ))}
          </div>
        ) : null}
        <h1 className={titleClasses}>{title}</h1>
        {description ? (
          <p className="mt-3 text-[15px] leading-[1.65] text-foreground/80 max-w-[60ch]">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div data-ui="editorial-page-actions" className="flex items-center gap-3 shrink-0">
          {actions}
        </div>
      ) : null}
    </header>
  )
}
