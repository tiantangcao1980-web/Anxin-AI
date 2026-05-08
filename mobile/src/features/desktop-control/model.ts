import type { PrivacyMode } from '@/lib/privacy-mode'

export interface RemoteControlStatusResponse {
  available: boolean
  status: string
  desktop_device_id?: string | null
  pairing_id?: string | null
  queued_command_count?: number
  required_controls: string[]
  message: string
}

export interface RemoteControlPairingRequest {
  mobile_device_id: string
  desktop_device_id: string
  requested_scopes?: string[]
  privacy_mode?: string
  expires_in_seconds?: number
}

export interface RemoteControlPairingResponse {
  pairing_id: string
  mobile_device_id: string
  desktop_device_id: string
  requested_scopes: string[]
  privacy_mode: string
  status: string
  expires_at?: string | null
  confirmed_at?: string | null
}

export interface RemoteControlRouteTokenRequest {
  pairing_id: string
  ttl_seconds?: number
}

export interface RemoteControlRouteTokenResponse {
  allowed: boolean
  reason_code: string
  human_message: string
  route_token?: string | null
  route_id?: string | null
  pairing_id?: string | null
  required_scope: string
  route_key: string
  expires_at?: string | null
}

export interface RemoteControlCommandRequest {
  desktop_device_id: string
  command_type: string
  payload?: Record<string, unknown>
  pairing_id?: string | null
  route_token?: string | null
  privacy_mode?: string
  risk_level?: string
  second_confirmed?: boolean
  expires_in_seconds?: number
}

export interface RemoteControlCommandResponse {
  command_id: string
  pairing_id: string
  desktop_device_id: string
  command_type: string
  risk_level: string
  status: string
  route_id?: string | null
  route_consumer_id?: string | null
  route_scopes: string[]
  second_confirmed: boolean
  expires_at?: string | null
  claimed_at?: string | null
  claimed_by_host?: string | null
  started_at?: string | null
  completed_at?: string | null
  failed_at?: string | null
  failure_reason?: string | null
  result_summary?: Record<string, unknown> | null
  cancelled_at?: string | null
}

export interface RemoteControlCancelCommandRequest {
  reason: string
}

export interface RemoteControlAuditEvent {
  id: string
  pairing_id?: string | null
  command_id?: string | null
  action: string
  status: string
  reason_code?: string | null
  resource_snapshot?: Record<string, unknown> | null
  metadata?: Record<string, unknown> | null
  created_at?: string | null
}

export interface RemoteControlAuditEventsResponse {
  items: RemoteControlAuditEvent[]
  total: number
}

export type DesktopControlGateState = 'ready' | 'blocked' | 'not_configured' | 'error'

export interface DesktopControlGate {
  state: DesktopControlGateState
  icon: 'desktop-outline' | 'lock-closed-outline' | 'construct-outline' | 'warning-outline'
  title: string
  description: string
  canRequestPairing: boolean
  canSendSafeProbe: boolean
  desktopDeviceId?: string | null
  pairingId?: string | null
  queuedCommandCount: number
  requiredControls: string[]
}

const REQUIRED_CONTROL_LABELS: Record<string, string> = {
  device_pairing: '设备配对',
  desktop_confirmation: '桌面端确认',
  capability_route_token: '短期能力路由 token',
  second_confirmation_for_high_risk_commands: '高风险二次确认',
  command_expiry_and_revocation: '命令过期与撤销',
  audit_log: '审计日志',
}

const AUDIT_ACTION_LABELS: Record<string, string> = {
  'remote_control.pairing.request': '配对申请',
  'remote_control.pairing.confirm': '桌面确认配对',
  'remote_control.pairing.deny': '配对拒绝',
  'remote_control.command.enqueue': '命令入队',
  'remote_control.command.claim': '桌面领取命令',
  'remote_control.command.status': '桌面状态回传',
  'remote_control.command.cancel': '命令取消',
  'remote_control.command.expire': '命令过期',
}

const AUDIT_STATUS_LABELS: Record<string, string> = {
  success: '成功',
  denied: '拒绝',
  failed: '失败',
}

export function formatRemoteControlRequiredControl(control: string): string {
  return REQUIRED_CONTROL_LABELS[control] ?? control
}

export function formatRemoteControlAuditAction(action: string): string {
  return AUDIT_ACTION_LABELS[action] ?? action
}

export function formatRemoteControlAuditStatus(status: string): string {
  return AUDIT_STATUS_LABELS[status] ?? status
}

export function getDesktopControlLoadErrorMessage(error: unknown): string {
  const maybe = error as { message?: string } | null
  if (maybe?.message?.includes('本地模式')) {
    return '本地模式下已阻断远控状态检查'
  }
  if (maybe?.message?.includes('Network')) {
    return '网络连接失败，请稍后重试'
  }
  return maybe?.message || '无法读取桌面控制状态'
}

export function canCancelRemoteControlCommand(command?: RemoteControlCommandResponse | null): boolean {
  return command?.status === 'queued' || command?.status === 'claimed'
}

export function buildDesktopControlGate({
  privacyMode,
  status,
  errorMessage,
}: {
  privacyMode: PrivacyMode
  status?: RemoteControlStatusResponse | null
  errorMessage?: string | null
}): DesktopControlGate {
  if (privacyMode === 'local') {
    return {
      state: 'blocked',
      icon: 'lock-closed-outline',
      title: '本地模式已阻断远控',
      description: '当前模式不会连接云端或向桌面端外发远控请求。',
      canRequestPairing: false,
      canSendSafeProbe: false,
      queuedCommandCount: 0,
      requiredControls: [],
    }
  }

  if (errorMessage) {
    return {
      state: 'error',
      icon: 'warning-outline',
      title: '无法确认桌面控制状态',
      description: errorMessage,
      canRequestPairing: false,
      canSendSafeProbe: false,
      queuedCommandCount: 0,
      requiredControls: [],
    }
  }

  if (!status || !status.available) {
    return {
      state: 'not_configured',
      icon: 'construct-outline',
      title: '等待桌面端支持',
      description: status?.message || '桌面控制尚未完成配对、命令队列和审计闭环。',
      canRequestPairing: false,
      canSendSafeProbe: false,
      desktopDeviceId: status?.desktop_device_id,
      pairingId: status?.pairing_id,
      queuedCommandCount: status?.queued_command_count ?? 0,
      requiredControls: status?.required_controls.map(formatRemoteControlRequiredControl) ?? [],
    }
  }

  const hasSafeProbeTarget = Boolean(status.desktop_device_id && status.pairing_id)

  return {
    state: 'ready',
    icon: 'desktop-outline',
    title: hasSafeProbeTarget ? '可发送安全探针' : '等待配对信息同步',
    description: status.message || '桌面端已开放受治理的远控控制面。',
    canRequestPairing: true,
    canSendSafeProbe: hasSafeProbeTarget,
    desktopDeviceId: status.desktop_device_id,
    pairingId: status.pairing_id,
    queuedCommandCount: status.queued_command_count ?? 0,
    requiredControls: status.required_controls.map(formatRemoteControlRequiredControl),
  }
}
