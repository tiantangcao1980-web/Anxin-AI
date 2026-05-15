/**
 * domain.tsx — 业务域可视化原子组件
 *
 * 用法：
 *   import { DomainBadge, DomainCard, DomainStripe } from '@/components/ui/domain'
 *   <DomainBadge domain="legal" />
 *   <DomainCard domain="finance" title="财务驾驶舱" description="..." onClick={...} />
 *   <DomainStripe domain="compliance" /> {/* 顶部 4px 高彩条，用于域内页面标识 *}
 *
 * 设计约束：
 * - 仅承担「分类标识」，不承担「行动召唤」
 * - 主行动按钮 / 焦点环 / 链接默认色仍走 --primary（琥珀橙）
 * - 与 Risk badge / Status badge 互不重叠（风险是状态，域是分类）
 */

import * as React from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'

import { DOMAIN_BY_ID, type DomainId, type DomainMeta } from '@/lib/domains'
import { cn } from './utils'

// ===== DomainBadge =====
// 小尺寸徽章，用于面包屑、表头、卡片角标
export interface DomainBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  domain: DomainId
  /** 是否显示图标（默认 true） */
  showIcon?: boolean
  /** 紧凑模式：仅图标，靠 a11y title 提示文本 */
  iconOnly?: boolean
  /** 尺寸 */
  size?: 'sm' | 'md'
}

export function DomainBadge({
  domain,
  showIcon = true,
  iconOnly = false,
  size = 'sm',
  className,
  ...rest
}: DomainBadgeProps) {
  const meta = DOMAIN_BY_ID[domain]
  const Icon = meta.icon
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'
  return (
    <span
      data-slot="domain-badge"
      data-domain={domain}
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium',
        size === 'sm'
          ? 'px-2 py-0.5 text-[11px]'
          : 'px-2.5 py-1 text-xs',
        meta.surfaceClass,
        meta.colorClass,
        className,
      )}
      title={iconOnly ? meta.label : undefined}
      aria-label={iconOnly ? meta.label : undefined}
      {...rest}
    >
      {showIcon ? <Icon className={iconSize} /> : null}
      {iconOnly ? null : meta.label}
    </span>
  )
}

// ===== DomainStripe =====
// 4px 高的顶部彩条，用于域内页面顶部识别（不抢镜）
export function DomainStripe({
  domain,
  className,
  ...rest
}: { domain: DomainId } & React.HTMLAttributes<HTMLDivElement>) {
  const meta = DOMAIN_BY_ID[domain]
  return (
    <div
      data-slot="domain-stripe"
      data-domain={domain}
      role="presentation"
      className={cn('h-1 w-full', className)}
      style={{ backgroundColor: `hsl(var(--${meta.cssVar}))` }}
      {...rest}
    />
  )
}

// ===== DomainCard =====
// Dashboard 业务域入口卡片
export interface DomainCardProps {
  domain: DomainId
  /** 入口名（默认取 meta.label） */
  title?: string
  /** 一句话定位（默认取 meta.tagline） */
  description?: string
  /** 跳转路径（默认取 meta.defaultPath） */
  href?: string
  /** 右上角徽章文本，如「新功能」「Beta」 */
  badge?: string
  /** 数字徽标（如未读数） */
  count?: number
  className?: string
  onClick?: () => void
}

export function DomainCard({
  domain,
  title,
  description,
  href,
  badge,
  count,
  className,
  onClick,
}: DomainCardProps) {
  const meta: DomainMeta = DOMAIN_BY_ID[domain]
  const Icon = meta.icon
  const finalHref = href ?? meta.defaultPath

  const inner = (
    <>
      {/* 顶部彩条 */}
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-1 rounded-t-2xl"
        style={{ backgroundColor: `hsl(var(--${meta.cssVar}))` }}
      />

      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className={cn(
            'flex h-11 w-11 shrink-0 items-center justify-center rounded-xl',
            meta.surfaceClass,
          )}
        >
          <Icon className={cn('h-5 w-5', meta.colorClass)} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-[15px] font-medium text-foreground">
              {title ?? meta.label}
            </h3>
            {badge ? (
              <span
                className={cn(
                  'rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                  meta.surfaceClass,
                  meta.colorClass,
                )}
              >
                {badge}
              </span>
            ) : null}
            {typeof count === 'number' && count > 0 ? (
              <span className="ml-auto rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                {count > 99 ? '99+' : count}
              </span>
            ) : null}
          </div>
          <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
            {description ?? meta.tagline}
          </p>
        </div>
        <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground/60 transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
      </div>
    </>
  )

  // 共用样式
  const baseClass = cn(
    'group relative block overflow-hidden rounded-2xl border border-border/40 bg-card p-4 pt-5',
    'shadow-elev-1 transition-all duration-200 ease-standard',
    'hover:-translate-y-0.5 hover:shadow-elev-3 hover:border-border-strong',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
    className,
  )

  if (onClick) {
    return (
      <button
        type="button"
        data-slot="domain-card"
        data-domain={domain}
        className={cn(baseClass, 'text-left w-full')}
        onClick={onClick}
      >
        {inner}
      </button>
    )
  }
  return (
    <Link
      to={finalHref}
      data-slot="domain-card"
      data-domain={domain}
      className={baseClass}
    >
      {inner}
    </Link>
  )
}

// ===== DomainGrid =====
// 8 大业务域一次性渲染（响应式 1/2/4 列）
export interface DomainGridProps {
  /** 仅显示某几个域；不传则显示全部 */
  only?: readonly DomainId[]
  /** 域 → 额外数据（如未读数、徽章）的映射 */
  meta?: Partial<Record<DomainId, { count?: number; badge?: string; href?: string }>>
  className?: string
}

export function DomainGrid({ only, meta, className }: DomainGridProps) {
  const list = only && only.length > 0
    ? only.map((id) => DOMAIN_BY_ID[id])
    : Object.values(DOMAIN_BY_ID)
  return (
    <div
      data-slot="domain-grid"
      className={cn(
        'grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
        className,
      )}
    >
      {list.map((d) => (
        <DomainCard
          key={d.id}
          domain={d.id}
          href={meta?.[d.id]?.href}
          count={meta?.[d.id]?.count}
          badge={meta?.[d.id]?.badge}
        />
      ))}
    </div>
  )
}
