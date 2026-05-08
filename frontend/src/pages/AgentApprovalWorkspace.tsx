import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { PageContainer } from '@/components/ui/PageContainer'
import {
  agentApprovalsApi,
  type AgentApprovalAuditExport,
  type AgentApprovalAuditEvent,
  type AgentApprovalItem,
  type AgentApprovalStatus,
} from '@/lib/api'
import { icons, type IconComponent } from '@/lib/icons'

type FilterStatus = 'all' | AgentApprovalStatus

const STATUS_FILTERS: Array<{ value: FilterStatus; label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待审批' },
  { value: 'approved', label: '已批准' },
  { value: 'rejected', label: '已驳回' },
  { value: 'revoked', label: '已撤销' },
  { value: 'expired', label: '已过期' },
]

const STATUS_META: Record<AgentApprovalStatus, { label: string; className: string; icon: IconComponent }> = {
  pending: { label: '待审批', className: 'border-amber-200 bg-amber-50 text-amber-700', icon: icons.Clock },
  approved: { label: '已批准', className: 'border-emerald-200 bg-emerald-50 text-emerald-700', icon: icons.CheckCircle2 },
  rejected: { label: '已驳回', className: 'border-destructive/20 bg-destructive/5 text-destructive', icon: icons.XCircle },
  revoked: { label: '已撤销', className: 'border-muted bg-muted text-muted-foreground', icon: icons.Ban },
  expired: { label: '已过期', className: 'border-muted bg-muted text-muted-foreground', icon: icons.AlertCircle },
}

function formatDateTime(value?: string | null): string {
  if (!value) return '未设置'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '无效时间'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatActionType(value: string): string {
  return value
    .split('.')
    .filter(Boolean)
    .map((part) => part.replace(/_/g, ' '))
    .join(' / ')
}

function shortId(value?: string | null): string {
  if (!value) return '未绑定'
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value
}

function payloadPreview(payload?: Record<string, unknown> | null): Array<[string, string]> {
  if (!payload) return []
  return Object.entries(payload)
    .slice(0, 4)
    .map(([key, value]) => [key, typeof value === 'string' ? value : JSON.stringify(value)])
}

function safeFileSegment(value: string): string {
  return value.replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'approval'
}

function downloadAuditArtifact(approvalId: string, artifact: AgentApprovalAuditExport): void {
  const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `agent-approval-${safeFileSegment(approvalId)}-audit.json`
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

export default function AgentApprovalWorkspace() {
  const [items, setItems] = useState<AgentApprovalItem[]>([])
  const [status, setStatus] = useState<FilterStatus>('pending')
  const [pendingCount, setPendingCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [auditEventsById, setAuditEventsById] = useState<Record<string, AgentApprovalAuditEvent[]>>({})
  const [auditLoadingId, setAuditLoadingId] = useState<string | null>(null)
  const [expandedAuditId, setExpandedAuditId] = useState<string | null>(null)
  const [exportingAuditId, setExportingAuditId] = useState<string | null>(null)

  const loadApprovals = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [list, count] = await Promise.all([
        agentApprovalsApi.list({
          status: status === 'all' ? undefined : status,
          page_size: 50,
        }),
        agentApprovalsApi.pendingCount(),
      ])
      setItems(list.items)
      setPendingCount(count.pending)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载审批失败')
    } finally {
      setLoading(false)
    }
  }, [status])

  useEffect(() => {
    void loadApprovals()
  }, [loadApprovals])

  const stats = useMemo(() => {
    const base: Record<AgentApprovalStatus, number> = {
      pending: 0,
      approved: 0,
      rejected: 0,
      revoked: 0,
      expired: 0,
    }
    for (const item of items) {
      base[item.status] = (base[item.status] ?? 0) + 1
    }
    return base
  }, [items])

  const decide = async (item: AgentApprovalItem, action: 'approve' | 'reject' | 'revoke') => {
    if (action === 'revoke' && !window.confirm('确认撤销该高风险审批？')) return
    setBusyId(item.id)
    try {
      if (action === 'approve') {
        await agentApprovalsApi.approve(item.id, 'approved in workspace')
        toast.success('审批已批准')
      } else if (action === 'reject') {
        await agentApprovalsApi.reject(item.id, 'rejected in workspace')
        toast.success('审批已驳回')
      } else {
        await agentApprovalsApi.revoke(item.id, 'revoked in workspace')
        toast.success('审批已撤销')
      }
      setExpandedAuditId(null)
      setAuditEventsById((prev) => {
        const next = { ...prev }
        delete next[item.id]
        return next
      })
      await loadApprovals()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '审批操作失败')
    } finally {
      setBusyId(null)
    }
  }

  const toggleAudit = async (item: AgentApprovalItem) => {
    if (expandedAuditId === item.id) {
      setExpandedAuditId(null)
      return
    }

    setExpandedAuditId(item.id)
    if (auditEventsById[item.id]) {
      return
    }

    setAuditLoadingId(item.id)
    try {
      const response = await agentApprovalsApi.auditEvents(item.id)
      setAuditEventsById((prev) => ({ ...prev, [item.id]: response.items }))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '审计记录加载失败')
    } finally {
      setAuditLoadingId(null)
    }
  }

  const exportAudit = async (item: AgentApprovalItem) => {
    setExportingAuditId(item.id)
    try {
      const artifact = await agentApprovalsApi.auditExport(item.id)
      downloadAuditArtifact(item.id, artifact)
      toast.success('审计导出已生成')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '审计导出失败')
    } finally {
      setExportingAuditId(null)
    }
  }

  return (
    <PageContainer
      title="Agent 审批工作台"
      description="高风险智能体动作"
      actions={
        <button
          type="button"
          onClick={() => void loadApprovals()}
          className="inline-flex h-10 items-center gap-2 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted"
        >
          <icons.RefreshCw className="h-4 w-4" />
          刷新
        </button>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="待处理" value={pendingCount} icon={icons.Clock} tone="amber" />
        <Metric label="本页批准" value={stats.approved} icon={icons.CheckCircle2} tone="emerald" />
        <Metric label="本页拦截" value={stats.rejected + stats.revoked + stats.expired} icon={icons.ShieldAlert} tone="rose" />
        <Metric label="本页总数" value={items.length} icon={icons.Activity} tone="slate" />
      </div>

      <div className="flex flex-wrap items-center gap-2" data-testid="agent-approval-status-filter">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.value}
            type="button"
            onClick={() => setStatus(filter.value)}
            className={`h-9 rounded-lg border px-3 text-sm font-medium transition-colors ${
              status === filter.value
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState variant="skeleton" rows={5} />
      ) : error ? (
        <ErrorState variant="card" message={error} onRetry={loadApprovals} />
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-background p-8 text-center" data-testid="agent-approval-empty">
          <icons.CheckCircle2 className="mx-auto h-8 w-8 text-emerald-600" />
          <p className="mt-3 text-sm font-medium text-foreground">暂无待处理审批</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="agent-approval-list">
          {items.map((item) => (
            <ApprovalRow
              key={item.id}
              item={item}
              busy={busyId === item.id}
              onApprove={() => void decide(item, 'approve')}
              onReject={() => void decide(item, 'reject')}
              onRevoke={() => void decide(item, 'revoke')}
              onToggleAudit={() => void toggleAudit(item)}
              auditOpen={expandedAuditId === item.id}
              auditItems={auditEventsById[item.id] ?? []}
              auditLoading={auditLoadingId === item.id}
              auditExporting={exportingAuditId === item.id}
              onExportAudit={() => void exportAudit(item)}
            />
          ))}
        </div>
      )}
    </PageContainer>
  )
}

function Metric({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string
  value: number
  icon: IconComponent
  tone: 'amber' | 'emerald' | 'rose' | 'slate'
}) {
  const toneClass = {
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    rose: 'bg-rose-50 text-rose-700 border-rose-100',
    slate: 'bg-slate-50 text-slate-700 border-slate-100',
  }[tone]

  return (
    <div className="flex min-h-[88px] items-center gap-3 rounded-lg border border-border bg-background p-4">
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${toneClass}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
      </div>
    </div>
  )
}

function ApprovalRow({
  item,
  busy,
  auditOpen,
  auditItems,
  auditLoading,
  auditExporting,
  onApprove,
  onReject,
  onRevoke,
  onToggleAudit,
  onExportAudit,
}: {
  item: AgentApprovalItem
  busy: boolean
  auditOpen: boolean
  auditItems: AgentApprovalAuditEvent[]
  auditLoading: boolean
  auditExporting: boolean
  onApprove: () => void
  onReject: () => void
  onRevoke: () => void
  onToggleAudit: () => void
  onExportAudit: () => void
}) {
  const meta = STATUS_META[item.status] ?? STATUS_META.pending
  const StatusIcon = meta.icon
  const preview = payloadPreview(item.payload)

  return (
    <article className="rounded-lg border border-border bg-background p-4 shadow-sm" data-testid={`agent-approval-row-${item.id}`}>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold ${meta.className}`}>
              <StatusIcon className="h-3.5 w-3.5" />
              {meta.label}
            </span>
            <span className="rounded-md border border-border bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
              {item.risk_level.toUpperCase()}
            </span>
          </div>

          <div>
            <h2 className="break-words text-base font-semibold text-foreground">
              {formatActionType(item.action_type)}
            </h2>
            <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 xl:grid-cols-4">
              <Field label="请求人" value={shortId(item.requested_by)} />
              <Field label="路由" value={shortId(item.route_id)} />
              <Field label="创建" value={formatDateTime(item.created_at)} />
              <Field label="到期" value={formatDateTime(item.expires_at)} />
            </div>
          </div>

          {preview.length > 0 && (
            <dl className="grid gap-2 sm:grid-cols-2">
              {preview.map(([key, value]) => (
                <div key={key} className="min-w-0 rounded-md bg-muted/60 px-3 py-2">
                  <dt className="text-[11px] font-medium text-muted-foreground">{key}</dt>
                  <dd className="mt-0.5 truncate text-sm text-foreground">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
          <button
            type="button"
            disabled={auditLoading}
            onClick={onToggleAudit}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
          >
            <icons.List className="h-4 w-4" />
            {auditOpen ? '收起审计' : '审计'}
          </button>
          <button
            type="button"
            disabled={auditExporting}
            onClick={onExportAudit}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
          >
            <icons.Download className="h-4 w-4" />
            导出
          </button>
          {item.status === 'pending' && (
            <>
              <button
                type="button"
                disabled={busy}
                onClick={onApprove}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <icons.Check className="h-4 w-4" />
                批准
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={onReject}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              >
                <icons.XCircle className="h-4 w-4" />
                驳回
              </button>
            </>
          )}
          {item.status === 'approved' && (
            <button
              type="button"
              disabled={busy}
              onClick={onRevoke}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-destructive/20 bg-destructive/5 px-3 text-sm font-medium text-destructive hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <icons.Ban className="h-4 w-4" />
              撤销
            </button>
          )}
        </div>
      </div>
      {auditOpen && (
        <AuditTrail
          loading={auditLoading}
          items={auditItems}
        />
      )}
    </article>
  )
}

function AuditTrail({
  loading,
  items,
}: {
  loading: boolean
  items: AgentApprovalAuditEvent[]
}) {
  if (loading) {
    return (
      <div className="mt-4 rounded-lg border border-dashed border-border bg-muted/30 p-3 text-sm text-muted-foreground">
        正在加载审计记录...
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="mt-4 rounded-lg border border-dashed border-border bg-muted/30 p-3 text-sm text-muted-foreground">
        暂无可见审计记录
      </div>
    )
  }

  return (
    <div className="mt-4 rounded-lg border border-border bg-muted/30 p-3" data-testid="agent-approval-audit-trail">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
        <icons.ClipboardCheck className="h-4 w-4 text-primary" />
        审计时间线
      </div>
      <ol className="space-y-2">
        {items.map((event) => (
          <li key={event.id} className="grid gap-2 rounded-md bg-background px-3 py-2 text-xs text-muted-foreground sm:grid-cols-[minmax(0,1fr)_auto]">
            <div className="min-w-0">
              <p className="truncate font-medium text-foreground">
                {formatActionType(event.action)}
              </p>
              <p className="mt-0.5">
                {event.status}
                {event.reason_code ? ` · ${event.reason_code}` : ''}
              </p>
            </div>
            <div className="sm:text-right">
              <p>{formatDateTime(event.created_at)}</p>
              <p className="mt-0.5">actor {shortId(event.actor_user_id || event.actor_type)}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <span className="font-medium text-muted-foreground">{label}</span>
      <span className="ml-1 text-foreground">{value}</span>
    </div>
  )
}
