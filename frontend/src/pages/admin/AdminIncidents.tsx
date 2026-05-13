/**
 * [CREAO 自愈闭环 Slice 1] Admin · 事件中心
 *
 * 列出 GET /admin/incidents 返回的事件，支持 source / severity / status 筛选 + 分页 + 详情 modal。
 * 严格参照 AdminAudit.tsx 结构。
 */
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { icons } from '@/lib/icons'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'

const PAGE_SIZE = 20
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// 与契约保持一致的枚举
const SOURCE_OPTIONS = [
  { value: 'all', label: '全部来源' },
  { value: 'output_validator', label: '输出校验' },
  { value: 'agent_forum', label: 'Agent 论坛' },
  { value: 'low_rating', label: '低评分' },
  { value: 'api_5xx', label: 'API 5xx' },
  { value: 'frontend_error', label: '前端错误' },
] as const

const SEVERITY_OPTIONS = [
  { value: 'all', label: '全部级别' },
  { value: 'P0', label: 'P0' },
  { value: 'P1', label: 'P1' },
  { value: 'P2', label: 'P2' },
  { value: 'P3', label: 'P3' },
] as const

const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'open', label: '待处理' },
  { value: 'triaged', label: '已分诊' },
  { value: 'linked', label: '已关联' },
  { value: 'resolved', label: '已解决' },
  { value: 'dismissed', label: '已忽略' },
] as const

type IncidentSource =
  | 'output_validator'
  | 'agent_forum'
  | 'low_rating'
  | 'api_5xx'
  | 'frontend_error'

type IncidentSeverity = 'P0' | 'P1' | 'P2' | 'P3'

type IncidentStatus =
  | 'open'
  | 'triaged'
  | 'linked'
  | 'resolved'
  | 'dismissed'

interface Incident {
  id: string
  source: IncidentSource
  severity: IncidentSeverity
  title: string
  status: IncidentStatus
  occurrence_count: number
  first_seen_at: string
  last_seen_at: string
  agent_name?: string | null
  route?: string | null
  trace_id?: string | null
  github_issue_url?: string | null
  // 详情可能携带的额外字段（payload）
  [key: string]: unknown
}

interface ListResp {
  items: Incident[]
  total: number
  page: number
  page_size: number
}

const SOURCE_LABEL: Record<string, string> = {
  output_validator: '输出校验',
  agent_forum: 'Agent 论坛',
  low_rating: '低评分',
  api_5xx: 'API 5xx',
  frontend_error: '前端错误',
}

const STATUS_LABEL: Record<string, string> = {
  open: '待处理',
  triaged: '已分诊',
  linked: '已关联',
  resolved: '已解决',
  dismissed: '已忽略',
}

/** Severity Badge：P0 红 / P1 橙 / P2 黄 / P3 灰 */
function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    P0: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-500/15 dark:text-red-400 dark:border-red-500/30',
    P1: 'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-500/15 dark:text-orange-400 dark:border-orange-500/30',
    P2: 'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-500/15 dark:text-yellow-400 dark:border-yellow-500/30',
    P3: 'bg-muted text-muted-foreground border-border',
  }
  return (
    <Badge variant="outline" className={`text-xs font-mono ${map[severity] || map.P3}`}>
      {severity || '--'}
    </Badge>
  )
}

function SourceBadge({ source }: { source: string }) {
  return (
    <Badge variant="outline" className="text-xs">
      {SOURCE_LABEL[source] || source || '--'}
    </Badge>
  )
}

function StatusBadge({ status }: { status: string }) {
  const variant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
    open: 'destructive',
    triaged: 'default',
    linked: 'secondary',
    resolved: 'outline',
    dismissed: 'outline',
  }
  return (
    <Badge variant={variant[status] || 'outline'} className="text-xs">
      {STATUS_LABEL[status] || status || '--'}
    </Badge>
  )
}

export default function AdminIncidents() {
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<Incident[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1) // 后端契约 page 从 1 起
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selected, setSelected] = useState<Incident | null>(null)

  const loadList = useCallback(async () => {
    setLoading(true)
    try {
      const qs = new URLSearchParams()
      qs.set('page', String(page))
      qs.set('page_size', String(PAGE_SIZE))
      if (sourceFilter !== 'all') qs.set('source', sourceFilter)
      if (severityFilter !== 'all') qs.set('severity', severityFilter)
      if (statusFilter !== 'all') qs.set('status', statusFilter)

      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      try {
        const token = localStorage.getItem('access_token')
        if (token) headers['Authorization'] = `Bearer ${token}`
      } catch {
        /* ignore */
      }

      const resp = await fetch(`${API_BASE_URL}/admin/incidents?${qs.toString()}`, {
        headers,
      })
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      const json = await resp.json()
      // 兼容 UnifiedResponse {code,data,message} 与裸返回 {items,total,...}
      const body: ListResp =
        (json && typeof json === 'object' && 'data' in json && json.data
          ? (json.data as ListResp)
          : (json as ListResp)) ?? {
          items: [],
          total: 0,
          page: 1,
          page_size: PAGE_SIZE,
        }
      setItems(Array.isArray(body.items) ? body.items : [])
      setTotal(typeof body.total === 'number' ? body.total : 0)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '加载事件列表失败'
      toast.error(`加载事件列表失败：${msg}`)
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [page, sourceFilter, severityFilter, statusFilter])

  useEffect(() => {
    loadList()
  }, [loadList])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const formatJson = (data: unknown) => {
    try {
      return JSON.stringify(data, null, 2)
    } catch {
      return String(data)
    }
  }

  return (
    <PageContainer
      title="事件中心"
      description="汇集前端异常 / API 5xx / 校验失败 / 低评分等失败信号，自愈闭环 Slice 1"
      actions={
        <Button variant="outline" size="sm" onClick={loadList} className="gap-2">
          <icons.Refresh className="w-4 h-4" />
          刷新
        </Button>
      }
    >
      {/* 筛选栏 */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap items-center gap-3">
            <Select
              value={sourceFilter}
              onValueChange={(v) => {
                setSourceFilter(v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="来源" />
              </SelectTrigger>
              <SelectContent>
                {SOURCE_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={severityFilter}
              onValueChange={(v) => {
                setSeverityFilter(v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="级别" />
              </SelectTrigger>
              <SelectContent>
                {SEVERITY_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={statusFilter}
              onValueChange={(v) => {
                setStatusFilter(v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 事件表格 */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[170px]">最近发生</TableHead>
                  <TableHead className="w-[70px]">级别</TableHead>
                  <TableHead className="w-[110px]">来源</TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead className="w-[80px] text-right">次数</TableHead>
                  <TableHead className="w-[90px]">状态</TableHead>
                  <TableHead className="w-[140px]">Agent</TableHead>
                  <TableHead className="w-[100px]">GitHub</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length > 0 ? (
                  items.map((it) => (
                    <TableRow
                      key={it.id}
                      className="cursor-pointer"
                      onClick={() => setSelected(it)}
                    >
                      <TableCell className="text-muted-foreground text-xs font-mono">
                        {it.last_seen_at
                          ? new Date(it.last_seen_at).toLocaleString('zh-CN')
                          : '--'}
                      </TableCell>
                      <TableCell>
                        <SeverityBadge severity={it.severity} />
                      </TableCell>
                      <TableCell>
                        <SourceBadge source={it.source} />
                      </TableCell>
                      <TableCell className="text-sm max-w-[420px] truncate" title={it.title}>
                        {it.title || '--'}
                      </TableCell>
                      <TableCell className="text-sm font-mono text-right">
                        {it.occurrence_count ?? 1}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={it.status} />
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground truncate" title={it.agent_name ?? undefined}>
                        {it.agent_name || '--'}
                      </TableCell>
                      <TableCell>
                        {it.github_issue_url ? (
                          <a
                            href={it.github_issue_url}
                            target="_blank"
                            rel="noreferrer noopener"
                            onClick={(e) => e.stopPropagation()}
                            className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                          >
                            <icons.ExternalLink className="w-3 h-3" />
                            Issue
                          </a>
                        ) : (
                          <span className="text-xs text-muted-foreground">--</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-12">
                      暂无事件
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            共 {total} 条，第 {page}/{totalPages} 页
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              上一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* 详情 Dialog */}
      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <SeverityBadge severity={selected?.severity || 'P3'} />
              <span className="truncate">{selected?.title || '事件详情'}</span>
            </DialogTitle>
            <DialogDescription>
              ID：<span className="font-mono">{selected?.id}</span>
            </DialogDescription>
          </DialogHeader>

          {selected && (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <Field label="来源">
                  <SourceBadge source={selected.source} />
                </Field>
                <Field label="状态">
                  <StatusBadge status={selected.status} />
                </Field>
                <Field label="发生次数">{selected.occurrence_count ?? 1}</Field>
                <Field label="Agent">{selected.agent_name || '--'}</Field>
                <Field label="路由">
                  <code className="text-xs">{selected.route || '--'}</code>
                </Field>
                <Field label="Trace ID">
                  <code className="text-xs break-all">{selected.trace_id || '--'}</code>
                </Field>
                <Field label="首次发生">
                  {selected.first_seen_at
                    ? new Date(selected.first_seen_at).toLocaleString('zh-CN')
                    : '--'}
                </Field>
                <Field label="最近发生">
                  {selected.last_seen_at
                    ? new Date(selected.last_seen_at).toLocaleString('zh-CN')
                    : '--'}
                </Field>
                {selected.github_issue_url && (
                  <Field label="GitHub Issue">
                    <a
                      href={selected.github_issue_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-primary hover:underline inline-flex items-center gap-1 text-xs"
                    >
                      <icons.ExternalLink className="w-3 h-3" />
                      {selected.github_issue_url}
                    </a>
                  </Field>
                )}
              </div>

              <div>
                <p className="text-xs text-muted-foreground mb-1">完整 Payload</p>
                <pre className="text-xs bg-muted p-3 rounded-lg overflow-auto max-h-[40vh] font-mono">
                  {formatJson(selected)}
                </pre>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </PageContainer>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <div className="text-sm">{children}</div>
    </div>
  )
}
