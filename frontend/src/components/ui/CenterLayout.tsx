/**
 * CenterLayout — 「中心」页面布局模板（Editorial Luxury · Phase 1.14）
 *
 * 用于 CaseCenter、ManagementCenter 等「顶部标题 + Tab 切换 + 全高内容」模式的页面。
 * 风格：
 *   - 标题用 serif H1 + micro UPPERCASE tracker（与 EditorialPageHeader 一致）
 *   - Tab 用 Editorial 下划线，而非药丸状的 bg-muted/50 rounded-xl 色块
 *   - icon 使用 lucide stroke-[1.5]
 */

import { type ReactNode, Fragment } from 'react'
import { icons, type IconName } from '@/lib/icons'
import { cn } from './utils'

export interface CenterTab {
  id: string
  label: string
  icon: IconName
  /** 英文 tracker（可选）—— 用于 micro UPPERCASE 显示 */
  labelEn?: string
}

interface CenterLayoutProps {
  /** 页面标题 */
  title: string
  /** 描述（可选） */
  description?: string
  /** Tab 定义 */
  tabs: CenterTab[]
  /** 当前激活的 Tab id */
  activeTab: string
  /** Tab 切换回调 */
  onTabChange: (tabId: string) => void
  /** 右侧操作区 */
  actions?: ReactNode
  /** Tracker（micro UPPERCASE 面包屑），默认 ['Center', title] */
  tracker?: string[]
  /** 内容区 */
  children: ReactNode
}

export function CenterLayout({
  title,
  description,
  tabs,
  activeTab,
  onTabChange,
  actions,
  tracker,
  children,
}: CenterLayoutProps) {
  const finalTracker = tracker ?? ['Center', title]
  return (
    <div className="h-full flex flex-col bg-background">
      {/* Editorial Header（serif H1 + tracker，无独立 border） */}
      <header
        data-ui="center-layout-header"
        className="shrink-0 px-6 sm:px-8 lg:px-12 xl:px-16 pt-8 lg:pt-10 pb-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
      >
        <div className="min-w-0 flex-1">
          {finalTracker.length > 0 && (
            <div
              data-ui="editorial-tracker"
              className="mb-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground"
            >
              {finalTracker.map((seg, i) => (
                <Fragment key={i}>
                  {i > 0 && <span className="text-foreground/30 mx-1.5" aria-hidden>·</span>}
                  <span className={i === finalTracker.length - 1 ? 'text-foreground/70 normal-case tracking-normal' : ''}>
                    {seg}
                  </span>
                </Fragment>
              ))}
            </div>
          )}
          <h1 className="font-serif text-[28px] sm:text-[32px] leading-[1.2] tracking-[-0.02em] font-medium text-foreground">
            {title}
          </h1>
          {description && (
            <p className="mt-2 text-[14px] leading-[1.6] text-foreground/70 max-w-[60ch]">{description}</p>
          )}
        </div>
        {actions && (
          <div data-ui="center-layout-actions" className="flex items-center gap-3 shrink-0">
            {actions}
          </div>
        )}
      </header>

      {/* Editorial 下划线 Tab */}
      <div className="shrink-0 border-b border-border">
        <div className="px-6 sm:px-8 lg:px-12 xl:px-16 overflow-x-auto">
          <nav className="flex items-end gap-8" role="tablist" aria-label={title}>
            {tabs.map((tab) => {
              const Icon = icons[tab.icon]
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => onTabChange(tab.id)}
                  className={cn(
                    'relative py-3 inline-flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.16em] transition-colors whitespace-nowrap outline-none focus-visible:text-foreground',
                    isActive
                      ? 'text-foreground after:absolute after:left-0 after:right-0 after:bottom-0 after:h-px after:bg-primary'
                      : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  {Icon && <Icon className="w-3.5 h-3.5 stroke-[1.5]" />}
                  {tab.labelEn && (
                    <>
                      <span>{tab.labelEn}</span>
                      <span className="text-foreground/30" aria-hidden>·</span>
                    </>
                  )}
                  <span className="normal-case tracking-normal">{tab.label}</span>
                </button>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}
