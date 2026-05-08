import type { PrivacyMode } from '@/lib/privacy-mode'

export interface RemoteControlStatusResponse {
  available: boolean
  status: string
  desktop_device_id?: string | null
  required_controls: string[]
  message: string
}

export type DesktopControlGateState = 'ready' | 'blocked' | 'not_configured' | 'error'

export interface DesktopControlGate {
  state: DesktopControlGateState
  icon: 'desktop-outline' | 'lock-closed-outline' | 'construct-outline' | 'warning-outline'
  title: string
  description: string
  canRequestPairing: boolean
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
      requiredControls: status?.required_controls.map(formatRemoteControlRequiredControl) ?? [],
    }
  }

  return {
    state: 'ready',
    icon: 'desktop-outline',
    title: '可申请桌面配对',
    description: status.message || '桌面端已开放远控配对申请。',
    canRequestPairing: true,
    requiredControls: status.required_controls.map(formatRemoteControlRequiredControl),
  }
}
