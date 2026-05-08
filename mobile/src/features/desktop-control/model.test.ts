import { describe, expect, it } from 'vitest'
import {
  buildDesktopControlGate,
  canCancelRemoteControlCommand,
  formatRemoteControlAuditAction,
  formatRemoteControlAuditStatus,
  formatRemoteControlRequiredControl,
  getDesktopControlLoadErrorMessage,
  type RemoteControlCommandResponse,
  type RemoteControlStatusResponse,
} from './model'

const notConfiguredStatus: RemoteControlStatusResponse = {
  available: false,
  status: 'not_configured',
  desktop_device_id: 'desktop-a',
  pairing_id: null,
  queued_command_count: 0,
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
    expect(gate.canSendSafeProbe).toBe(false)
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
        pairing_id: 'pairing-a',
        message: '桌面端已开放远控配对申请。',
      },
    })

    expect(gate.state).toBe('ready')
    expect(gate.canRequestPairing).toBe(true)
    expect(gate.canSendSafeProbe).toBe(true)
    expect(gate.desktopDeviceId).toBe('desktop-a')
    expect(gate.pairingId).toBe('pairing-a')
  })

  it('does not enable safe probe when the ready status is missing target identifiers', () => {
    const gate = buildDesktopControlGate({
      privacyMode: 'cloud',
      status: {
        ...notConfiguredStatus,
        available: true,
        status: 'ready',
        desktop_device_id: null,
        pairing_id: null,
        message: '桌面端已开放远控配对申请。',
      },
    })

    expect(gate.state).toBe('ready')
    expect(gate.canRequestPairing).toBe(true)
    expect(gate.canSendSafeProbe).toBe(false)
    expect(gate.title).toBe('等待配对信息同步')
  })

  it('uses explicit error copy when status loading fails', () => {
    const gate = buildDesktopControlGate({
      privacyMode: 'hybrid',
      errorMessage: '网络连接失败，请稍后重试',
    })

    expect(gate.state).toBe('error')
    expect(gate.canRequestPairing).toBe(false)
    expect(gate.canSendSafeProbe).toBe(false)
  })
})

describe('formatRemoteControlRequiredControl', () => {
  it('maps known controls and keeps unknown controls inspectable', () => {
    expect(formatRemoteControlRequiredControl('command_expiry_and_revocation')).toBe('命令过期与撤销')
    expect(formatRemoteControlRequiredControl('future_control')).toBe('future_control')
  })
})

describe('formatRemoteControlAuditAction', () => {
  it('maps known audit actions and keeps unknown actions inspectable', () => {
    expect(formatRemoteControlAuditAction('remote_control.command.enqueue')).toBe('命令入队')
    expect(formatRemoteControlAuditAction('future.audit')).toBe('future.audit')
  })
})

describe('formatRemoteControlAuditStatus', () => {
  it('maps known audit status values and keeps unknown values inspectable', () => {
    expect(formatRemoteControlAuditStatus('success')).toBe('成功')
    expect(formatRemoteControlAuditStatus('future_status')).toBe('future_status')
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

describe('canCancelRemoteControlCommand', () => {
  const command: RemoteControlCommandResponse = {
    command_id: 'command-a',
    pairing_id: 'pairing-a',
    desktop_device_id: 'desktop-a',
    command_type: 'desktop.status_probe',
    risk_level: 'l2',
    status: 'queued',
    route_scopes: ['desktop:control'],
    second_confirmed: false,
  }

  it('allows cancellation only before terminal execution states', () => {
    expect(canCancelRemoteControlCommand(command)).toBe(true)
    expect(canCancelRemoteControlCommand({ ...command, status: 'claimed' })).toBe(true)
    expect(canCancelRemoteControlCommand({ ...command, status: 'running' })).toBe(false)
    expect(canCancelRemoteControlCommand({ ...command, status: 'completed' })).toBe(false)
    expect(canCancelRemoteControlCommand({ ...command, status: 'failed' })).toBe(false)
    expect(canCancelRemoteControlCommand({ ...command, status: 'cancelled' })).toBe(false)
  })
})
