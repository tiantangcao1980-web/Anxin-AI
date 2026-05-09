export type WorkstationMode = 'top-secret' | 'hybrid' | 'cloud'
export type WorkstationRuntime = 'desktop' | 'preview'

export type WorkstationResourceStatus = 'ready' | 'available' | 'restricted' | 'blocked' | 'pending'
export type RemoteControlHostLoadState = 'preview' | 'loading' | 'ready' | 'error'
export type RemoteControlHostUiState =
  | 'blocked'
  | 'preview'
  | 'loading'
  | 'error'
  | 'not-configured'
  | 'pending-confirmation'
  | 'ready'

export interface WorkstationModeOption {
  mode: WorkstationMode
  label: string
  description: string
}

export interface WorkstationAction {
  label: string
  path: string
  enabled: boolean
  safeInTopSecret: boolean
  disabledReason?: string
}

export interface WorkstationResource {
  id: 'privacy' | 'local-model' | 'knowledge' | 'skills-mcp' | 'sync' | 'remote-control'
  title: string
  status: WorkstationResourceStatus
  statusLabel: string
  summary: string
  action: WorkstationAction
}

export interface RemoteControlStatusSnapshot {
  available: boolean
  status: string
  desktop_device_id?: string | null
  pairing_id?: string | null
  queued_command_count?: number | null
  required_controls?: string[] | null
  message?: string | null
}

export interface RemoteControlAuditEventSnapshot {
  id: string
  pairing_id?: string | null
  command_id?: string | null
  action: string
  status: string
  reason_code?: string | null
  created_at?: string | null
}

export interface RemoteControlHostAuditRow {
  id: string
  title: string
  detail: string
  timestamp: string
  commandLabel?: string
}

export interface RemoteControlHostState {
  state: RemoteControlHostUiState
  statusLabel: string
  title: string
  detail: string
  pairingLabel: string
  scopeLabel: string
  executionLabel: string
  auditLabel: string
  desktopDeviceId?: string | null
  pairingId?: string | null
  queuedCommandCount: number
  requiredControls: string[]
  auditRows: RemoteControlHostAuditRow[]
  canConfirmPairing: boolean
  canRunHostCycle: boolean
  canCancelCommand: boolean
  cancellableCommandId?: string | null
}

const TOP_SECRET_RESTRICTION = '绝密模式下默认不出站'
const DESKTOP_CLIENT_REQUIRED = '请在桌面客户端启用'
const REMOTE_CONTROL_READY_MESSAGE = '已具备配对与安全探针 host 回路'

const REMOTE_CONTROL_REQUIRED_CONTROL_LABELS: Record<string, string> = {
  device_pairing: '设备配对',
  desktop_confirmation: '桌面确认',
  capability_route_token: '短期能力路由',
  second_confirmation_for_high_risk_commands: '高风险二次确认',
  command_expiry_and_revocation: '命令过期/撤销',
  audit_log: '审计日志',
}

const REMOTE_CONTROL_AUDIT_ACTION_LABELS: Record<string, string> = {
  'remote_control.pairing.request': '配对申请',
  'remote_control.pairing.confirm': '桌面确认配对',
  'remote_control.pairing.deny': '配对拒绝',
  'remote_control.pairing.transition': '配对状态变更',
  'remote_control.command.enqueue': '命令入队',
  'remote_control.command.claim': '桌面领取命令',
  'remote_control.command.status': '桌面状态回传',
  'remote_control.command.status_update': '桌面状态回传',
  'remote_control.command.cancel': '命令取消',
  'remote_control.command.expire': '命令过期',
}

const REMOTE_CONTROL_AUDIT_STATUS_LABELS: Record<string, string> = {
  success: '成功',
  denied: '拒绝',
  failed: '失败',
}

const CANCELLABLE_REMOTE_COMMAND_REASONS = new Set(['queued', 'claimed'])
const TERMINAL_REMOTE_COMMAND_REASONS = new Set(['cancelled', 'completed', 'expired', 'failed'])

export const WORKSTATION_MODE_OPTIONS: WorkstationModeOption[] = [
  {
    mode: 'top-secret',
    label: '绝密',
    description: '本地闭环，默认阻断外部数据通道',
  },
  {
    mode: 'hybrid',
    label: '混合',
    description: '本地优先，按策略连接组织服务',
  },
  {
    mode: 'cloud',
    label: '云端',
    description: '完整云端协同与外部能力接入',
  },
]

export function buildDesktopWorkstationResources(
  mode: WorkstationMode,
  runtime: WorkstationRuntime = 'desktop'
): WorkstationResource[] {
  const isTopSecret = mode === 'top-secret'
  const isDesktopRuntime = runtime === 'desktop'

  return [
    {
      id: 'privacy',
      title: '隐私模式',
      status: mode === 'top-secret' ? 'ready' : 'available',
      statusLabel: mode === 'top-secret' ? '本地闭环' : mode === 'hybrid' ? '本地优先' : '云端增强',
      summary: mode === 'top-secret' ? '外部数据通道默认关闭' : '按组织策略启用连接',
      action: {
        label: '查看模式',
        path: '/settings?tab=workstation',
        enabled: true,
        safeInTopSecret: true,
      },
    },
    {
      id: 'local-model',
      title: '本地模型',
      status: isDesktopRuntime ? 'available' : 'pending',
      statusLabel: isDesktopRuntime ? '可配置' : '需桌面端',
      summary: isDesktopRuntime ? 'Ollama 与本地兼容端点' : '桌面客户端内配置本地模型',
      action: {
        label: '配置模型',
        path: '/private-llm',
        enabled: isDesktopRuntime,
        safeInTopSecret: true,
        disabledReason: isDesktopRuntime ? undefined : DESKTOP_CLIENT_REQUIRED,
      },
    },
    {
      id: 'knowledge',
      title: '独立知识库',
      status: 'available',
      statusLabel: isTopSecret ? '仅本地' : '可同步',
      summary: isTopSecret ? '使用已下载资料与本地索引' : '可连接组织资料与本地索引',
      action: {
        label: '打开知识库',
        path: '/knowledge-base',
        enabled: true,
        safeInTopSecret: true,
      },
    },
    {
      id: 'skills-mcp',
      title: 'Skills / MCP',
      status: isTopSecret ? 'restricted' : 'available',
      statusLabel: isTopSecret ? '审批后启用' : '可治理',
      summary: isTopSecret ? '外部连接保持关闭' : '按 allowlist 与审批策略连接',
      action: {
        label: isTopSecret ? '查看治理' : '配置服务',
        path: '/settings?tab=mcp',
        enabled: true,
        safeInTopSecret: true,
      },
    },
    {
      id: 'sync',
      title: '跨端同步',
      status: isTopSecret ? 'blocked' : isDesktopRuntime ? 'available' : 'pending',
      statusLabel: isTopSecret ? '已阻断' : isDesktopRuntime ? '可用' : '需桌面端',
      summary: isTopSecret
        ? TOP_SECRET_RESTRICTION
        : isDesktopRuntime
          ? '可同步任务、知识与工作记录'
          : '桌面客户端内查看同步状态',
      action: {
        label: '同步状态',
        path: '/sync-conflicts',
        enabled: !isTopSecret && isDesktopRuntime,
        safeInTopSecret: false,
        disabledReason: isTopSecret ? TOP_SECRET_RESTRICTION : isDesktopRuntime ? undefined : DESKTOP_CLIENT_REQUIRED,
      },
    },
    {
      id: 'remote-control',
      title: '移动远控桌面',
      status: isTopSecret ? 'blocked' : 'pending',
      statusLabel: isTopSecret ? '已阻断' : isDesktopRuntime ? '待验收' : '需桌面端',
      summary: isTopSecret
        ? TOP_SECRET_RESTRICTION
        : isDesktopRuntime
          ? '等待设备配对与命令审计证据'
          : '桌面客户端作为受控主机',
      action: {
        label: '查看任务',
        path: '/settings?tab=workstation',
        enabled: !isTopSecret && isDesktopRuntime,
        safeInTopSecret: false,
        disabledReason: isTopSecret ? TOP_SECRET_RESTRICTION : isDesktopRuntime ? undefined : DESKTOP_CLIENT_REQUIRED,
      },
    },
  ]
}

export function getUnsafeEnabledTopSecretActions(resources: WorkstationResource[]): WorkstationAction[] {
  return resources
    .map((resource) => resource.action)
    .filter((action) => action.enabled && !action.safeInTopSecret)
}

export function normalizeWorkstationBackendUrl(input: string): { ok: true; value: string } | { ok: false; error: string } {
  const trimmed = input.trim()
  if (!trimmed) {
    return { ok: false, error: '后端地址不能为空' }
  }

  let parsed: URL
  try {
    parsed = new URL(trimmed)
  } catch {
    return { ok: false, error: '请输入完整的 http:// 或 https:// 地址' }
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    return { ok: false, error: '后端地址只允许 http 或 https 协议' }
  }

  if (!parsed.hostname) {
    return { ok: false, error: '后端地址缺少主机名' }
  }

  return { ok: true, value: parsed.toString().replace(/\/$/, '') }
}

export function formatRemoteControlRequiredControl(control: string): string {
  return REMOTE_CONTROL_REQUIRED_CONTROL_LABELS[control] ?? control
}

export function formatRemoteControlAuditAction(action: string): string {
  return REMOTE_CONTROL_AUDIT_ACTION_LABELS[action] ?? action
}

export function formatRemoteControlAuditStatus(status: string): string {
  return REMOTE_CONTROL_AUDIT_STATUS_LABELS[status] ?? status
}

export function buildRemoteControlHostState({
  mode,
  runtime,
  loadState,
  status,
  auditEvents = [],
  errorMessage,
}: {
  mode: WorkstationMode
  runtime: WorkstationRuntime
  loadState: RemoteControlHostLoadState
  status?: RemoteControlStatusSnapshot | null
  auditEvents?: RemoteControlAuditEventSnapshot[]
  errorMessage?: string | null
}): RemoteControlHostState {
  if (mode === 'top-secret') {
    return baseRemoteControlHostState({
      state: 'blocked',
      statusLabel: '已阻断',
      title: '绝密模式阻断移动远控',
      detail: TOP_SECRET_RESTRICTION,
      pairingLabel: '不接受配对',
      scopeLabel: '外部控制关闭',
      executionLabel: '不领取命令',
      auditLabel: '不读取远控审计',
    })
  }

  if (runtime !== 'desktop') {
    return baseRemoteControlHostState({
      state: 'preview',
      statusLabel: '需桌面端',
      title: '桌面 host 未运行',
      detail: DESKTOP_CLIENT_REQUIRED,
      pairingLabel: '需桌面客户端',
      scopeLabel: '需桌面客户端',
      executionLabel: '需桌面客户端',
      auditLabel: '预览态',
    })
  }

  if (loadState === 'loading') {
    return baseRemoteControlHostState({
      state: 'loading',
      statusLabel: '检测中',
      title: '正在读取移动远控状态',
      detail: '读取配对、命令队列与审计状态',
      pairingLabel: '读取中',
      scopeLabel: '读取中',
      executionLabel: '读取中',
      auditLabel: '读取中',
    })
  }

  if (loadState === 'error') {
    return baseRemoteControlHostState({
      state: 'error',
      statusLabel: '读取失败',
      title: '远控状态不可用',
      detail: errorMessage || '无法读取远控控制面状态',
      pairingLabel: '读取失败',
      scopeLabel: '读取失败',
      executionLabel: '暂停操作',
      auditLabel: '读取失败',
    })
  }

  const queuedCommandCount = Number(status?.queued_command_count ?? 0)
  const requiredControls = (status?.required_controls ?? []).map(formatRemoteControlRequiredControl)
  const auditRows = auditEvents.slice(0, 6).map(formatRemoteControlAuditRow)
  const cancellableCommandId = findCancellableRemoteControlCommandId(auditEvents)
  const pairingId = status?.pairing_id ?? null
  const desktopDeviceId = status?.desktop_device_id ?? null
  const canConfirmPairing = status?.status === 'pending_desktop_confirmation' && Boolean(pairingId && desktopDeviceId)
  const canRunHostCycle = Boolean(status?.available && pairingId && desktopDeviceId)

  if (status?.status === 'pending_desktop_confirmation') {
    return {
      state: 'pending-confirmation',
      statusLabel: '待桌面确认',
      title: '有配对请求等待确认',
      detail: status.message || '确认前不会接受远控命令',
      pairingLabel: maskRemoteId(pairingId, '待确认配对'),
      scopeLabel: requiredControls.length ? requiredControls.join(' / ') : '桌面确认后生效',
      executionLabel: '确认前不领取命令',
      auditLabel: auditRows.length ? `${auditRows.length} 条审计` : '暂无审计事件',
      desktopDeviceId,
      pairingId,
      queuedCommandCount,
      requiredControls,
      auditRows,
      canConfirmPairing,
      canRunHostCycle: false,
      canCancelCommand: Boolean(cancellableCommandId),
      cancellableCommandId,
    }
  }

  if (status?.available) {
    return {
      state: 'ready',
      statusLabel: '可安全探针',
      title: REMOTE_CONTROL_READY_MESSAGE,
      detail: status.message || '远控控制面可进行 safe-probe host cycle',
      pairingLabel: maskRemoteId(pairingId, '已确认配对'),
      scopeLabel: requiredControls.length ? requiredControls.join(' / ') : 'desktop:control',
      executionLabel: queuedCommandCount > 0 ? `${queuedCommandCount} 条命令待 host 领取` : '暂无待领取命令',
      auditLabel: auditRows.length ? `${auditRows.length} 条审计` : '暂无审计事件',
      desktopDeviceId,
      pairingId,
      queuedCommandCount,
      requiredControls,
      auditRows,
      canConfirmPairing: false,
      canRunHostCycle,
      canCancelCommand: Boolean(cancellableCommandId),
      cancellableCommandId,
    }
  }

  return {
    state: 'not-configured',
    statusLabel: '未配对',
    title: '等待移动端配对',
    detail: status?.message || '移动远控桌面尚未创建持久化配对',
    pairingLabel: '未发现配对',
    scopeLabel: requiredControls.length ? requiredControls.join(' / ') : '等待后端状态',
    executionLabel: '无待领取命令',
    auditLabel: auditRows.length ? `${auditRows.length} 条审计` : '暂无审计事件',
    desktopDeviceId,
    pairingId,
    queuedCommandCount,
    requiredControls,
    auditRows,
    canConfirmPairing: false,
    canRunHostCycle: false,
    canCancelCommand: Boolean(cancellableCommandId),
    cancellableCommandId,
  }
}

function baseRemoteControlHostState(input: Omit<
  RemoteControlHostState,
  | 'desktopDeviceId'
  | 'pairingId'
  | 'queuedCommandCount'
  | 'requiredControls'
  | 'auditRows'
  | 'canConfirmPairing'
  | 'canRunHostCycle'
  | 'canCancelCommand'
  | 'cancellableCommandId'
>): RemoteControlHostState {
  return {
    ...input,
    desktopDeviceId: null,
    pairingId: null,
    queuedCommandCount: 0,
    requiredControls: [],
    auditRows: [],
    canConfirmPairing: false,
    canRunHostCycle: false,
    canCancelCommand: false,
    cancellableCommandId: null,
  }
}

function formatRemoteControlAuditRow(event: RemoteControlAuditEventSnapshot): RemoteControlHostAuditRow {
  const action = formatRemoteControlAuditAction(event.action)
  const status = formatRemoteControlAuditStatus(event.status)
  const reason = event.reason_code ? ` · ${event.reason_code}` : ''
  const commandLabel = event.command_id ? `命令 ${maskRemoteId(event.command_id, '未知')}` : undefined

  return {
    id: event.id,
    title: action,
    detail: `${status}${reason}`,
    timestamp: event.created_at ? formatAuditTime(event.created_at) : '时间未记录',
    commandLabel,
  }
}

function findCancellableRemoteControlCommandId(events: RemoteControlAuditEventSnapshot[]): string | null {
  const terminalCommandIds = new Set<string>()
  for (const event of events) {
    const commandId = normalizeOptionalString(event.command_id)
    if (!commandId) continue
    const reason = normalizeOptionalString(event.reason_code)?.toLowerCase()
    if (
      TERMINAL_REMOTE_COMMAND_REASONS.has(reason ?? '')
      || event.action === 'remote_control.command.cancel'
      || event.action === 'remote_control.command.expire'
    ) {
      terminalCommandIds.add(commandId)
    }
  }

  for (const event of events) {
    const commandId = normalizeOptionalString(event.command_id)
    if (!commandId || terminalCommandIds.has(commandId)) continue
    const reason = normalizeOptionalString(event.reason_code)?.toLowerCase()
    if (
      CANCELLABLE_REMOTE_COMMAND_REASONS.has(reason ?? '')
      || event.action === 'remote_control.command.enqueue'
      || event.action === 'remote_control.command.claim'
    ) {
      return commandId
    }
  }

  return null
}

function maskRemoteId(value: string | null | undefined, fallback: string): string {
  const normalized = normalizeOptionalString(value)
  if (!normalized) return fallback
  if (normalized.length <= 10) return normalized
  return `${normalized.slice(0, 6)}…${normalized.slice(-4)}`
}

function normalizeOptionalString(value: string | null | undefined): string | null {
  const normalized = value?.trim()
  return normalized ? normalized : null
}

function formatAuditTime(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
