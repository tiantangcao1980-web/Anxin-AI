/**
 * PageTemplates.tsx — V3 Editorial Luxury 业务页面模板集
 *
 * 配套 ListPageTemplate（在独立文件中）。本文件含其余 3 个模板：
 *   - DetailPageTemplate     详情页（CaseDetail / LawyerProfile）
 *   - FormPageTemplate       表单页（Settings / Onboarding）
 *   - DashboardTemplate      Dashboard（LawyerDashboard / MonitoringCenter）
 *
 * 全部 Editorial Luxury：衬线 H1 + micro UPPERCASE tracker + 1px hairline +
 * 单一琥珀橙 CTA + 暖灰阶梯背景，无任何域色 / 无 emoji / 无紫色。
 */

import * as React from 'react'
import {
  EditorialPageHeader,
  type EditorialPageHeaderProps,
} from './EditorialPageHeader'
import { ScrollArea } from './scroll-area'
import { cn } from './utils'

// ============================================================
// DetailPageTemplate
// ============================================================

export interface DetailPageTemplateProps {
  tracker?: EditorialPageHeaderProps['tracker']
  title: string
  description?: string
  actions?: React.ReactNode
  /** 主内容（详情卡 / 表单 / 文档预览）*/
  children: React.ReactNode
  /** 右侧栏（属性 / 时间线 / 关联 — 可选）*/
  aside?: React.ReactNode
  /** 顶部 ribbon（如 status banner / 提示条）*/
  ribbon?: React.ReactNode
  scrollable?: boolean
  maxWidth?: string
  className?: string
}

export function DetailPageTemplate({
  tracker,
  title,
  description,
  actions,
  children,
  aside,
  ribbon,
  scrollable = true,
  maxWidth = '1400px',
  className,
}: DetailPageTemplateProps) {
  const inner = (
    <div
      data-ui="detail-page"
      className={cn('mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-12', className)}
      style={{ maxWidth }}
    >
      {ribbon && (
        <div
          data-ui="detail-page-ribbon"
          className="mb-6 border border-border bg-surface-2 px-5 py-3 text-[14px]"
        >
          {ribbon}
        </div>
      )}
      <EditorialPageHeader
        tracker={tracker}
        title={title}
        description={description}
        actions={actions}
      />
      <div
        className={cn(
          'grid gap-10 lg:gap-16',
          aside ? 'grid-cols-1 lg:grid-cols-[1fr_320px]' : 'grid-cols-1',
        )}
      >
        <main data-ui="detail-page-main" className="min-w-0">
          {children}
        </main>
        {aside && (
          <aside data-ui="detail-page-aside" className="min-w-0 lg:sticky lg:top-24 lg:self-start">
            {aside}
          </aside>
        )}
      </div>
    </div>
  )
  if (!scrollable) return <div className="h-full overflow-hidden">{inner}</div>
  return <ScrollArea className="h-full">{inner}</ScrollArea>
}

// ============================================================
// FormPageTemplate
// ============================================================

export interface FormPageSectionConfig {
  key: string
  /** 区块标题（H2 sans 24px）*/
  title: string
  /** 区块描述 */
  description?: string
  /** 区块内容（form fields）*/
  children: React.ReactNode
}

export interface FormPageTemplateProps {
  tracker?: EditorialPageHeaderProps['tracker']
  title: string
  description?: string
  /** 顶部右侧按钮（可选）*/
  actions?: React.ReactNode
  /** 表单分区（每段 sticky 标题）*/
  sections: ReadonlyArray<FormPageSectionConfig>
  /** 底部 sticky 按钮区（保存 / 取消） — 推荐用法 */
  footer?: React.ReactNode
  scrollable?: boolean
  /** 左侧 anchor 导航（多 section 时推荐 true）*/
  anchorNav?: boolean
  /** 容器宽度 — 表单页通常更窄聚焦 */
  maxWidth?: string
  className?: string
}

export function FormPageTemplate({
  tracker,
  title,
  description,
  actions,
  sections,
  footer,
  scrollable = true,
  anchorNav = false,
  maxWidth = '960px',
  className,
}: FormPageTemplateProps) {
  const inner = (
    <div
      data-ui="form-page"
      className={cn('mx-auto px-6 sm:px-8 lg:px-12 py-8 lg:py-12', className)}
      style={{ maxWidth }}
    >
      <EditorialPageHeader
        tracker={tracker}
        title={title}
        description={description}
        actions={actions}
      />
      <div className={cn('grid gap-10', anchorNav ? 'lg:grid-cols-[180px_1fr]' : 'grid-cols-1')}>
        {anchorNav && (
          <nav
            data-ui="form-page-anchor"
            aria-label="表单分段"
            className="hidden lg:block lg:sticky lg:top-24 lg:self-start space-y-px"
          >
            {sections.map((s) => (
              <a
                key={s.key}
                href={`#${s.key}`}
                className="block px-3 py-2 text-[13px] text-muted-foreground hover:text-foreground border-l border-transparent hover:border-primary transition-colors"
              >
                {s.title}
              </a>
            ))}
          </nav>
        )}
        <div className="space-y-12 min-w-0">
          {sections.map((s) => (
            <section key={s.key} id={s.key} data-ui="form-page-section">
              <header className="mb-4 pb-3 border-b border-border">
                <h2 className="text-[20px] leading-[1.3] font-medium text-foreground">{s.title}</h2>
                {s.description && (
                  <p className="text-[13px] text-muted-foreground mt-1 leading-relaxed">
                    {s.description}
                  </p>
                )}
              </header>
              <div className="space-y-6">{s.children}</div>
            </section>
          ))}
        </div>
      </div>
      {footer && (
        <footer
          data-ui="form-page-footer"
          className="mt-12 pt-6 border-t border-border flex items-center justify-end gap-3"
        >
          {footer}
        </footer>
      )}
    </div>
  )
  if (!scrollable) return <div className="h-full overflow-hidden">{inner}</div>
  return <ScrollArea className="h-full">{inner}</ScrollArea>
}

// ============================================================
// DashboardTemplate
// ============================================================

export interface DashboardKpiConfig {
  key: string
  label: string
  /** 主值（如 "142" / "¥2.8M" / "8.4 小时"）*/
  value: React.ReactNode
  /** 副值（如 "较上周 +12%" — 可选）*/
  delta?: string
  /** 副值色调 */
  deltaTone?: 'normal' | 'success' | 'warning' | 'error'
  /** 可选 micro tracker（如 "INDEX 01"）*/
  tracker?: string
}

export interface DashboardTemplateProps {
  tracker?: EditorialPageHeaderProps['tracker']
  title: string
  description?: string
  actions?: React.ReactNode
  /** KPI 卡片组（Editorial 排版 — 大数 + 衬线 + caption）*/
  kpis?: ReadonlyArray<DashboardKpiConfig>
  /** KPI 区域下方的主体内容（图表 / 列表 / 多个 PanelSection）*/
  children: React.ReactNode
  scrollable?: boolean
  maxWidth?: string
  className?: string
}

export function DashboardTemplate({
  tracker,
  title,
  description,
  actions,
  kpis,
  children,
  scrollable = true,
  maxWidth = '1400px',
  className,
}: DashboardTemplateProps) {
  const inner = (
    <div
      data-ui="dashboard-page"
      className={cn('mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-12', className)}
      style={{ maxWidth }}
    >
      <EditorialPageHeader
        tracker={tracker}
        title={title}
        description={description}
        actions={actions}
      />
      {kpis && kpis.length > 0 && (
        <div
          data-ui="dashboard-kpis"
          className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border mb-10 border-t border-l border-border"
        >
          {kpis.map((k) => {
            const deltaToneClass = {
              normal: 'text-muted-foreground',
              success: 'text-success',
              warning: 'text-warning',
              error: 'text-destructive',
            }[k.deltaTone ?? 'normal']
            return (
              <div
                key={k.key}
                data-ui="dashboard-kpi"
                className="bg-card px-6 py-5 border-r border-b border-border"
              >
                {k.tracker && (
                  <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
                    {k.tracker}
                  </div>
                )}
                <div className="text-[13px] text-muted-foreground">{k.label}</div>
                <div className="font-serif text-[32px] leading-[1.1] tracking-tight text-foreground mt-1 tabular-nums">
                  {k.value}
                </div>
                {k.delta && (
                  <div className={cn('text-[12px] mt-2', deltaToneClass)}>{k.delta}</div>
                )}
              </div>
            )
          })}
        </div>
      )}
      <div data-ui="dashboard-body">{children}</div>
    </div>
  )
  if (!scrollable) return <div className="h-full overflow-hidden">{inner}</div>
  return <ScrollArea className="h-full">{inner}</ScrollArea>
}

/**
 * PanelSection — Dashboard 内的子区块（图表/列表/任意内容卡）
 * Editorial 风格：标题 H3 sans + caption + 1px hairline 边
 */
export interface PanelSectionProps {
  tracker?: string
  title?: string
  description?: string
  actions?: React.ReactNode
  children: React.ReactNode
  className?: string
}

export function PanelSection({
  tracker,
  title,
  description,
  actions,
  children,
  className,
}: PanelSectionProps) {
  return (
    <section data-ui="panel-section" className={cn('border border-border bg-card', className)}>
      {(title || actions || tracker) && (
        <header className="px-6 py-4 flex items-end justify-between gap-3 border-b border-border">
          <div>
            {tracker && (
              <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-1">
                {tracker}
              </div>
            )}
            {title && <h3 className="text-[18px] font-medium text-foreground">{title}</h3>}
            {description && (
              <p className="text-[13px] text-muted-foreground mt-0.5">{description}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </header>
      )}
      <div className="p-6">{children}</div>
    </section>
  )
}
