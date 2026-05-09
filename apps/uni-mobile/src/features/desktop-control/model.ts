import type { PrivacyMode } from '@/services/privacy'

export interface RemoteControlStatusResponse {
  available: boolean
  status: string
  desktop_device_id?: string | null
  pairing_id?: string | null
  queued_command_count?: number
  required_controls: string[]
  message: string
}

export interface RemoteControlCommandResponse {
  command_id: string
  pairing_id: string
  desktop_device_id: string
  command_type: string
  risk_level: string
  status: string
  route_scopes: string[]
  second_confirmed: boolean
}

export type DesktopControlGateState = 'ready' | 'blocked' | 'not_configured' | 'error'

export interface DesktopControlGate {
  state: DesktopControlGateState
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

export function formatRemoteControlRequiredControl(control: string): string {
  return REQUIRED_CONTROL_LABELS[control] ?? control
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
  if (privacyMode === 'local' || privacyMode === 'top-secret') {
    return {
      state: 'blocked',
      title: '当前模式已阻断远控',
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
