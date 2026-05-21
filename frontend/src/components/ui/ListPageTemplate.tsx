/**
 * ListPageTemplate — V3 Editorial Luxury 列表页统一模板
 *
 * 用于：Cases / Contracts / FindLawyer / Leads / Documents / KnowledgeBase 等 15+ 页面
 *
 * 提供：
 *   - 头部（tracker + serif H1 + description + actions）
 *   - Toolbar（tabs + search + filter） — 可选
 *   - 列表区（item 渲染 + empty/loading/error 状态）
 *   - 分页 footer — 可选
 *   - 内置 ScrollArea + sticky toolbar
 *
 * 用法：
 *   <ListPageTemplate
 *     tracker={["Legal", "案件中心"]}
 *     title="案件中心"
 *     description="案件全生命周期 · 团队协作"
 *     actions={<NewItemButton />}
 *     tabs={[{ key: 'all', label: '全部', count: 142 }, ...]}
 *     activeTab={status}
 *     onTabChange={setStatus}
 *     search={<SearchInput .../>}
 *     loading={loading}
 *     error={error}
 *     empty={items.length === 0 && !loading}
 *     emptyState={<EmptyState .../>}
 *     pagination={<Pagination .../>}
 *   >
 *     {items.map(item => <CaseRow key={item.id} {...item} />)}
 *   </ListPageTemplate>
 *
 * 设计约束：
 *   - 列表 item 应自己用 `border-b border-border/60 py-4` hairline 分隔，不用卡片
 *   - Toolbar 与 header 之间留呼吸感（mb-8）
 *   - Empty/Loading/Error 状态走 Editorial 风格：micro tracker + serif H3 + body caption
 */

import * as React from 'react'
import { EditorialPageHeader, type EditorialPageHeaderProps } from './EditorialPageHeader'
import { ScrollArea } from './scroll-area'
import { cn } from './utils'

export interface ListPageTabConfig {
  key: string
  label: string
  /** 数量徽标（可选）— 显示为右侧灰色数字 */
  count?: number
}

export interface ListPageTemplateProps {
  // === 头部 ===
  tracker?: EditorialPageHeaderProps['tracker']
  title: string
  description?: string
  actions?: React.ReactNode
  headerSize?: EditorialPageHeaderProps['size']

  // === Toolbar ===
  /** 状态/筛选 tabs（Editorial underline 风格） */
  tabs?: ReadonlyArray<ListPageTabConfig>
  activeTab?: string
  onTabChange?: (key: string) => void
  /** Toolbar 右侧元素（搜索框 / 排序 / filter）*/
  toolbarRight?: React.ReactNode

  // === 主体（列表区）===
  /** 列表 items —— 调用方自己渲染（应使用 hairline 分隔，非卡片）*/
  children: React.ReactNode
  /** 加载态 */
  loading?: boolean
  /** 错误信息（字符串）*/
  error?: string | null
  /** 空状态布尔（同时给 emptyState 元素即生效）*/
  empty?: boolean
  /** 空状态渲染（推荐：serif H3 + caption + 可选 CTA）*/
  emptyState?: React.ReactNode

  // === 底部 ===
  /** 分页 / 计数 footer */
  pagination?: React.ReactNode

  // === 容器 ===
  /** 是否走 ScrollArea 包裹（默认 true）*/
  scrollable?: boolean
  /** 容器最大宽度（默认 1400 — 与 Login/DomainHomePage 一致）*/
  maxWidth?: string
  className?: string
}

export function ListPageTemplate({
  tracker,
  title,
  description,
  actions,
  headerSize = 'h1',
  tabs,
  activeTab,
  onTabChange,
  toolbarRight,
  children,
  loading,
  error,
  empty,
  emptyState,
  pagination,
  scrollable = true,
  maxWidth = '1400px',
  className,
}: ListPageTemplateProps) {
  const inner = (
    <div
      data-ui="list-page"
      className={cn('mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-12', className)}
      style={{ maxWidth }}
    >
      <EditorialPageHeader
        tracker={tracker}
        title={title}
        description={description}
        actions={actions}
        size={headerSize}
      />

      {(tabs || toolbarRight) && (
        <div
          data-ui="list-page-toolbar"
          className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8"
        >
          {tabs && (
            <nav className="flex items-center gap-1 -ml-2" aria-label="筛选">
              {tabs.map((t) => {
                const isActive = activeTab === t.key
                return (
                  <button
                    key={t.key}
                    onClick={() => onTabChange?.(t.key)}
                    aria-current={isActive ? 'page' : undefined}
                    className={cn(
                      'relative px-3 py-1.5 text-[13px] transition-colors',
                      isActive ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
                    )}
                  >
                    <span>{t.label}</span>
                    {typeof t.count === 'number' && (
                      <span className="ml-1.5 text-muted-foreground">{t.count}</span>
                    )}
                    {isActive && (
                      <span aria-hidden className="absolute left-3 right-3 -bottom-px h-px bg-primary" />
                    )}
                  </button>
                )
              })}
            </nav>
          )}
          {toolbarRight && (
            <div data-ui="list-page-toolbar-right" className="flex items-center gap-3">
              {toolbarRight}
            </div>
          )}
        </div>
      )}

      <div data-ui="list-page-body">
        {loading && !error && !empty && (
          <ListPageStatus
            tracker="Loading"
            title="正在加载"
            description="正在拉取列表数据…"
          />
        )}
        {error && (
          <ListPageStatus
            tracker="Error"
            title="加载失败"
            description={error}
            tone="error"
          />
        )}
        {empty && !loading && !error && (
          emptyState ?? (
            <ListPageStatus
              tracker="Empty"
              title="暂无数据"
              description="目前还没有匹配的条目。"
            />
          )
        )}
        {!loading && !error && !empty && (
          <ol data-ui="list-page-items" className="space-y-px">{children}</ol>
        )}
      </div>

      {pagination && (
        <footer
          data-ui="list-page-footer"
          className="mt-12 pt-6 border-t border-border flex items-center justify-between text-[13px] text-muted-foreground"
        >
          {pagination}
        </footer>
      )}
    </div>
  )

  if (!scrollable) {
    return <div className="h-full overflow-hidden">{inner}</div>
  }

  return <ScrollArea className="h-full">{inner}</ScrollArea>
}

/**
 * ListPageStatus — 列表页的空/加载/错误状态（Editorial 风格）
 *
 * 也可作为独立组件给业务自定义 emptyState 使用。
 */
export interface ListPageStatusProps {
  tracker: string
  title: string
  description?: string
  /** 'normal' 默认 · 'error' 红墨色调 */
  tone?: 'normal' | 'error'
  /** 可选 CTA 按钮 */
  action?: React.ReactNode
}

export function ListPageStatus({
  tracker,
  title,
  description,
  tone = 'normal',
  action,
}: ListPageStatusProps) {
  return (
    <div
      data-ui="list-page-status"
      className="flex flex-col items-center text-center py-20 px-6"
    >
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-3">
        {tracker}
      </div>
      <h3
        className={cn(
          'font-serif text-[24px] leading-[1.3] tracking-[-0.01em] font-medium',
          tone === 'error' ? 'text-destructive' : 'text-foreground',
        )}
      >
        {title}
      </h3>
      {description && (
        <p className="mt-3 text-[14px] text-foreground/70 max-w-[40ch]">{description}</p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}

/**
 * ListPageRow — 标准列表项（Editorial hairline 风格）
 *
 * 用于：合同/案件/线索等任意条目。提供：
 *   - 序号（serif tabular-nums）
 *   - 主体（title 衬线 + meta caption）
 *   - 右侧标签 + 进入 → 图标
 *
 * 用法：
 *   <ListPageRow
 *     index="001"
 *     title="深圳某科技公司 · 设备采购协议"
 *     trackerRight="RC-2026-0518-003"
 *     metaItems={[
 *       { icon: 'user', label: '李霁明' },
 *       { icon: 'clock', label: '4 小时前' },
 *     ]}
 *     status={{ label: '高风险 · 3', tone: 'error' }}
 *     onClick={() => router.push('/cases/123')}
 *   />
 */
export interface ListPageRowMeta {
  /** 可选 lucide 图标名称（Caller 自行 import 并传 ReactNode）*/
  icon?: React.ReactNode
  label: string
}

export interface ListPageRowProps {
  /** 序号或编号 — serif tabular-nums */
  index?: string
  /** 标题（默认衬线 H3 18px）*/
  title: string
  /** 标题右侧的 RC 编号等 micro tracker 文本 */
  trackerRight?: string
  /** 元信息 chip 序列 */
  metaItems?: ReadonlyArray<ListPageRowMeta>
  /** 右侧状态信息（如风险等级）*/
  status?: {
    label: string
    sub?: string
    tone?: 'normal' | 'success' | 'warning' | 'error'
  }
  onClick?: () => void
  /** 整行 link 路径（与 onClick 二选一）*/
  href?: string
  /** 自定义 className */
  className?: string
}

export function ListPageRow({
  index,
  title,
  trackerRight,
  metaItems,
  status,
  onClick,
  href,
  className,
}: ListPageRowProps) {
  const statusToneClass = {
    normal: 'text-muted-foreground',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-destructive',
  }[status?.tone ?? 'normal']

  const inner = (
    <>
      {index && (
        <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 pt-1 tabular-nums">
          {index}
        </span>
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h3 className="font-serif text-[18px] leading-tight text-foreground">{title}</h3>
          {trackerRight && (
            <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              {trackerRight}
            </span>
          )}
        </div>
        {metaItems && metaItems.length > 0 && (
          <div className="text-[13px] text-muted-foreground mt-2 flex items-center gap-4 flex-wrap">
            {metaItems.map((m, i) => (
              <span key={i} className="inline-flex items-center gap-1.5">
                {m.icon}
                <span>{m.label}</span>
              </span>
            ))}
          </div>
        )}
      </div>
      {status && (
        <div className="text-right shrink-0">
          <div className={cn('text-[11px] font-medium uppercase tracking-[0.16em]', statusToneClass)}>
            {status.label}
          </div>
          {status.sub && (
            <div className="text-[13px] text-muted-foreground mt-0.5">{status.sub}</div>
          )}
        </div>
      )}
    </>
  )

  const liClass = cn(
    'group flex items-start gap-6 py-6 px-3 -mx-3 border-b border-border/60',
    'transition-colors hover:bg-surface-2/40',
    className,
  )

  if (href) {
    return (
      <li>
        <a href={href} className={liClass}>
          {inner}
        </a>
      </li>
    )
  }

  if (onClick) {
    return (
      <li>
        <button type="button" onClick={onClick} className={cn(liClass, 'w-full text-left')}>
          {inner}
        </button>
      </li>
    )
  }

  return <li className={liClass}>{inner}</li>
}
