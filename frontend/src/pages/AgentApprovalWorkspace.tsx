import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { PageContainer } from '@/components/ui/PageContainer'
import {
  agentApprovalsApi,
  SKILL_GOVERNANCE_REQUIRED_CHECKS,
  skillGovernanceApi,
  type AgentApprovalAuditExport,
  type AgentApprovalAuditEvent,
  type AgentApprovalItem,
  type AgentApprovalStatus,
  type AgentWorkspaceControlAction,
  type SkillGovernanceAuditEvent,
  type SkillGovernanceAuditExport,
  type SkillGovernanceEnabledVersion,
  type SkillGovernanceProposal,
  type SkillGovernanceStatus,
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

const WORKSPACE_CONTROLS: Array<{ action: AgentWorkspaceControlAction; label: string; icon: IconComponent }> = [
  { action: 'pause', label: '暂停', icon: icons.Square },
  { action: 'takeover', label: '接管', icon: icons.ShieldCheck },
  { action: 'terminate', label: '终止', icon: icons.Ban },
]

const SKILL_STATUS_META: Record<SkillGovernanceStatus, { label: string; className: string; icon: IconComponent }> = {
  draft: { label: '草稿', className: 'border-slate-200 bg-slate-50 text-slate-700', icon: icons.Edit3 },
  evaluated: { label: '已评测', className: 'border-sky-200 bg-sky-50 text-sky-700', icon: icons.ClipboardCheck },
  approved: { label: '已批准', className: 'border-emerald-200 bg-emerald-50 text-emerald-700', icon: icons.ShieldCheck },
  gray_released: { label: '灰度中', className: 'border-primary/20 bg-primary/10 text-primary', icon: icons.SkipForward },
  rejected: { label: '已拒绝', className: 'border-destructive/20 bg-destructive/5 text-destructive', icon: icons.XCircle },
  rolled_back: { label: '已回滚', className: 'border-amber-200 bg-amber-50 text-amber-700', icon: icons.Undo },
}

const SKILL_RISK_OPTIONS = ['low', 'medium', 'high'] as const

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

function downloadSkillAuditArtifact(proposalId: string, artifact: SkillGovernanceAuditExport): void {
  const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `skill-governance-${safeFileSegment(proposalId)}-audit.json`
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
  const [controlBusyKey, setControlBusyKey] = useState<string | null>(null)
  const [skillProposals, setSkillProposals] = useState<SkillGovernanceProposal[]>([])
  const [skillEnabled, setSkillEnabled] = useState<SkillGovernanceEnabledVersion | null>(null)
  const [skillLoading, setSkillLoading] = useState(true)
  const [skillError, setSkillError] = useState<string | null>(null)
  const [skillBusyKey, setSkillBusyKey] = useState<string | null>(null)
  const [skillAuditEventsById, setSkillAuditEventsById] = useState<Record<string, SkillGovernanceAuditEvent[]>>({})
  const [skillAuditLoadingId, setSkillAuditLoadingId] = useState<string | null>(null)
  const [expandedSkillAuditId, setExpandedSkillAuditId] = useState<string | null>(null)
  const [exportingSkillAuditId, setExportingSkillAuditId] = useState<string | null>(null)
  const [watchedSkillName, setWatchedSkillName] = useState('contract-review')
  const [skillForm, setSkillForm] = useState({
    skill_name: 'contract-review',
    current_version: '1.0.0',
    proposed_version: '1.1.0',
    source: 'workspace:manual-proposal',
    risk_level: 'medium',
  })

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

  const loadSkillGovernance = useCallback(async () => {
    const skillName = watchedSkillName.trim() || 'contract-review'
    setSkillLoading(true)
    setSkillError(null)
    try {
      const [list, enabled] = await Promise.all([
        skillGovernanceApi.list({ page_size: 20 }),
        skillGovernanceApi.enabled(skillName),
      ])
      setSkillProposals(list.items)
      setSkillEnabled(enabled)
    } catch (err) {
      setSkillError(err instanceof Error ? err.message : '加载 Skill 治理失败')
    } finally {
      setSkillLoading(false)
    }
  }, [watchedSkillName])

  useEffect(() => {
    void loadSkillGovernance()
  }, [loadSkillGovernance])

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

  const controlWorkspace = async (item: AgentApprovalItem, action: AgentWorkspaceControlAction) => {
    const key = `${item.id}:${action}`
    setControlBusyKey(key)
    try {
      await agentApprovalsApi.workspaceControl(item.id, action, `${action} requested in workspace`)
      toast.success('工作室控制已执行')
      await loadApprovals()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '工作室控制被拒绝')
    } finally {
      setControlBusyKey(null)
    }
  }

  const submitSkillProposal = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const skillName = skillForm.skill_name.trim()
    const proposedVersion = skillForm.proposed_version.trim()
    const source = skillForm.source.trim()
    if (!skillName || !proposedVersion || !source) {
      toast.error('请补齐 Skill、版本和来源')
      return
    }

    setSkillBusyKey('create')
    try {
      const created = await skillGovernanceApi.create({
        skill_name: skillName,
        current_version: skillForm.current_version.trim() || null,
        proposed_version: proposedVersion,
        source,
        risk_level: skillForm.risk_level,
      })
      setWatchedSkillName(created.skill_name)
      setSkillForm((prev) => ({
        ...prev,
        skill_name: created.skill_name,
        current_version: created.proposed_version,
        proposed_version: '',
        source: 'workspace:manual-proposal',
      }))
      setSkillProposals((prev) => [created, ...prev.filter((item) => item.id !== created.id)])
      setSkillEnabled(await skillGovernanceApi.enabled(created.skill_name))
      toast.success('Skill 提案已创建')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Skill 提案创建失败')
    } finally {
      setSkillBusyKey(null)
    }
  }

  const runSkillAction = async (
    proposal: SkillGovernanceProposal,
    action: 'eval' | 'approve' | 'grayRelease' | 'rollback',
  ) => {
    const key = `${proposal.id}:${action}`
    setSkillBusyKey(key)
    try {
      if (action === 'eval') {
        const checks = Object.fromEntries(SKILL_GOVERNANCE_REQUIRED_CHECKS.map((name) => [name, true]))
        await skillGovernanceApi.recordEval(proposal.id, checks)
        toast.success('评测结果已记录')
      } else if (action === 'approve') {
        await skillGovernanceApi.approve(proposal.id)
        toast.success('Skill 提案已批准')
      } else if (action === 'grayRelease') {
        await skillGovernanceApi.grayRelease(proposal.id, 100)
        toast.success('Skill 已灰度启用')
      } else {
        await skillGovernanceApi.rollback(proposal.id, 'rollback requested in workspace')
        toast.success('Skill 已回滚')
      }
      setSkillAuditEventsById((prev) => {
        const next = { ...prev }
        delete next[proposal.id]
        return next
      })
      setWatchedSkillName(proposal.skill_name)
      await loadSkillGovernance()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Skill 治理操作失败')
    } finally {
      setSkillBusyKey(null)
    }
  }

  const toggleSkillAudit = async (proposal: SkillGovernanceProposal) => {
    if (expandedSkillAuditId === proposal.id) {
      setExpandedSkillAuditId(null)
      return
    }

    setExpandedSkillAuditId(proposal.id)
    if (skillAuditEventsById[proposal.id]) return

    setSkillAuditLoadingId(proposal.id)
    try {
      const response = await skillGovernanceApi.auditEvents(proposal.id)
      setSkillAuditEventsById((prev) => ({ ...prev, [proposal.id]: response.items }))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Skill 审计记录加载失败')
    } finally {
      setSkillAuditLoadingId(null)
    }
  }

  const exportSkillAudit = async (proposal: SkillGovernanceProposal) => {
    setExportingSkillAuditId(proposal.id)
    try {
      const artifact = await skillGovernanceApi.auditExport(proposal.id)
      downloadSkillAuditArtifact(proposal.id, artifact)
      toast.success('Skill 审计导出已生成')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Skill 审计导出失败')
    } finally {
      setExportingSkillAuditId(null)
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

      <SkillGovernancePanel
        proposals={skillProposals}
        enabled={skillEnabled}
        loading={skillLoading}
        error={skillError}
        busyKey={skillBusyKey}
        form={skillForm}
        watchedSkillName={watchedSkillName}
        auditOpenId={expandedSkillAuditId}
        auditEventsById={skillAuditEventsById}
        auditLoadingId={skillAuditLoadingId}
        exportingAuditId={exportingSkillAuditId}
        onRefresh={() => void loadSkillGovernance()}
        onSubmit={submitSkillProposal}
        onFormChange={(patch) => setSkillForm((prev) => ({ ...prev, ...patch }))}
        onWatchSkill={(value) => setWatchedSkillName(value.trim() || 'contract-review')}
        onRunAction={(proposal, action) => void runSkillAction(proposal, action)}
        onToggleAudit={(proposal) => void toggleSkillAudit(proposal)}
        onExportAudit={(proposal) => void exportSkillAudit(proposal)}
      />

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
              controlBusyKey={controlBusyKey}
              onExportAudit={() => void exportAudit(item)}
              onControlWorkspace={(action) => void controlWorkspace(item, action)}
            />
          ))}
        </div>
      )}
    </PageContainer>
  )
}

type SkillFormState = {
  skill_name: string
  current_version: string
  proposed_version: string
  source: string
  risk_level: string
}

type SkillGovernanceAction = 'eval' | 'approve' | 'grayRelease' | 'rollback'

function SkillGovernancePanel({
  proposals,
  enabled,
  loading,
  error,
  busyKey,
  form,
  watchedSkillName,
  auditOpenId,
  auditEventsById,
  auditLoadingId,
  exportingAuditId,
  onRefresh,
  onSubmit,
  onFormChange,
  onWatchSkill,
  onRunAction,
  onToggleAudit,
  onExportAudit,
}: {
  proposals: SkillGovernanceProposal[]
  enabled: SkillGovernanceEnabledVersion | null
  loading: boolean
  error: string | null
  busyKey: string | null
  form: SkillFormState
  watchedSkillName: string
  auditOpenId: string | null
  auditEventsById: Record<string, SkillGovernanceAuditEvent[]>
  auditLoadingId: string | null
  exportingAuditId: string | null
  onRefresh: () => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onFormChange: (patch: Partial<SkillFormState>) => void
  onWatchSkill: (value: string) => void
  onRunAction: (proposal: SkillGovernanceProposal, action: SkillGovernanceAction) => void
  onToggleAudit: (proposal: SkillGovernanceProposal) => void
  onExportAudit: (proposal: SkillGovernanceProposal) => void
}) {
  const activeProposals = proposals.filter((proposal) => proposal.status !== 'rolled_back').length

  return (
    <section className="rounded-lg border border-border bg-background p-4 shadow-sm" data-testid="skill-governance-panel">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
              <icons.Wand2 className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-foreground">Skills 进化治理</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {watchedSkillName} · 启用 {enabled?.enabled_version ?? '未启用'} · {activeProposals} 个流转中
              </p>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted"
        >
          <icons.RefreshCw className="h-4 w-4" />
          刷新
        </button>
      </div>

      <form className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_0.8fr_0.8fr_1.2fr_auto_auto]" data-testid="skill-governance-proposal-form" onSubmit={onSubmit}>
        <label className="min-w-0">
          <span className="text-xs font-medium text-muted-foreground">Skill</span>
          <input
            value={form.skill_name}
            onChange={(event) => onFormChange({ skill_name: event.target.value })}
            onBlur={(event) => onWatchSkill(event.target.value)}
            className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
          />
        </label>
        <label className="min-w-0">
          <span className="text-xs font-medium text-muted-foreground">当前版本</span>
          <input
            value={form.current_version}
            onChange={(event) => onFormChange({ current_version: event.target.value })}
            className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
          />
        </label>
        <label className="min-w-0">
          <span className="text-xs font-medium text-muted-foreground">目标版本</span>
          <input
            value={form.proposed_version}
            onChange={(event) => onFormChange({ proposed_version: event.target.value })}
            className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
          />
        </label>
        <label className="min-w-0">
          <span className="text-xs font-medium text-muted-foreground">来源</span>
          <input
            value={form.source}
            onChange={(event) => onFormChange({ source: event.target.value })}
            className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
          />
        </label>
        <label className="min-w-0">
          <span className="text-xs font-medium text-muted-foreground">风险</span>
          <select
            value={form.risk_level}
            onChange={(event) => onFormChange({ risk_level: event.target.value })}
            className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary lg:w-28"
          >
            {SKILL_RISK_OPTIONS.map((risk) => (
              <option key={risk} value={risk}>{risk}</option>
            ))}
          </select>
        </label>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={busyKey === 'create'}
            className="inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60 lg:w-auto"
          >
            <icons.Plus className="h-4 w-4" />
            创建
          </button>
        </div>
      </form>

      <div className="mt-4">
        {loading ? (
          <LoadingState variant="skeleton" rows={3} />
        ) : error ? (
          <ErrorState variant="card" message={error} onRetry={onRefresh} />
        ) : proposals.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-muted/30 p-4 text-sm text-muted-foreground">
            暂无 Skill 提案
          </div>
        ) : (
          <div className="space-y-3" data-testid="skill-governance-proposal-list">
            {proposals.map((proposal) => (
              <SkillGovernanceRow
                key={proposal.id}
                proposal={proposal}
                busyKey={busyKey}
                auditOpen={auditOpenId === proposal.id}
                auditItems={auditEventsById[proposal.id] ?? []}
                auditLoading={auditLoadingId === proposal.id}
                auditExporting={exportingAuditId === proposal.id}
                onRunAction={(action) => onRunAction(proposal, action)}
                onToggleAudit={() => onToggleAudit(proposal)}
                onExportAudit={() => onExportAudit(proposal)}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function SkillGovernanceRow({
  proposal,
  busyKey,
  auditOpen,
  auditItems,
  auditLoading,
  auditExporting,
  onRunAction,
  onToggleAudit,
  onExportAudit,
}: {
  proposal: SkillGovernanceProposal
  busyKey: string | null
  auditOpen: boolean
  auditItems: SkillGovernanceAuditEvent[]
  auditLoading: boolean
  auditExporting: boolean
  onRunAction: (action: SkillGovernanceAction) => void
  onToggleAudit: () => void
  onExportAudit: () => void
}) {
  const meta = SKILL_STATUS_META[proposal.status] ?? SKILL_STATUS_META.draft
  const StatusIcon = meta.icon
  const evalDone = SKILL_GOVERNANCE_REQUIRED_CHECKS.filter((name) => proposal.eval_results?.[name]).length

  return (
    <article className="rounded-lg border border-border bg-muted/20 p-3" data-testid={`skill-governance-row-${proposal.id}`}>
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold ${meta.className}`}>
              <StatusIcon className="h-3.5 w-3.5" />
              {meta.label}
            </span>
            <span className="rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground">
              {proposal.risk_level.toUpperCase()}
            </span>
            {proposal.gray_percentage ? (
              <span className="rounded-md border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
                {proposal.gray_percentage}%
              </span>
            ) : null}
          </div>
          <div>
            <h3 className="break-words text-sm font-semibold text-foreground">
              {proposal.skill_name} {proposal.current_version ?? 'new'} → {proposal.proposed_version}
            </h3>
            <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 xl:grid-cols-4">
              <Field label="来源" value={proposal.source} />
              <Field label="创建人" value={shortId(proposal.created_by)} />
              <Field label="评测" value={`${evalDone}/${SKILL_GOVERNANCE_REQUIRED_CHECKS.length}`} />
              <Field label="更新" value={formatDateTime(proposal.updated_at)} />
            </div>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2 xl:justify-end">
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
          {(proposal.status === 'draft' || proposal.status === 'rejected') && (
            <SkillActionButton
              busy={busyKey === `${proposal.id}:eval`}
              icon={icons.ClipboardCheck}
              label="评测"
              onClick={() => onRunAction('eval')}
            />
          )}
          {proposal.status === 'evaluated' && (
            <SkillActionButton
              busy={busyKey === `${proposal.id}:approve`}
              icon={icons.ShieldCheck}
              label="批准"
              onClick={() => onRunAction('approve')}
            />
          )}
          {proposal.status === 'approved' && (
            <SkillActionButton
              busy={busyKey === `${proposal.id}:grayRelease`}
              icon={icons.SkipForward}
              label="灰度"
              onClick={() => onRunAction('grayRelease')}
            />
          )}
          {(proposal.status === 'approved' || proposal.status === 'gray_released') && (
            <button
              type="button"
              disabled={busyKey === `${proposal.id}:rollback`}
              onClick={() => onRunAction('rollback')}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 text-sm font-medium text-amber-700 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <icons.Undo className="h-4 w-4" />
              回滚
            </button>
          )}
        </div>
      </div>
      {auditOpen && (
        <SkillAuditTrail
          loading={auditLoading}
          items={auditItems}
        />
      )}
    </article>
  )
}

function SkillActionButton({
  busy,
  icon: Icon,
  label,
  onClick,
}: {
  busy: boolean
  icon: IconComponent
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  )
}

function SkillAuditTrail({
  loading,
  items,
}: {
  loading: boolean
  items: SkillGovernanceAuditEvent[]
}) {
  if (loading) {
    return (
      <div className="mt-4 rounded-lg border border-dashed border-border bg-background p-3 text-sm text-muted-foreground">
        正在加载审计记录...
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="mt-4 rounded-lg border border-dashed border-border bg-background p-3 text-sm text-muted-foreground">
        暂无可见审计记录
      </div>
    )
  }

  return (
    <div className="mt-4 rounded-lg border border-border bg-background p-3" data-testid="skill-governance-audit-trail">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
        <icons.ClipboardCheck className="h-4 w-4 text-primary" />
        Skill 审计时间线
      </div>
      <ol className="space-y-2">
        {items.map((event) => (
          <li key={event.id} className="grid gap-2 rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground sm:grid-cols-[minmax(0,1fr)_auto]">
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
              <p className="mt-0.5">actor {shortId(event.actor)}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
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
  controlBusyKey,
  onApprove,
  onReject,
  onRevoke,
  onToggleAudit,
  onExportAudit,
  onControlWorkspace,
}: {
  item: AgentApprovalItem
  busy: boolean
  auditOpen: boolean
  auditItems: AgentApprovalAuditEvent[]
  auditLoading: boolean
  auditExporting: boolean
  controlBusyKey: string | null
  onApprove: () => void
  onReject: () => void
  onRevoke: () => void
  onToggleAudit: () => void
  onExportAudit: () => void
  onControlWorkspace: (action: AgentWorkspaceControlAction) => void
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
          {item.status === 'approved' && WORKSPACE_CONTROLS.map(({ action, label, icon: ControlIcon }) => {
            const controlKey = `${item.id}:${action}`
            return (
              <button
                key={action}
                type="button"
                disabled={controlBusyKey === controlKey}
                onClick={() => onControlWorkspace(action)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              >
                <ControlIcon className="h-4 w-4" />
                {label}
              </button>
            )
          })}
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
      <span className="ml-1 break-words text-foreground">{value}</span>
    </div>
  )
}
