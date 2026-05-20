import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

// J (Phase J, 2026-05-14): common/ → ui-unified/ 迁移 (ADR 003 Phase 2)
import { ErrorState, LoadingState } from '@/components/ui-unified'
import { PageContainer } from '@/components/ui/PageContainer'
import {
  agentApprovalsApi,
  SKILL_GOVERNANCE_REQUIRED_CHECKS,
  harnessGovernanceApi,
  skillGovernanceApi,
  type AgentApprovalAuditExport,
  type AgentApprovalAuditEvent,
  type AgentCapabilityRoutePolicy,
  type AgentApprovalItem,
  type AgentApprovalStatus,
  type AgentWorkspaceArtifact,
  type AgentWorkspaceArtifactExport,
  type AgentWorkspaceControlAction,
  type HarnessAgentTools,
  type HarnessToolItem,
  type SkillGovernanceAuditEvent,
  type SkillGovernanceAuditExport,
  type SkillGovernanceEnabledVersion,
  type SkillGovernanceProposal,
  type SkillGovernanceStatus,
  type SkillConnectorConfig,
} from '@/lib/api'
import { icons, type IconComponent } from '@/lib/icons'
import { useAuthStore } from '@/lib/store'
import {
  buildSkillConnectorPayload,
  connectorToForm,
  defaultSkillConnectorForm,
  parseConnectorCredentials,
  summarizeConnectorCredentials,
  type SkillConnectorFormState,
} from './skillConnectorSettingsModel'

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
  { action: 'observe', label: '旁听', icon: icons.Eye },
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

const CAPABILITY_AGENT_OPTIONS = [
  { value: 'legal_researcher', label: 'Legal Researcher' },
  { value: 'legal_advisor', label: 'Legal Advisor' },
  { value: 'contract_analyzer', label: 'Contract Analyzer' },
]

const FULL_CAPABILITY_ROLES = new Set(['admin', 'boss', 'owner', 'org_admin', 'super_admin'])
const DEPARTMENT_CAPABILITY_ROLES = new Set(['department_admin', 'dept_admin'])
const PROVIDER_CAPABILITY_ROLES = new Set(['accountant', 'external_provider', 'finance_advisor', 'lawyer', 'tax_advisor'])
const BASIC_TOOL_RISKS = new Set(['', 'l0', 'l1', 'low', 'none', 'read', 'read_only', 'readonly'])
const FULL_ONLY_TOOL_TAGS = new Set(['admin', 'billing', 'cli', 'code', 'desktop', 'export', 'mcp', 'system'])
const PROVIDER_VISIBLE_TOOL_TAGS = new Set(['knowledge', 'material', 'package', 'provider'])

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

function downloadWorkspaceArtifacts(approvalId: string, artifact: AgentWorkspaceArtifactExport): void {
  const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `agent-approval-${safeFileSegment(approvalId)}-workspace-artifacts.json`
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

function normalizeRole(role?: string | null): string {
  return (role || 'employee').trim().toLowerCase().replace(/-/g, '_')
}

function normalizeRiskLevel(value?: string): string {
  return (value || '').trim().toLowerCase().replace(/-/g, '_')
}

function toolTags(tool: HarnessToolItem): Set<string> {
  return new Set((tool.tags ?? []).map((tag) => tag.trim().toLowerCase()).filter(Boolean))
}

function hasFullCapabilityVisibility(role: string): boolean {
  return FULL_CAPABILITY_ROLES.has(normalizeRole(role))
}

function roleVisibilityLabel(role: string): string {
  const normalized = normalizeRole(role)
  if (FULL_CAPABILITY_ROLES.has(normalized)) return '全量能力'
  if (DEPARTMENT_CAPABILITY_ROLES.has(normalized)) return '部门能力'
  if (PROVIDER_CAPABILITY_ROLES.has(normalized)) return '材料包能力'
  return '基础与申请'
}

function isBasicCapabilityTool(tool: HarnessToolItem): boolean {
  return !tool.requires_approval && BASIC_TOOL_RISKS.has(normalizeRiskLevel(tool.risk_level))
}

function hasFullOnlyTag(tool: HarnessToolItem): boolean {
  const tags = toolTags(tool)
  for (const tag of tags) {
    if (FULL_ONLY_TOOL_TAGS.has(tag)) return true
  }
  return false
}

function providerCanSeeTool(tool: HarnessToolItem, isAvailable: boolean): boolean {
  if (isAvailable || isBasicCapabilityTool(tool)) return true
  const tags = toolTags(tool)
  for (const tag of tags) {
    if (PROVIDER_VISIBLE_TOOL_TAGS.has(tag)) return true
  }
  return false
}

function canRoleSeeCapabilityTool(tool: HarnessToolItem, role: string, isAvailable: boolean): boolean {
  const normalized = normalizeRole(role)
  if (FULL_CAPABILITY_ROLES.has(normalized)) return true
  if (PROVIDER_CAPABILITY_ROLES.has(normalized)) return providerCanSeeTool(tool, isAvailable)
  if (isAvailable || isBasicCapabilityTool(tool)) return true
  if (hasFullOnlyTag(tool)) return false
  if (DEPARTMENT_CAPABILITY_ROLES.has(normalized)) return Boolean(tool.requires_approval)
  return Boolean(tool.requires_approval)
}

function capabilityToolState(tool: HarnessToolItem, isAvailable: boolean): 'available' | 'blocked' | 'requestable' {
  if (isAvailable) return 'available'
  if (tool.requires_approval) return 'requestable'
  return 'blocked'
}

export default function AgentApprovalWorkspace() {
  const currentUserRole = useAuthStore((state) => state.user?.role ?? 'employee')
  const canManageCapabilityPolicies = hasFullCapabilityVisibility(currentUserRole)
  const canManageSkillConnectors = hasFullCapabilityVisibility(currentUserRole)
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
  const [workspaceArtifactsById, setWorkspaceArtifactsById] = useState<Record<string, AgentWorkspaceArtifact[]>>({})
  const [workspaceArtifactLoadingId, setWorkspaceArtifactLoadingId] = useState<string | null>(null)
  const [expandedWorkspaceArtifactId, setExpandedWorkspaceArtifactId] = useState<string | null>(null)
  const [workspaceArtifactBusyId, setWorkspaceArtifactBusyId] = useState<string | null>(null)
  const [workspaceArtifactRevisionBusyId, setWorkspaceArtifactRevisionBusyId] = useState<string | null>(null)
  const [workspaceArtifactExportingId, setWorkspaceArtifactExportingId] = useState<string | null>(null)
  const [skillProposals, setSkillProposals] = useState<SkillGovernanceProposal[]>([])
  const [skillEnabled, setSkillEnabled] = useState<SkillGovernanceEnabledVersion | null>(null)
  const [skillLoading, setSkillLoading] = useState(true)
  const [skillError, setSkillError] = useState<string | null>(null)
  const [skillBusyKey, setSkillBusyKey] = useState<string | null>(null)
  const [skillAuditEventsById, setSkillAuditEventsById] = useState<Record<string, SkillGovernanceAuditEvent[]>>({})
  const [skillAuditLoadingId, setSkillAuditLoadingId] = useState<string | null>(null)
  const [expandedSkillAuditId, setExpandedSkillAuditId] = useState<string | null>(null)
  const [exportingSkillAuditId, setExportingSkillAuditId] = useState<string | null>(null)
  const [skillConnectors, setSkillConnectors] = useState<SkillConnectorConfig[]>([])
  const [skillConnectorsLoading, setSkillConnectorsLoading] = useState(true)
  const [skillConnectorsError, setSkillConnectorsError] = useState<string | null>(null)
  const [skillConnectorBusyKey, setSkillConnectorBusyKey] = useState<string | null>(null)
  const [editingSkillConnectorId, setEditingSkillConnectorId] = useState<string | null>(null)
  const [skillConnectorForm, setSkillConnectorForm] = useState<SkillConnectorFormState>(defaultSkillConnectorForm)
  const [watchedSkillName, setWatchedSkillName] = useState('contract-review')
  const [skillForm, setSkillForm] = useState({
    skill_name: 'contract-review',
    current_version: '1.0.0',
    proposed_version: '1.1.0',
    source: 'workspace:manual-proposal',
    risk_level: 'medium',
  })
  const [capabilityAgent, setCapabilityAgent] = useState('legal_researcher')
  const [capabilityTools, setCapabilityTools] = useState<HarnessToolItem[]>([])
  const [capabilityAvailability, setCapabilityAvailability] = useState<HarnessAgentTools | null>(null)
  const [capabilityLoading, setCapabilityLoading] = useState(true)
  const [capabilityError, setCapabilityError] = useState<string | null>(null)
  const [capabilityRoutes, setCapabilityRoutes] = useState<AgentCapabilityRoutePolicy[]>([])
  const [capabilityRoutesLoading, setCapabilityRoutesLoading] = useState(true)
  const [capabilityRoutesError, setCapabilityRoutesError] = useState<string | null>(null)
  const [capabilityRouteBusyKey, setCapabilityRouteBusyKey] = useState<string | null>(null)

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

  const loadSkillConnectors = useCallback(async () => {
    if (!canManageSkillConnectors) {
      setSkillConnectors([])
      setSkillConnectorsError(null)
      setSkillConnectorsLoading(false)
      return
    }

    const skillName = watchedSkillName.trim() || undefined
    setSkillConnectorsLoading(true)
    setSkillConnectorsError(null)
    try {
      const response = await skillGovernanceApi.connectors.list({ skill_name: skillName })
      setSkillConnectors(response.items)
    } catch (err) {
      setSkillConnectorsError(err instanceof Error ? err.message : '加载 Skill 连接器失败')
    } finally {
      setSkillConnectorsLoading(false)
    }
  }, [canManageSkillConnectors, watchedSkillName])

  useEffect(() => {
    void loadSkillConnectors()
  }, [loadSkillConnectors])

  const loadCapabilityPolicy = useCallback(async () => {
    setCapabilityLoading(true)
    setCapabilityError(null)
    try {
      const [tools, availability] = await Promise.all([
        harnessGovernanceApi.listTools(),
        harnessGovernanceApi.agentTools(capabilityAgent, {
          privacy_mode: 'hybrid',
          device_trusted: true,
          channel_allowed: true,
          approval_state: 'approved',
          subscription_feature: ['legal_knowledge_base', 'lawyer_matching'],
        }),
      ])
      setCapabilityTools(tools)
      setCapabilityAvailability(availability)
    } catch (err) {
      setCapabilityError(err instanceof Error ? err.message : '加载能力策略失败')
    } finally {
      setCapabilityLoading(false)
    }
  }, [capabilityAgent])

  useEffect(() => {
    void loadCapabilityPolicy()
  }, [loadCapabilityPolicy])

  const loadCapabilityRoutes = useCallback(async () => {
    if (!canManageCapabilityPolicies) {
      setCapabilityRoutes([])
      setCapabilityRoutesError(null)
      setCapabilityRoutesLoading(false)
      return
    }

    setCapabilityRoutesLoading(true)
    setCapabilityRoutesError(null)
    try {
      const response = await agentApprovalsApi.capabilityRoutes.list()
      setCapabilityRoutes(response.items)
    } catch (err) {
      setCapabilityRoutesError(err instanceof Error ? err.message : '加载组织能力策略失败')
    } finally {
      setCapabilityRoutesLoading(false)
    }
  }, [canManageCapabilityPolicies])

  useEffect(() => {
    void loadCapabilityRoutes()
  }, [loadCapabilityRoutes])

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
      const decision = await agentApprovalsApi.workspaceControl(item.id, action, `${action} requested in workspace`)
      if (action === 'observe' && decision.workspace_snapshot) {
        setWorkspaceArtifactsById((prev) => ({
          ...prev,
          [item.id]: decision.workspace_snapshot?.artifacts ?? [],
        }))
        setAuditEventsById((prev) => ({
          ...prev,
          [item.id]: decision.workspace_snapshot?.audit_events ?? [],
        }))
        setExpandedWorkspaceArtifactId(item.id)
        setExpandedAuditId(item.id)
        toast.success('旁听快照已生成')
        return
      }
      toast.success(action === 'observe' ? '旁听快照已生成' : '工作室控制已执行')
      await loadApprovals()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '工作室控制被拒绝')
    } finally {
      setControlBusyKey(null)
    }
  }

  const toggleWorkspaceArtifacts = async (item: AgentApprovalItem) => {
    if (expandedWorkspaceArtifactId === item.id) {
      setExpandedWorkspaceArtifactId(null)
      return
    }

    setExpandedWorkspaceArtifactId(item.id)
    if (workspaceArtifactsById[item.id]) return

    setWorkspaceArtifactLoadingId(item.id)
    try {
      const response = await agentApprovalsApi.workspaceArtifacts.list(item.id)
      setWorkspaceArtifactsById((prev) => ({ ...prev, [item.id]: response.items }))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '工作室成果加载失败')
    } finally {
      setWorkspaceArtifactLoadingId(null)
    }
  }

  const recordWorkspaceArtifact = async (item: AgentApprovalItem) => {
    setWorkspaceArtifactBusyId(item.id)
    try {
      const response = await agentApprovalsApi.workspaceArtifacts.create(item.id, {
        artifact_type: 'summary',
        title: '高风险工作摘要',
        content: {
          action_type: item.action_type,
          status: item.status,
          checkpoint: 'operator-reviewed-workspace',
        },
        metadata: {
          source: 'agent-approval-workspace',
        },
      })
      if (response.artifact) {
        setWorkspaceArtifactsById((prev) => ({
          ...prev,
          [item.id]: [response.artifact as AgentWorkspaceArtifact, ...(prev[item.id] ?? [])],
        }))
      }
      setExpandedWorkspaceArtifactId(item.id)
      toast.success('工作室成果已记录')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '工作室成果记录失败')
    } finally {
      setWorkspaceArtifactBusyId(null)
    }
  }

  const exportWorkspaceArtifacts = async (item: AgentApprovalItem) => {
    setWorkspaceArtifactExportingId(item.id)
    try {
      const artifact = await agentApprovalsApi.workspaceArtifacts.export(item.id)
      downloadWorkspaceArtifacts(item.id, artifact)
      toast.success('工作室成果导出已生成')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '工作室成果导出失败')
    } finally {
      setWorkspaceArtifactExportingId(null)
    }
  }

  const reviewWorkspaceArtifact = async (item: AgentApprovalItem, artifact: AgentWorkspaceArtifact) => {
    const busyKey = artifact.id
    setWorkspaceArtifactRevisionBusyId(busyKey)
    try {
      const nextContent = {
        ...artifact.content,
        review_status: 'human-reviewed',
        reviewed_from: 'agent-approval-workspace',
      }
      const nextMetadata = {
        ...artifact.metadata,
        reviewed_from: 'agent-approval-workspace',
      }
      const response = await agentApprovalsApi.workspaceArtifacts.update(item.id, artifact.id, {
        title: artifact.title.includes('已复核') ? artifact.title : `${artifact.title}（已复核）`,
        content: nextContent,
        metadata: nextMetadata,
      })
      if (response.artifact) {
        setWorkspaceArtifactsById((prev) => ({
          ...prev,
          [item.id]: (prev[item.id] ?? []).map((current) =>
            current.id === response.artifact?.id ? response.artifact as AgentWorkspaceArtifact : current,
          ),
        }))
      }
      toast.success('工作室成果已复核')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '工作室成果复核失败')
    } finally {
      setWorkspaceArtifactRevisionBusyId(null)
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

  const resetSkillConnectorForm = (skillName = watchedSkillName.trim() || 'contract-review') => {
    setEditingSkillConnectorId(null)
    setSkillConnectorForm({
      ...defaultSkillConnectorForm,
      skill_name: skillName,
    })
  }

  const submitSkillConnector = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const skillName = skillConnectorForm.skill_name.trim()
    const connectorName = skillConnectorForm.connector_name.trim()
    if (!skillName || !connectorName) {
      toast.error('请补齐 Skill 和连接器名称')
      return
    }

    const editing = Boolean(editingSkillConnectorId)
    const payload = buildSkillConnectorPayload(skillConnectorForm, { editing })
    if (editing && skillConnectorForm.credential_mode === 'replace' && !payload.credentials) {
      toast.error('替换凭据时至少填写一个 KEY=value')
      return
    }

    const busyKey = editingSkillConnectorId ?? 'connector:create'
    setSkillConnectorBusyKey(busyKey)
    try {
      const saved = editingSkillConnectorId
        ? await skillGovernanceApi.connectors.update(editingSkillConnectorId, payload)
        : await skillGovernanceApi.connectors.create(payload)
      setWatchedSkillName(saved.skill_name)
      setSkillConnectorForm({
        ...defaultSkillConnectorForm,
        skill_name: saved.skill_name,
      })
      setEditingSkillConnectorId(null)
      toast.success(editing ? '连接器配置已更新' : '连接器配置已创建')
      const refreshed = await skillGovernanceApi.connectors.list({ skill_name: saved.skill_name })
      setSkillConnectors(refreshed.items)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '连接器配置保存失败')
    } finally {
      setSkillConnectorBusyKey(null)
    }
  }

  const editSkillConnector = (config: SkillConnectorConfig) => {
    setEditingSkillConnectorId(config.id)
    setSkillConnectorForm(connectorToForm(config))
  }

  const deleteSkillConnector = async (config: SkillConnectorConfig) => {
    if (!window.confirm(`确认删除 ${config.connector_name} 连接器配置？`)) return
    setSkillConnectorBusyKey(config.id)
    try {
      await skillGovernanceApi.connectors.delete(config.id)
      setSkillConnectors((prev) => prev.filter((item) => item.id !== config.id))
      if (editingSkillConnectorId === config.id) {
        resetSkillConnectorForm(config.skill_name)
      }
      toast.success('连接器配置已删除')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '连接器配置删除失败')
    } finally {
      setSkillConnectorBusyKey(null)
    }
  }

  const toggleCapabilityRoute = async (route: AgentCapabilityRoutePolicy) => {
    const isActive = route.status === 'active' || route.status === 'enabled'
    setCapabilityRouteBusyKey(route.route_key)
    try {
      await agentApprovalsApi.capabilityRoutes.update(route.route_key, {
        status: isActive ? 'disabled' : 'enabled',
      })
      toast.success(isActive ? '能力路由已禁用' : '能力路由已启用')
      await Promise.all([loadCapabilityRoutes(), loadCapabilityPolicy()])
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '能力路由策略更新失败')
    } finally {
      setCapabilityRouteBusyKey(null)
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
        onWatchSkill={(value) => {
          const nextSkillName = value.trim() || 'contract-review'
          setWatchedSkillName(nextSkillName)
          if (!editingSkillConnectorId) {
            setSkillConnectorForm((prev) => ({ ...prev, skill_name: nextSkillName }))
          }
        }}
        onRunAction={(proposal, action) => void runSkillAction(proposal, action)}
        onToggleAudit={(proposal) => void toggleSkillAudit(proposal)}
        onExportAudit={(proposal) => void exportSkillAudit(proposal)}
      />

      <SkillConnectorPanel
        canManage={canManageSkillConnectors}
        connectors={skillConnectors}
        loading={skillConnectorsLoading}
        error={skillConnectorsError}
        busyKey={skillConnectorBusyKey}
        editingId={editingSkillConnectorId}
        form={skillConnectorForm}
        onRefresh={() => void loadSkillConnectors()}
        onSubmit={submitSkillConnector}
        onFormChange={(patch) => setSkillConnectorForm((prev) => ({ ...prev, ...patch }))}
        onEdit={editSkillConnector}
        onDelete={(config) => void deleteSkillConnector(config)}
        onCancel={() => resetSkillConnectorForm()}
      />

      <CapabilityPolicyPanel
        agent={capabilityAgent}
        role={currentUserRole}
        tools={capabilityTools}
        availability={capabilityAvailability}
        loading={capabilityLoading}
        error={capabilityError}
        onAgentChange={setCapabilityAgent}
        onRefresh={() => void loadCapabilityPolicy()}
      />

      <CapabilityRoutePolicyPanel
        role={currentUserRole}
        canManage={canManageCapabilityPolicies}
        routes={capabilityRoutes}
        loading={capabilityRoutesLoading}
        error={capabilityRoutesError}
        busyKey={capabilityRouteBusyKey}
        onRefresh={() => void loadCapabilityRoutes()}
        onToggle={(route) => void toggleCapabilityRoute(route)}
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
              artifactOpen={expandedWorkspaceArtifactId === item.id}
              artifactItems={workspaceArtifactsById[item.id] ?? []}
              artifactLoading={workspaceArtifactLoadingId === item.id}
              artifactBusy={workspaceArtifactBusyId === item.id}
              artifactRevisionBusyId={workspaceArtifactRevisionBusyId}
              artifactExporting={workspaceArtifactExportingId === item.id}
              onExportAudit={() => void exportAudit(item)}
              onControlWorkspace={(action) => void controlWorkspace(item, action)}
              onToggleArtifacts={() => void toggleWorkspaceArtifacts(item)}
              onRecordArtifact={() => void recordWorkspaceArtifact(item)}
              onReviewArtifact={(artifact) => void reviewWorkspaceArtifact(item, artifact)}
              onExportArtifacts={() => void exportWorkspaceArtifacts(item)}
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

function SkillConnectorPanel({
  canManage,
  connectors,
  loading,
  error,
  busyKey,
  editingId,
  form,
  onRefresh,
  onSubmit,
  onFormChange,
  onEdit,
  onDelete,
  onCancel,
}: {
  canManage: boolean
  connectors: SkillConnectorConfig[]
  loading: boolean
  error: string | null
  busyKey: string | null
  editingId: string | null
  form: SkillConnectorFormState
  onRefresh: () => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onFormChange: (patch: Partial<SkillConnectorFormState>) => void
  onEdit: (config: SkillConnectorConfig) => void
  onDelete: (config: SkillConnectorConfig) => void
  onCancel: () => void
}) {
  const credentialKeyCount = connectors.reduce((total, connector) => total + connector.credential_keys.length, 0)
  const parsedCredentialCount = Object.keys(parseConnectorCredentials(form.credentials_text)).length
  const editing = Boolean(editingId)
  const credentialInputDisabled = editing && form.credential_mode !== 'replace'

  return (
    <section className="rounded-lg border border-border bg-background p-4 shadow-sm" data-testid="skill-connector-panel">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-violet-200 bg-violet-50 text-violet-700">
            <icons.Key className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-foreground">Skill 连接器凭据</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {form.skill_name || '未选择 Skill'} · {connectors.length} 个连接器 · {credentialKeyCount} 个凭据键
            </p>
          </div>
        </div>
        {canManage ? (
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted"
          >
            <icons.RefreshCw className="h-4 w-4" />
            刷新
          </button>
        ) : null}
      </div>

      {!canManage ? (
        <div className="mt-4 rounded-lg border border-dashed border-border bg-muted/30 p-4 text-sm text-muted-foreground">
          当前角色不能维护连接器凭据；请由老板、Owner、组织管理员或超级管理员处理。
        </div>
      ) : (
        <>
          <form className="mt-4 grid gap-3 xl:grid-cols-[0.9fr_0.9fr_0.7fr_1.2fr_0.7fr_0.8fr_auto]" data-testid="skill-connector-form" onSubmit={onSubmit}>
            <label className="min-w-0">
              <span className="text-xs font-medium text-muted-foreground">Skill</span>
              <input
                value={form.skill_name}
                onChange={(event) => onFormChange({ skill_name: event.target.value })}
                className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
              />
            </label>
            <label className="min-w-0">
              <span className="text-xs font-medium text-muted-foreground">连接器名称</span>
              <input
                value={form.connector_name}
                onChange={(event) => onFormChange({ connector_name: event.target.value })}
                className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
              />
            </label>
            <label className="min-w-0">
              <span className="text-xs font-medium text-muted-foreground">类型</span>
              <select
                value={form.connector_type}
                onChange={(event) => onFormChange({ connector_type: event.target.value })}
                className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
              >
                <option value="http_api">http_api</option>
                <option value="mcp">mcp</option>
                <option value="database">database</option>
                <option value="webhook">webhook</option>
              </select>
            </label>
            <label className="min-w-0">
              <span className="text-xs font-medium text-muted-foreground">Endpoint</span>
              <input
                value={form.endpoint_url}
                onChange={(event) => onFormChange({ endpoint_url: event.target.value })}
                placeholder="https://provider.example/api"
                className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
              />
            </label>
            <label className="min-w-0">
              <span className="text-xs font-medium text-muted-foreground">认证</span>
              <select
                value={form.auth_type}
                onChange={(event) => onFormChange({ auth_type: event.target.value })}
                className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
              >
                <option value="api_key">api_key</option>
                <option value="bearer">bearer</option>
                <option value="basic">basic</option>
                <option value="none">none</option>
              </select>
            </label>
            <label className="min-w-0">
              <span className="text-xs font-medium text-muted-foreground">凭据动作</span>
              <select
                value={form.credential_mode}
                onChange={(event) => onFormChange({ credential_mode: event.target.value as SkillConnectorFormState['credential_mode'] })}
                className="mt-1 h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
              >
                <option value="preserve">保留</option>
                <option value="replace">替换</option>
                <option value="clear">清空</option>
              </select>
            </label>
            <div className="flex items-end gap-2">
              <button
                type="submit"
                disabled={busyKey === (editingId ?? 'connector:create')}
                className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busyKey === (editingId ?? 'connector:create') ? (
                  <icons.Loader2 className="h-4 w-4 animate-spin" />
                ) : editing ? (
                  <icons.Check className="h-4 w-4" />
                ) : (
                  <icons.Plus className="h-4 w-4" />
                )}
                {editing ? '更新' : '创建'}
              </button>
              {editing ? (
                <button
                  type="button"
                  onClick={onCancel}
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted"
                >
                  取消
                </button>
              ) : null}
            </div>
            <label className="min-w-0 xl:col-span-7">
              <span className="text-xs font-medium text-muted-foreground">凭据文本</span>
              <textarea
                value={form.credentials_text}
                disabled={credentialInputDisabled}
                onChange={(event) => onFormChange({ credentials_text: event.target.value })}
                placeholder="API_KEY=sk-...\nCLIENT_SECRET=..."
                className="mt-1 min-h-[82px] w-full resize-y rounded-lg border border-border bg-background px-3 py-2 font-mono text-sm text-foreground outline-none focus:border-primary disabled:bg-muted/40 disabled:text-muted-foreground"
              />
              <span className="mt-1 block text-xs text-muted-foreground">
                {editing && form.credential_mode === 'preserve'
                  ? '编辑元数据时不会发送 credentials，已保存密钥保持不变。'
                  : form.credential_mode === 'clear'
                    ? '保存后会发送空 credentials，用于清空已保存凭据。'
                    : `将提交 ${parsedCredentialCount} 个凭据键；保存后界面只显示键名。`}
              </span>
            </label>
            <label className="inline-flex items-center gap-2 text-sm text-foreground xl:col-span-7">
              <input
                type="checkbox"
                checked={form.is_enabled}
                onChange={(event) => onFormChange({ is_enabled: event.target.checked })}
                className="h-4 w-4 rounded border-border"
              />
              启用该连接器
            </label>
          </form>

          <div className="mt-4">
            {loading ? (
              <LoadingState variant="skeleton" rows={3} />
            ) : error ? (
              <ErrorState variant="card" message={error} onRetry={onRefresh} />
            ) : connectors.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border bg-muted/30 p-4 text-sm text-muted-foreground">
                暂无 Skill 连接器配置
              </div>
            ) : (
              <div className="grid gap-2 lg:grid-cols-2" data-testid="skill-connector-list">
                {connectors.map((connector) => (
                  <SkillConnectorRow
                    key={connector.id}
                    connector={connector}
                    busy={busyKey === connector.id}
                    editing={editingId === connector.id}
                    onEdit={() => onEdit(connector)}
                    onDelete={() => onDelete(connector)}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  )
}

function SkillConnectorRow({
  connector,
  busy,
  editing,
  onEdit,
  onDelete,
}: {
  connector: SkillConnectorConfig
  busy: boolean
  editing: boolean
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <article className={`min-w-0 rounded-lg border p-3 ${editing ? 'border-primary bg-primary/5' : 'border-border bg-muted/20'}`} data-testid={`skill-connector-row-${connector.id}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-foreground">{connector.connector_name}</h3>
            <span className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${
              connector.is_enabled
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-muted bg-background text-muted-foreground'
            }`}>
              {connector.is_enabled ? '启用' : '停用'}
            </span>
          </div>
          <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <Field label="Skill" value={connector.skill_name} />
            <Field label="类型" value={`${connector.connector_type}/${connector.auth_type}`} />
            <Field label="Endpoint" value={connector.endpoint_url || '未设置'} />
            <Field label="更新" value={formatDateTime(connector.updated_at)} />
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {connector.credential_keys.length === 0 ? (
              <span className="rounded-md border border-dashed border-border bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                未保存凭据
              </span>
            ) : connector.credential_keys.map((key) => (
              <span key={key} className="rounded-md border border-violet-200 bg-violet-50 px-2 py-0.5 text-[11px] font-semibold text-violet-700">
                {key}
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{summarizeConnectorCredentials(connector)}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={onEdit}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted"
          >
            <icons.Edit3 className="h-4 w-4" />
            编辑
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onDelete}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-destructive/20 bg-destructive/5 px-3 text-sm font-medium text-destructive hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy ? <icons.Loader2 className="h-4 w-4 animate-spin" /> : <icons.Trash2 className="h-4 w-4" />}
            删除
          </button>
        </div>
      </div>
    </article>
  )
}

function CapabilityRoutePolicyPanel({
  role,
  canManage,
  routes,
  loading,
  error,
  busyKey,
  onRefresh,
  onToggle,
}: {
  role: string
  canManage: boolean
  routes: AgentCapabilityRoutePolicy[]
  loading: boolean
  error: string | null
  busyKey: string | null
  onRefresh: () => void
  onToggle: (route: AgentCapabilityRoutePolicy) => void
}) {
  const enabledCount = routes.filter((route) => route.status === 'active' || route.status === 'enabled').length
  const disabledCount = routes.filter((route) => route.status === 'disabled').length

  return (
    <section className="rounded-lg border border-border bg-background p-4 shadow-sm" data-testid="capability-route-policy-panel">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700">
            <icons.Target className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-foreground">组织能力策略</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {normalizeRole(role)} · 启用 {enabledCount} · 禁用 {disabledCount}
            </p>
          </div>
        </div>
        {canManage ? (
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted"
          >
            <icons.RefreshCw className="h-4 w-4" />
            刷新
          </button>
        ) : null}
      </div>

      <div className="mt-4">
        {!canManage ? (
          <div className="rounded-lg border border-dashed border-border bg-muted/30 p-4 text-sm text-muted-foreground">
            当前角色只能查看基础与可申请能力，组织策略由老板或超级管理员维护
          </div>
        ) : loading ? (
          <LoadingState variant="skeleton" rows={3} />
        ) : error ? (
          <ErrorState variant="card" message={error} onRetry={onRefresh} />
        ) : routes.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-muted/30 p-4 text-sm text-muted-foreground">
            暂无组织能力路由
          </div>
        ) : (
          <div className="grid gap-2 lg:grid-cols-2" data-testid="capability-route-policy-list">
            {routes.slice(0, 8).map((route) => {
              const isActive = route.status === 'active' || route.status === 'enabled'
              return (
                <div key={route.id} className="flex min-h-[92px] min-w-0 items-start justify-between gap-3 rounded-lg border border-border bg-muted/20 p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-foreground">{route.route_key}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <span className="rounded-md border border-border bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                        {route.route_type}
                      </span>
                      <span className="rounded-md border border-border bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                        {route.risk_level}
                      </span>
                      <span className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${
                        isActive
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                          : 'border-muted bg-background text-muted-foreground'
                      }`}>
                        {isActive ? '启用' : '禁用'}
                      </span>
                    </div>
                    <p className="mt-2 truncate text-xs text-muted-foreground">
                      {route.allowed_scopes.length} scopes · {route.allowed_consumers.length} consumers
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={busyKey === route.route_key}
                    onClick={() => onToggle(route)}
                    data-testid={`capability-route-${route.route_key}-toggle`}
                    className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {busyKey === route.route_key ? (
                      <icons.Loader2 className="h-4 w-4 animate-spin" />
                    ) : isActive ? (
                      <icons.Ban className="h-4 w-4" />
                    ) : (
                      <icons.CheckCircle2 className="h-4 w-4" />
                    )}
                    {isActive ? '禁用' : '启用'}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}

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

function CapabilityPolicyPanel({
  agent,
  role,
  tools,
  availability,
  loading,
  error,
  onAgentChange,
  onRefresh,
}: {
  agent: string
  role: string
  tools: HarnessToolItem[]
  availability: HarnessAgentTools | null
  loading: boolean
  error: string | null
  onAgentChange: (agent: string) => void
  onRefresh: () => void
}) {
  const availableSet = new Set(availability?.available_tools ?? [])
  const visibleTools = tools.filter((tool) => canRoleSeeCapabilityTool(tool, role, availableSet.has(tool.name)))
  const availableCount = visibleTools.filter((tool) => availableSet.has(tool.name)).length
  const blockedCount = Math.max(visibleTools.length - availableCount, 0)
  const hiddenCount = Math.max(tools.length - visibleTools.length, 0)
  const approvalCount = visibleTools.filter((tool) => tool.requires_approval).length
  const fullVisibility = hasFullCapabilityVisibility(role)
  const visibilityLabel = roleVisibilityLabel(role)

  return (
    <section className="rounded-lg border border-border bg-background p-4 shadow-sm" data-testid="capability-policy-panel">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-sky-200 bg-sky-50 text-sky-700">
            <icons.Network className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-foreground">能力策略</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {availability?.agent ?? agent} · 可用 {availableCount} · 阻断 {blockedCount}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground" data-testid="capability-role-visibility">
              {normalizeRole(role)} · {visibilityLabel}
              {hiddenCount > 0 ? ` · 已隐藏 ${hiddenCount}` : ''}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={agent}
            onChange={(event) => onAgentChange(event.target.value)}
            className="h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
            aria-label="Agent"
          >
            {CAPABILITY_AGENT_OPTIONS.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted"
          >
            <icons.RefreshCw className="h-4 w-4" />
            刷新
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <MiniMetric label={fullVisibility ? '注册工具' : '可见工具'} value={visibleTools.length} icon={icons.Wrench} />
        <MiniMetric label="当前可用" value={availableCount} icon={icons.CheckCircle2} />
        <MiniMetric label="需审批" value={approvalCount} icon={icons.ShieldAlert} />
      </div>

      <div className="mt-4">
        {loading ? (
          <LoadingState variant="skeleton" rows={3} />
        ) : error ? (
          <ErrorState variant="card" message={error} onRetry={onRefresh} />
        ) : visibleTools.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-muted/30 p-4 text-sm text-muted-foreground">
            当前角色暂无可见能力
          </div>
        ) : (
          <div className="grid gap-2 lg:grid-cols-2" data-testid="capability-policy-tool-list">
            {visibleTools.slice(0, 8).map((tool) => {
              const isAvailable = availableSet.has(tool.name)
              const state = capabilityToolState(tool, isAvailable)
              return (
                <div key={tool.name} className="flex min-h-[76px] min-w-0 items-start justify-between gap-3 rounded-lg border border-border bg-muted/20 p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-foreground">
                      {tool.display_name || tool.name}
                    </p>
                    <p className="mt-1 break-words text-xs text-muted-foreground">
                      {tool.description || tool.name}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <span className="rounded-md border border-border bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                        {tool.risk_level || 'unknown'}
                      </span>
                      {tool.requires_approval ? (
                        <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                          approval
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <span className={`shrink-0 rounded-md border px-2 py-1 text-xs font-semibold ${
                    state === 'available'
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : state === 'requestable'
                        ? 'border-amber-200 bg-amber-50 text-amber-700'
                        : 'border-muted bg-background text-muted-foreground'
                  }`}>
                    {state === 'available' ? '可用' : state === 'requestable' ? '可申请' : '阻断'}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}

function MiniMetric({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: number
  icon: IconComponent
}) {
  return (
    <div className="flex min-h-[70px] items-center gap-3 rounded-lg border border-border bg-muted/20 p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background text-primary">
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-semibold text-foreground">{value}</p>
      </div>
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
  artifactOpen,
  artifactItems,
  artifactLoading,
  artifactBusy,
  artifactRevisionBusyId,
  artifactExporting,
  onApprove,
  onReject,
  onRevoke,
  onToggleAudit,
  onExportAudit,
  onControlWorkspace,
  onToggleArtifacts,
  onRecordArtifact,
  onReviewArtifact,
  onExportArtifacts,
}: {
  item: AgentApprovalItem
  busy: boolean
  auditOpen: boolean
  auditItems: AgentApprovalAuditEvent[]
  auditLoading: boolean
  auditExporting: boolean
  controlBusyKey: string | null
  artifactOpen: boolean
  artifactItems: AgentWorkspaceArtifact[]
  artifactLoading: boolean
  artifactBusy: boolean
  artifactRevisionBusyId: string | null
  artifactExporting: boolean
  onApprove: () => void
  onReject: () => void
  onRevoke: () => void
  onToggleAudit: () => void
  onExportAudit: () => void
  onControlWorkspace: (action: AgentWorkspaceControlAction) => void
  onToggleArtifacts: () => void
  onRecordArtifact: () => void
  onReviewArtifact: (artifact: AgentWorkspaceArtifact) => void
  onExportArtifacts: () => void
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
          <button
            type="button"
            disabled={artifactLoading}
            onClick={onToggleArtifacts}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
          >
            <icons.FileText className="h-4 w-4" />
            {artifactOpen ? '收起成果' : '成果'}
          </button>
          {item.status === 'approved' && (
            <>
              <button
                type="button"
                disabled={artifactBusy}
                onClick={onRecordArtifact}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              >
                <icons.Plus className="h-4 w-4" />
                添加成果
              </button>
              <button
                type="button"
                disabled={artifactExporting}
                onClick={onExportArtifacts}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              >
                <icons.Download className="h-4 w-4" />
                导出成果
              </button>
            </>
          )}
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
      {artifactOpen && (
        <WorkspaceArtifactTrail
          loading={artifactLoading}
          items={artifactItems}
          revisionBusyId={artifactRevisionBusyId}
          onReviewArtifact={onReviewArtifact}
        />
      )}
    </article>
  )
}

function WorkspaceArtifactTrail({
  loading,
  items,
  revisionBusyId,
  onReviewArtifact,
}: {
  loading: boolean
  items: AgentWorkspaceArtifact[]
  revisionBusyId: string | null
  onReviewArtifact: (artifact: AgentWorkspaceArtifact) => void
}) {
  if (loading) {
    return (
      <div className="mt-4 rounded-lg border border-dashed border-border bg-muted/30 p-3 text-sm text-muted-foreground">
        正在加载工作室成果...
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="mt-4 rounded-lg border border-dashed border-border bg-muted/30 p-3 text-sm text-muted-foreground">
        暂无工作室成果
      </div>
    )
  }

  return (
    <div className="mt-4 rounded-lg border border-border bg-muted/30 p-3" data-testid="agent-workspace-artifacts">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
        <icons.FileText className="h-4 w-4 text-primary" />
        工作室成果
      </div>
      <div className="space-y-2">
        {items.map((artifact) => (
          <article key={artifact.id} className="rounded-md bg-background px-3 py-2 text-xs text-muted-foreground">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">{artifact.title}</p>
                <p className="mt-0.5">
                  {artifact.artifact_type} · {formatDateTime(artifact.updated_at || artifact.created_at)}
                  {artifact.revision ? ` · r${artifact.revision}` : ''}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <p>actor {shortId(artifact.updated_by || artifact.created_by)}</p>
                <button
                  type="button"
                  disabled={revisionBusyId === artifact.id}
                  onClick={() => onReviewArtifact(artifact)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-2 text-xs font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <icons.Check className="h-3.5 w-3.5" />
                  复核
                </button>
              </div>
            </div>
            <dl className="mt-2 grid gap-2 sm:grid-cols-2">
              {payloadPreview(artifact.content).map(([key, value]) => (
                <div key={key} className="min-w-0 rounded-md bg-muted/50 px-2 py-1.5">
                  <dt className="text-[11px] font-medium text-muted-foreground">{key}</dt>
                  <dd className="mt-0.5 truncate text-foreground">{value}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>
    </div>
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
