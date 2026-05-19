/**
 * domain.tsx — 业务域可视化原子组件 (V3 · Editorial Luxury · Reset)
 *
 * 2026-05 Reset 说明：
 *   原版用 8 个高饱和色 + surface 底色 + 域色 stripe 实现 Badge/Stripe/Card/Grid。
 *   该方案违反 ui-design skill 多条硬性禁令 + DESIGN.md §1 设计哲学，已重写为
 *   Editorial Luxury 风格：
 *     - 衬线域名（Noto Serif SC）
 *     - 序号 01–08（serif num display）
 *     - Lucide 单色图标（1.5px stroke / text-foreground/70）
 *     - 1px hairline 边框分隔
 *     - 字距 0.16em + UPPERCASE 编辑级 caption
 *     - 单色调，仅 active 项可用 primary 琥珀橙 1px 左线点缀
 *
 * 用法：
 *   <DomainBadge domain="legal" />            // micro UPPERCASE 「LEGAL · 法务」
 *   <DomainCard domain="finance" />            // 序号 + 衬线域名 + 描述 + → 图标
 *   <DomainGrid />                             // 8 行编辑部目录
 *
 *   旧 DomainStripe 已不再需要（业务子页头部用 micro UPPERCASE breadcrumb 替代）
 *   旧 DomainStripe 导出仍保留为 no-op shim，避免破坏已有调用方
 *
 * 设计约束：
 *   - 禁止用色彩区分 8 个业务域
 *   - 主行动按钮 / 链接默认色 / 焦点环仍走 --primary（琥珀橙）
 *   - 与 risk-* / status-* 不重叠（风险是状态，域是分类）
 */

import * as React from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'

import { DOMAIN_BY_ID, DOMAINS, type DomainId, type DomainMeta } from '@/lib/domains'
import { cn } from './utils'

// ===== DomainBadge — micro UPPERCASE tracking 编辑级徽章 =====
// 用于：面包屑、表头、卡片角标
export interface DomainBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  domain: DomainId
  /** 是否显示英文 labelEn 前缀（如 "LEGAL · 法务"），默认 false 仅显示中文 */
  showEnglish?: boolean
}

export function DomainBadge({
  domain,
  showEnglish = false,
  className,
  ...rest
}: DomainBadgeProps) {
  const meta = DOMAIN_BY_ID[domain]
  return (
    <span
      data-slot="domain-badge"
      data-domain={domain}
      className={cn(
        'inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground',
        className,
      )}
      aria-label={`业务域：${meta.label}`}
      {...rest}
    >
      {showEnglish ? (
        <>
          <span>{meta.labelEn}</span>
          <span className="text-foreground/30" aria-hidden>·</span>
        </>
      ) : null}
      <span className="normal-case tracking-normal text-foreground/70">{meta.label}</span>
    </span>
  )
}

// ===== DomainStripe — 2026-05 Reset 后保留为 no-op =====
// 旧版渲染 4pt 高业务域彩条，违反「不强调 AI 感 / 不像 SaaS 控制台」原则。
// 业务子页头部现用 micro UPPERCASE breadcrumb（DomainBadge 即可）替代彩条识别。
// 保留导出仅为兼容老调用点，render 任何 DOM。
export function DomainStripe(_props: { domain: DomainId } & React.HTMLAttributes<HTMLDivElement>) {
  return null
}

// ===== DomainCard — Editorial Luxury 卡片 =====
// 序号 (01–08 serif) + 衬线域名 H3 + caption 描述 + → 图标
export interface DomainCardProps {
  domain: DomainId
  /** 自定义入口路径（默认走 meta.defaultPath） */
  href?: string
  /** 序号字串，默认从 DOMAINS 顺序计算 */
  index?: string
  /** 「推荐入口」「敬请期待」一类 micro UPPERCASE 标签 */
  badge?: string
  /** 数字徽标（如未读数）— Reset 后采用 muted-foreground 极低视觉权重 */
  count?: number
  className?: string
  onClick?: () => void
}

export function DomainCard({
  domain,
  href,
  index,
  badge,
  count,
  className,
  onClick,
}: DomainCardProps) {
  const meta: DomainMeta = DOMAIN_BY_ID[domain]
  const Icon = meta.icon
  const finalHref = href ?? meta.defaultPath
  // 序号：使用 DOMAINS 的实际位置，固定两位
  const indexStr = index ?? String(DOMAINS.findIndex((d) => d.id === domain) + 1).padStart(2, '0')

  const inner = (
    <>
      {/* 顶部：序号 + 可选 badge */}
      <div className="flex items-baseline justify-between mb-3">
        <span className="font-serif text-2xl tracking-tight text-muted-foreground">{indexStr}</span>
        {badge ? (
          <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            {badge}
          </span>
        ) : null}
      </div>

      {/* 主标题：衬线域名 + Lucide 图标 */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-serif text-[20px] leading-tight tracking-tight text-foreground">
            {meta.label}
          </h3>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground line-clamp-2">
            {meta.tagline}
          </p>
        </div>
        <Icon className="h-4 w-4 mt-1 shrink-0 text-foreground/60 stroke-[1.5]" aria-hidden />
      </div>

      {/* 底部：可选 count + → */}
      <div className="mt-4 pt-3 flex items-center justify-between border-t border-border/40">
        <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground/70">
          {meta.labelEn}
        </span>
        {typeof count === 'number' && count > 0 ? (
          <span className="text-xs text-muted-foreground">
            {count > 99 ? '99+' : count}
          </span>
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50 group-hover:text-foreground group-hover:translate-x-0.5 transition-all stroke-[1.5]" aria-hidden />
        )}
      </div>
    </>
  )

  const baseClass = cn(
    'group relative block bg-card border border-border/60 px-5 py-4',
    'transition-colors duration-200 ease-standard',
    'hover:bg-surface-2/40 hover:border-border-strong',
    'focus-visible:outline-none focus-visible:border-primary',
    className,
  )

  if (onClick) {
    return (
      <button type="button" data-slot="domain-card" data-domain={domain}
        className={cn(baseClass, 'text-left w-full')} onClick={onClick}>
        {inner}
      </button>
    )
  }
  return (
    <Link to={finalHref} data-slot="domain-card" data-domain={domain} className={baseClass}>
      {inner}
    </Link>
  )
}

// ===== DomainGrid — 编辑部目录式 8 行 =====
// 不是 4×2 卡片墙；是编辑级目录列表，一行一域。
export interface DomainGridProps {
  /** 仅显示某几个域 */
  only?: readonly DomainId[]
  /** 域 → 额外数据 */
  meta?: Partial<Record<DomainId, { count?: number; badge?: string; href?: string }>>
  className?: string
}

export function DomainGrid({ only, meta, className }: DomainGridProps) {
  const list = only && only.length > 0
    ? only.map((id) => DOMAIN_BY_ID[id])
    : DOMAINS
  return (
    <ol
      data-slot="domain-grid"
      className={cn(
        // 默认单列编辑部目录；空间充裕时双列
        'grid gap-px sm:grid-cols-2 lg:grid-cols-2',
        className,
      )}
    >
      {list.map((d) => (
        <li key={d.id}>
          <DomainCard
            domain={d.id}
            href={meta?.[d.id]?.href}
            count={meta?.[d.id]?.count}
            badge={meta?.[d.id]?.badge}
          />
        </li>
      ))}
    </ol>
  )
}
