/**
 * AdminTableTemplate — V3 Editorial Luxury 后台表格页统一模板
 *
 * 用于：AdminBilling / AdminConfig / AdminFeatureFlags / AdminUsers / AdminEnterprise 等 12+ 后台页
 *
 * 与 ListPageTemplate 的区别：
 *   - 表格优先（密集数据），用 <table> 而非 <ol>
 *   - 内置筛选条 / 批量操作栏 / 行内操作
 *   - 表头 sticky，行 hover 微底
 *   - 行间用 1px hairline，不用斑马纹（Editorial 克制）
 */

import * as React from 'react'
import { EditorialPageHeader, type EditorialPageHeaderProps } from './EditorialPageHeader'
import { ScrollArea } from './scroll-area'
import { cn } from './utils'

export interface AdminTableColumn<T> {
  key: string
  /** 表头标签（默认 sans 13px） — 若给 ReactNode 则原样渲染 */
  header: React.ReactNode
  /** 行渲染函数 */
  render: (row: T, index: number) => React.ReactNode
  /** 列宽（CSS 值如 '180px' / '20%'）*/
  width?: string
  /** 列对齐 */
  align?: 'left' | 'right' | 'center'
  /** 是否右对齐数字（自动 tabular-nums）*/
  numeric?: boolean
  /** sticky 列（一般首列 + 末列 actions）*/
  sticky?: 'left' | 'right'
  /** 单元格自定义 className */
  cellClassName?: string
}

export interface AdminTableTemplateProps<T> {
  // 头部
  tracker?: EditorialPageHeaderProps['tracker']
  title: string
  description?: string
  actions?: React.ReactNode

  // 顶部 toolbar
  /** 左侧（搜索 / 状态筛选）*/
  toolbarLeft?: React.ReactNode
  /** 右侧（视图切换 / 排序 / 导出）*/
  toolbarRight?: React.ReactNode

  // 表格
  columns: ReadonlyArray<AdminTableColumn<T>>
  rows: ReadonlyArray<T>
  /** 行 key 提取 */
  rowKey: (row: T, index: number) => string
  /** 行点击（可选）*/
  onRowClick?: (row: T) => void
  /** 行 hover 时是否高亮（默认 true）*/
  rowHover?: boolean

  // 批量选择（可选）
  selection?: {
    selected: ReadonlySet<string>
    onChange: (ids: ReadonlySet<string>) => void
    /** 批量操作 toolbar — selected.size > 0 时显示 */
    batchActions?: React.ReactNode
  }

  // 状态
  loading?: boolean
  empty?: boolean
  emptyMessage?: string
  error?: string | null

  // 底部
  pagination?: React.ReactNode

  // 容器
  scrollable?: boolean
  maxWidth?: string
  className?: string
}

export function AdminTableTemplate<T>({
  tracker,
  title,
  description,
  actions,
  toolbarLeft,
  toolbarRight,
  columns,
  rows,
  rowKey,
  onRowClick,
  rowHover = true,
  selection,
  loading,
  empty,
  emptyMessage = '暂无数据',
  error,
  pagination,
  scrollable = true,
  maxWidth = '1600px',
  className,
}: AdminTableTemplateProps<T>) {
  const hasSelection = !!selection
  const allSelected = hasSelection && rows.length > 0 && rows.every((r, i) => selection.selected.has(rowKey(r, i)))
  const someSelected = hasSelection && rows.some((r, i) => selection.selected.has(rowKey(r, i))) && !allSelected

  function toggleAll() {
    if (!selection) return
    if (allSelected) {
      selection.onChange(new Set())
    } else {
      selection.onChange(new Set(rows.map((r, i) => rowKey(r, i))))
    }
  }

  function toggleRow(id: string) {
    if (!selection) return
    const next = new Set(selection.selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    selection.onChange(next)
  }

  const inner = (
    <div
      data-ui="admin-table-page"
      className={cn('mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-12', className)}
      style={{ maxWidth }}
    >
      <EditorialPageHeader tracker={tracker} title={title} description={description} actions={actions} />

      {(toolbarLeft || toolbarRight) && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div className="flex items-center gap-3 flex-wrap">{toolbarLeft}</div>
          <div className="flex items-center gap-3">{toolbarRight}</div>
        </div>
      )}

      {selection && selection.selected.size > 0 && selection.batchActions && (
        <div
          data-ui="admin-table-batch-bar"
          className="mb-4 border border-border bg-primary-50 px-4 py-3 flex items-center justify-between gap-3 text-[13px]"
        >
          <span className="text-foreground/80">
            已选择 <span className="font-medium text-foreground tabular-nums">{selection.selected.size}</span> 项
          </span>
          <div className="flex items-center gap-2">{selection.batchActions}</div>
        </div>
      )}

      {error ? (
        <div className="border border-destructive/40 bg-destructive/5 px-6 py-12 text-center">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-destructive mb-2">ERROR</div>
          <div className="text-[18px] font-medium text-destructive">加载失败</div>
          <p className="text-[14px] text-muted-foreground mt-2">{error}</p>
        </div>
      ) : loading ? (
        <div className="border border-border px-6 py-20 text-center">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">Loading</div>
          <div className="text-[18px] font-medium text-foreground">正在加载</div>
        </div>
      ) : empty || rows.length === 0 ? (
        <div className="border border-border px-6 py-20 text-center">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">Empty</div>
          <div className="text-[18px] font-medium text-foreground">{emptyMessage}</div>
        </div>
      ) : (
        <div data-ui="admin-table-wrapper" className="overflow-x-auto border border-border">
          <table className="w-full text-[14px] border-collapse">
            <thead className="bg-surface-2 text-[12px] uppercase tracking-[0.08em] text-muted-foreground">
              <tr className="border-b border-border">
                {hasSelection && (
                  <th className="w-10 px-3 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      ref={(el) => { if (el) el.indeterminate = someSelected }}
                      onChange={toggleAll}
                      aria-label="全选"
                      className="cursor-pointer"
                    />
                  </th>
                )}
                {columns.map((col) => (
                  <th
                    key={col.key}
                    style={{ width: col.width, textAlign: col.align ?? (col.numeric ? 'right' : 'left') }}
                    className={cn(
                      'px-4 py-3 font-medium',
                      col.sticky === 'left' && 'sticky left-0 bg-surface-2 z-[1]',
                      col.sticky === 'right' && 'sticky right-0 bg-surface-2 z-[1]',
                    )}
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                const id = rowKey(row, i)
                const isSelected = hasSelection && selection.selected.has(id)
                return (
                  <tr
                    key={id}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={cn(
                      'border-b border-border/60 transition-colors',
                      rowHover && 'hover:bg-surface-2/40',
                      onRowClick && 'cursor-pointer',
                      isSelected && 'bg-primary-50',
                    )}
                  >
                    {hasSelection && (
                      <td
                        className="w-10 px-3 py-3"
                        onClick={(e) => { e.stopPropagation(); toggleRow(id) }}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleRow(id)}
                          aria-label={`选择第 ${i + 1} 行`}
                          className="cursor-pointer"
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        style={{ textAlign: col.align ?? (col.numeric ? 'right' : 'left') }}
                        className={cn(
                          'px-4 py-3 align-middle',
                          col.numeric && 'tabular-nums',
                          col.sticky === 'left' && 'sticky left-0 bg-card z-[1]',
                          col.sticky === 'right' && 'sticky right-0 bg-card z-[1]',
                          col.cellClassName,
                        )}
                      >
                        {col.render(row, i)}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {pagination && (
        <footer className="mt-6 pt-4 border-t border-border flex items-center justify-between text-[13px] text-muted-foreground">
          {pagination}
        </footer>
      )}
    </div>
  )

  if (!scrollable) return <div className="h-full overflow-hidden">{inner}</div>
  return <ScrollArea className="h-full">{inner}</ScrollArea>
}
