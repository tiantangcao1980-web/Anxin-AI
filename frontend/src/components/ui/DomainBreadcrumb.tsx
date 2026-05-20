/**
 * DomainBreadcrumb — 业务域面包屑 (V3 · Editorial Luxury · Reset)
 *
 * 2026-05 Reset 说明：
 *   旧版有 surface 域色底 + 域色 4pt 圆点 + 域色文字 — 已全部删除。
 *   新版只有：micro UPPERCASE tracking 文字。
 *
 * 用法：
 *   <DomainBreadcrumb pathname={currentPath} />
 *   <DomainBreadcrumb pathname={currentPath} moduleName="合同审查" />
 *
 * 渲染：
 *   LEGAL · 法务  →  「LEGAL · 法务」
 *   LEGAL · 法务 + moduleName='合同审查'  →  「LEGAL · 法务 · 合同审查」
 *
 * 当 pathname 命中 inferDomainFromPath 时显示；否则返回 null。
 */

import * as React from 'react'

import { inferDomainFromPath } from '@/lib/domains'
import { cn } from './utils'

export interface DomainBreadcrumbProps {
  pathname: string
  moduleName?: string
  /** 兼容旧 API — compact 现已等同默认（Reset 后无对比变体） */
  compact?: boolean
  className?: string
}

export function DomainBreadcrumb({
  pathname,
  moduleName,
  className,
}: DomainBreadcrumbProps) {
  const meta = inferDomainFromPath(pathname)
  if (!meta) return null

  return (
    <nav
      data-slot="domain-breadcrumb"
      data-domain={meta.id}
      aria-label="业务域面包屑"
      className={cn(
        'inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground',
        className,
      )}
    >
      <span>{meta.labelEn}</span>
      <span className="text-foreground/30" aria-hidden>·</span>
      <span className="normal-case tracking-normal text-foreground/70">{meta.label}</span>
      {moduleName ? (
        <>
          <span className="text-foreground/30" aria-hidden>·</span>
          <span className="normal-case tracking-normal text-muted-foreground truncate max-w-[24ch]">
            {moduleName}
          </span>
        </>
      ) : null}
    </nav>
  )
}
