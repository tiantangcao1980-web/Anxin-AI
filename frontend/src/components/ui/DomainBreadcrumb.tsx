/**
 * DomainBreadcrumb — 业务域可视化面包屑
 *
 * 用法：
 *   <DomainBreadcrumb pathname={currentPath} />
 *   <DomainBreadcrumb pathname={currentPath} moduleName="案件中心" />
 *
 * 当 pathname 命中 inferDomainFromPath 时显示：
 *   [icon] {业务域} · {moduleName?}
 *
 * 当未命中时返回 null（不占空间）。
 *
 * 设计哲学：
 * - 紧凑、不抢镜（4pt 圆点 + 文字）
 * - 仅做"位置指示"，不承担行动
 * - 与 ModuleSidebar 标题区域配合使用，告诉用户"你在哪个业务域"
 */

import * as React from 'react'

import { inferDomainFromPath } from '@/lib/domains'
import { cn } from './utils'

export interface DomainBreadcrumbProps {
  /** 当前 pathname，必须由调用方传入（避免 hook 隐式耦合） */
  pathname: string
  /** 可选：当前模块/子页名称，显示在域名之后 */
  moduleName?: string
  /** 紧凑变体：仅显示一个 4pt 圆点 + 域名（不显示图标和 moduleName） */
  compact?: boolean
  /** 容器额外 className */
  className?: string
}

export function DomainBreadcrumb({
  pathname,
  moduleName,
  compact = false,
  className,
}: DomainBreadcrumbProps) {
  const meta = inferDomainFromPath(pathname)
  if (!meta) return null

  const Icon = meta.icon

  if (compact) {
    return (
      <span
        data-slot="domain-breadcrumb-compact"
        data-domain={meta.id}
        className={cn(
          'inline-flex items-center gap-1.5 text-xs text-muted-foreground',
          className,
        )}
        aria-label={`当前业务域：${meta.label}`}
      >
        <span
          aria-hidden
          className="h-1.5 w-1.5 rounded-full shrink-0"
          style={{ backgroundColor: `hsl(var(--${meta.cssVar}))` }}
        />
        <span className={cn('truncate', meta.colorClass)}>{meta.label}</span>
      </span>
    )
  }

  return (
    <nav
      data-slot="domain-breadcrumb"
      data-domain={meta.id}
      aria-label="业务域面包屑"
      className={cn('inline-flex items-center gap-2', className)}
    >
      <span
        className={cn(
          'inline-flex h-5 w-5 items-center justify-center rounded-md shrink-0',
          meta.surfaceClass,
        )}
        aria-hidden
      >
        <Icon className={cn('h-3 w-3', meta.colorClass)} />
      </span>
      <span className={cn('text-xs font-medium', meta.colorClass)}>
        {meta.label}
      </span>
      {moduleName ? (
        <>
          <span className="text-muted-foreground/40 text-xs" aria-hidden>
            ·
          </span>
          <span className="text-xs text-muted-foreground truncate">
            {moduleName}
          </span>
        </>
      ) : null}
    </nav>
  )
}
