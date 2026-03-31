/**
 * TimesheetTable - 工时周视图组件
 *
 * - 顶部: 日期选择器（周切换） + "提交选中" / "全部提交" 按钮
 * - 表格: 行=案件/项目, 列=周一~周日, 单元格=小时数（可编辑）
 * - 底部: 本周总计、可计费总计
 * - 状态标识: draft(灰), submitted(蓝), approved(绿), rejected(红)
 * - 支持新增工时条目 Dialog
 * 全部 mock 数据
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { icons } from '@/lib/icons'
import { Skeleton } from '@/components/ui/skeleton'
import { iconSize, heading, statusBadge, cardStyle } from '@/lib/design-tokens'
import { firmApi } from '@/lib/api'

// ========== 类型 ==========

type EntryStatus = 'draft' | 'submitted' | 'approved' | 'rejected'

interface TimesheetRow {
  id: string
  caseName: string
  caseId: string
  billable: boolean
  status: EntryStatus
  /** 周一~周日的小时数 */
  hours: number[]
}

// ========== 工具函数 ==========

function getWeekDates(offset: number): Date[] {
  const now = new Date()
  const day = now.getDay()
  const monday = new Date(now)
  monday.setDate(now.getDate() - (day === 0 ? 6 : day - 1) + offset * 7)

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return d
  })
}

function formatShortDate(d: Date): string {
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatWeekRange(dates: Date[]): string {
  const first = dates[0]
  const last = dates[6]
  return `${first.getFullYear()}/${first.getMonth() + 1}/${first.getDate()} - ${last.getMonth() + 1}/${last.getDate()}`
}

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const STATUS_MAP: Record<EntryStatus, { label: string; badge: string }> = {
  draft: { label: '草稿', badge: statusBadge.neutral },
  submitted: { label: '已提交', badge: statusBadge.info },
  approved: { label: '已审批', badge: statusBadge.success },
  rejected: { label: '已拒绝', badge: statusBadge.error },
}

// 数据从 API 加载

// ========== 组件 ==========

export default function TimesheetTable() {
  const [weekOffset, setWeekOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<TimesheetRow[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [newCaseName, setNewCaseName] = useState('')

  const weekDates = useMemo(() => getWeekDates(weekOffset), [weekOffset])

  const fetchTimesheet = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const dates = getWeekDates(weekOffset)
      const startDate = dates[0].toISOString().split('T')[0]
      const endDate = dates[6].toISOString().split('T')[0]
      const data = await firmApi.listTimesheet({ start_date: startDate, end_date: endDate })
      // 适配后端返回数据：可能是数组或 { items: [] }
      const items = Array.isArray(data) ? data : (data.items ?? [])
      setRows(
        items.map((entry: any, idx: number) => ({
          id: entry.id ?? `entry-${idx}`,
          caseName: entry.case_name ?? entry.caseName ?? entry.description ?? '',
          caseId: entry.case_id ?? entry.caseId ?? '',
          billable: entry.billable ?? true,
          status: entry.status ?? 'draft',
          hours: entry.hours ?? entry.daily_hours ?? [0, 0, 0, 0, 0, 0, 0],
        }))
      )
    } catch (err: any) {
      setError(err.message || '加载工时数据失败')
    } finally {
      setLoading(false)
    }
  }, [weekOffset])

  useEffect(() => {
    fetchTimesheet()
  }, [fetchTimesheet])

  const totals = useMemo(() => {
    let total = 0
    let billable = 0
    rows.forEach(r => {
      const sum = r.hours.reduce((a, b) => a + b, 0)
      total += sum
      if (r.billable) billable += sum
    })
    return { total: Math.round(total * 10) / 10, billable: Math.round(billable * 10) / 10 }
  }, [rows])

  const handleToggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSelectAll = () => {
    const draftIds = rows.filter(r => r.status === 'draft').map(r => r.id)
    if (draftIds.every(id => selectedIds.has(id))) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(draftIds))
    }
  }

  const handleSubmitSelected = () => {
    setRows(prev =>
      prev.map(r =>
        selectedIds.has(r.id) && r.status === 'draft' ? { ...r, status: 'submitted' as const } : r,
      ),
    )
    setSelectedIds(new Set())
  }

  const handleSubmitAll = () => {
    setRows(prev => prev.map(r => (r.status === 'draft' ? { ...r, status: 'submitted' as const } : r)))
    setSelectedIds(new Set())
  }

  const handleCellChange = (rowId: string, dayIndex: number, value: string) => {
    const num = parseFloat(value) || 0
    setRows(prev =>
      prev.map(r => {
        if (r.id !== rowId || r.status !== 'draft') return r
        const newHours = [...r.hours]
        newHours[dayIndex] = num
        return { ...r, hours: newHours }
      }),
    )
  }

  const handleAddRow = () => {
    if (!newCaseName.trim()) return
    const newRow: TimesheetRow = {
      id: `new-${Date.now()}`,
      caseName: newCaseName,
      caseId: 'NEW',
      billable: true,
      status: 'draft',
      hours: [0, 0, 0, 0, 0, 0, 0],
    }
    setRows(prev => [...prev, newRow])
    setNewCaseName('')
    setAddDialogOpen(false)
  }

  return (
    <div className="space-y-4">
      {/* 顶部工具栏 */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        {/* 周切换 */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setWeekOffset(w => w - 1)}>
            <icons.ChevronLeft className={iconSize.sm} />
          </Button>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-muted rounded-lg text-sm font-medium text-foreground">
            <icons.Calendar className={iconSize.sm} />
            {formatWeekRange(weekDates)}
          </div>
          <Button variant="outline" size="icon" onClick={() => setWeekOffset(w => w + 1)}>
            <icons.ChevronRight className={iconSize.sm} />
          </Button>
          {weekOffset !== 0 && (
            <Button variant="ghost" size="sm" onClick={() => setWeekOffset(0)}>
              本周
            </Button>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setAddDialogOpen(true)}>
            <icons.Plus className={iconSize.sm} />
            新增条目
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={selectedIds.size === 0}
            onClick={handleSubmitSelected}
          >
            提交选中 ({selectedIds.size})
          </Button>
          <Button size="sm" onClick={handleSubmitAll}>
            全部提交
          </Button>
        </div>
      </div>

      {/* 工时表格 */}
      {loading ? (
        <div className={`${cardStyle.base} space-y-3`}>
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className={`${cardStyle.base} flex flex-col items-center justify-center py-12`}>
          <icons.AlertTriangle className={`${iconSize.xl} text-destructive/60 mb-2`} />
          <p className="text-sm text-muted-foreground mb-3">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchTimesheet}>
            重试
          </Button>
        </div>
      ) : rows.length === 0 ? (
        <div className={`${cardStyle.base} text-center py-12`}>
          <icons.Clock className={`${iconSize.xl} text-muted-foreground/40 mx-auto mb-2`} />
          <p className="text-sm text-muted-foreground">本周暂无工时记录</p>
        </div>
      ) : (
      <div className={`${cardStyle.base} overflow-x-auto`}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={
                    rows.filter(r => r.status === 'draft').length > 0 &&
                    rows.filter(r => r.status === 'draft').every(r => selectedIds.has(r.id))
                  }
                  onCheckedChange={handleSelectAll}
                />
              </TableHead>
              <TableHead className="min-w-[200px]">案件/项目</TableHead>
              <TableHead className="w-20 text-center">状态</TableHead>
              {weekDates.map((d, i) => (
                <TableHead key={i} className="w-20 text-center">
                  <div className="text-xs">{DAY_LABELS[i]}</div>
                  <div className="text-[10px] text-muted-foreground">{formatShortDate(d)}</div>
                </TableHead>
              ))}
              <TableHead className="w-20 text-center font-semibold">合计</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(row => {
              const rowTotal = row.hours.reduce((a, b) => a + b, 0)
              const statusInfo = STATUS_MAP[row.status]
              return (
                <TableRow key={row.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(row.id)}
                      disabled={row.status !== 'draft'}
                      onCheckedChange={() => handleToggleSelect(row.id)}
                    />
                  </TableCell>
                  <TableCell>
                    <div>
                      <span className="text-sm font-medium text-foreground">{row.caseName}</span>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] text-muted-foreground">{row.caseId}</span>
                        {!row.billable && (
                          <Badge variant="outline" className="text-[10px] px-1 py-0">
                            不可计费
                          </Badge>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${statusInfo.badge}`}>
                      {statusInfo.label}
                    </Badge>
                  </TableCell>
                  {row.hours.map((h, i) => (
                    <TableCell key={i} className="text-center p-1">
                      {row.status === 'draft' ? (
                        <input
                          type="number"
                          step="0.5"
                          min="0"
                          max="24"
                          value={h || ''}
                          onChange={e => handleCellChange(row.id, i, e.target.value)}
                          className="w-14 h-8 text-center text-sm border border-border rounded-md bg-background focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/10"
                          placeholder="0"
                        />
                      ) : (
                        <span className={`text-sm ${h > 0 ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                          {h > 0 ? h : '-'}
                        </span>
                      )}
                    </TableCell>
                  ))}
                  <TableCell className="text-center">
                    <span className="text-sm font-semibold text-foreground">
                      {Math.round(rowTotal * 10) / 10}h
                    </span>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
      )}

      {/* 底部汇总 */}
      <div className="flex items-center gap-6">
        <div className={`${cardStyle.compact} flex items-center gap-2`}>
          <icons.Clock className={`${iconSize.sm} text-muted-foreground`} />
          <span className={heading.muted}>本周总计</span>
          <span className="text-lg font-bold text-foreground">{totals.total}h</span>
        </div>
        <div className={`${cardStyle.compact} flex items-center gap-2`}>
          <icons.DollarSign className={`${iconSize.sm} text-emerald-600 dark:text-emerald-400`} />
          <span className={heading.muted}>可计费</span>
          <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{totals.billable}h</span>
        </div>
      </div>

      {/* 新增条目 Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新增工时条目</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="entry-case">案件/项目名称</Label>
              <Input
                id="entry-case"
                value={newCaseName}
                onChange={e => setNewCaseName(e.target.value)}
                placeholder="输入案件或项目名称"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleAddRow} disabled={!newCaseName.trim()}>
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
