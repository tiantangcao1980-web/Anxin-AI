import { describe, expect, it } from 'vitest'
import {
  buildDesktopControlGate,
  formatRemoteControlRequiredControl,
  getDesktopControlLoadErrorMessage,
  type RemoteControlStatusResponse,
} from './model'

const notConfiguredStatus: RemoteControlStatusResponse = {
  available: false,
  status: 'not_configured',
  desktop_device_id: 'desktop-a',
  required_controls: [
    'device_pairing',
    'desktop_confirmation',
    'capability_route_token',
    'audit_log',
  ],
  message: '移动远控桌面尚未配置持久化设备配对、命令队列、撤销和审计闭环，默认不可用。',
}

describe('buildDesktopControlGate', () => {
  it('blocks remote-control status checks in local privacy mode', () => {
    const gate = buildDesktopControlGate({
      privacyMode: 'local',
      status: notConfiguredStatus,
    })

    expect(gate).toMatchObject({
      state: 'blocked',
      canRequestPairing: false,
      title: '本地模式已阻断远控',
    })
    expect(gate.requiredControls).toEqual([])
  })

  it('keeps not-configured backend status as disabled UI', () => {
    const gate = buildDesktopControlGate({
      privacyMode: 'hybrid',
      status: notConfiguredStatus,
    })

    expect(gate.state).toBe('not_configured')
    expect(gate.canRequestPairing).toBe(false)
    expect(gate.requiredControls).toEqual([
      '设备配对',
      '桌面端确认',
      '短期能力路由 token',
      '审计日志',
    ])
  })

  it('allows pairing only when the backend declares the control plane available', () => {
    const gate = buildDesktopControlGate({
      privacyMode: 'cloud',
      status: {
        ...notConfiguredStatus,
        available: true,
        status: 'ready',
        message: '桌面端已开放远控配对申请。',
      },
    })

    expect(gate.state).toBe('ready')
    expect(gate.canRequestPairing).toBe(true)
  })

  it('uses explicit error copy when status loading fails', () => {
    const gate = buildDesktopControlGate({
      privacyMode: 'hybrid',
      errorMessage: '网络连接失败，请稍后重试',
    })

    expect(gate.state).toBe('error')
    expect(gate.canRequestPairing).toBe(false)
  })
})

describe('formatRemoteControlRequiredControl', () => {
  it('maps known controls and keeps unknown controls inspectable', () => {
    expect(formatRemoteControlRequiredControl('command_expiry_and_revocation')).toBe('命令过期与撤销')
    expect(formatRemoteControlRequiredControl('future_control')).toBe('future_control')
  })
})

describe('getDesktopControlLoadErrorMessage', () => {
  it('normalizes local-mode and network failures', () => {
    expect(getDesktopControlLoadErrorMessage(new Error('本地模式下禁止连接云端服务'))).toBe(
      '本地模式下已阻断远控状态检查',
    )
    expect(getDesktopControlLoadErrorMessage(new Error('Network request failed'))).toBe(
      '网络连接失败，请稍后重试',
    )
  })
})
