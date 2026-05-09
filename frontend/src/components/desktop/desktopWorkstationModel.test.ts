import { describe, expect, it } from 'vitest'

import {
  buildRemoteControlHostState,
  buildDesktopWorkstationResources,
  formatRemoteControlAuditAction,
  formatRemoteControlRequiredControl,
  getUnsafeEnabledTopSecretActions,
  normalizeWorkstationBackendUrl,
  type RemoteControlAuditEventSnapshot,
  type RemoteControlStatusSnapshot,
} from './desktopWorkstationModel'

describe('desktop workstation model', () => {
  it('does not expose unsafe outbound actions in top-secret mode', () => {
    const resources = buildDesktopWorkstationResources('top-secret')

    expect(getUnsafeEnabledTopSecretActions(resources)).toEqual([])
    expect(resources.find((item) => item.id === 'sync')).toMatchObject({
      status: 'blocked',
      action: { enabled: false },
    })
    expect(resources.find((item) => item.id === 'remote-control')).toMatchObject({
      status: 'blocked',
      action: { enabled: false },
    })
    expect(resources.find((item) => item.id === 'skills-mcp')).toMatchObject({
      status: 'restricted',
      action: { enabled: true, safeInTopSecret: true },
    })
  })

  it('opens governed connection actions outside top-secret mode', () => {
    const hybrid = buildDesktopWorkstationResources('hybrid')
    const cloud = buildDesktopWorkstationResources('cloud')

    expect(hybrid.find((item) => item.id === 'sync')?.action.enabled).toBe(true)
    expect(hybrid.find((item) => item.id === 'remote-control')?.status).toBe('pending')
    expect(cloud.find((item) => item.id === 'privacy')?.statusLabel).toBe('云端增强')
  })

  it('keeps desktop-only actions disabled in non-desktop preview', () => {
    const resources = buildDesktopWorkstationResources('hybrid', 'preview')

    expect(resources.find((item) => item.id === 'local-model')).toMatchObject({
      status: 'pending',
      action: { enabled: false },
    })
    expect(resources.find((item) => item.id === 'sync')).toMatchObject({
      status: 'pending',
      action: { enabled: false },
    })
    expect(resources.find((item) => item.id === 'remote-control')).toMatchObject({
      status: 'pending',
      action: { enabled: false },
    })
    expect(resources.find((item) => item.id === 'knowledge')?.action.enabled).toBe(true)
    expect(resources.find((item) => item.id === 'skills-mcp')?.action.enabled).toBe(true)
  })

  it('normalizes workstation backend URLs without accepting unsafe schemes', () => {
    expect(normalizeWorkstationBackendUrl(' http://localhost:8001/ ')).toEqual({
      ok: true,
      value: 'http://localhost:8001',
    })
    expect(normalizeWorkstationBackendUrl('https://api.anxin.example/v1/')).toEqual({
      ok: true,
      value: 'https://api.anxin.example/v1',
    })
    expect(normalizeWorkstationBackendUrl('local://api')).toMatchObject({
      ok: false,
    })
    expect(normalizeWorkstationBackendUrl('')).toMatchObject({
      ok: false,
    })
  })
})

describe('remote-control host state model', () => {
  const pendingStatus: RemoteControlStatusSnapshot = {
    available: false,
    status: 'pending_desktop_confirmation',
    desktop_device_id: 'desktop-device-123456',
    pairing_id: 'pairing-1234567890',
    queued_command_count: 0,
    required_controls: ['device_pairing', 'desktop_confirmation', 'audit_log'],
    message: '已有配对请求等待桌面端确认；确认前不会接受远控命令。',
  }

  const readyStatus: RemoteControlStatusSnapshot = {
    available: true,
    status: 'queue_ready_execution_pending',
    desktop_device_id: 'desktop-device-123456',
    pairing_id: 'pairing-1234567890',
    queued_command_count: 2,
    required_controls: ['capability_route_token', 'command_expiry_and_revocation', 'audit_log'],
    message: '远控控制面已具备已确认配对和命令队列；仍需桌面 host 拉取。',
  }

  it('keeps top-secret and preview states non-actionable', () => {
    const topSecret = buildRemoteControlHostState({
      mode: 'top-secret',
      runtime: 'desktop',
      loadState: 'ready',
      status: readyStatus,
    })
    const preview = buildRemoteControlHostState({
      mode: 'hybrid',
      runtime: 'preview',
      loadState: 'preview',
      status: readyStatus,
    })

    expect(topSecret).toMatchObject({
      state: 'blocked',
      canConfirmPairing: false,
      canRunHostCycle: false,
      canCancelCommand: false,
    })
    expect(preview).toMatchObject({
      state: 'preview',
      canConfirmPairing: false,
      canRunHostCycle: false,
      canCancelCommand: false,
    })
  })

  it('enables desktop pairing confirmation only for pending pairing snapshots', () => {
    const state = buildRemoteControlHostState({
      mode: 'hybrid',
      runtime: 'desktop',
      loadState: 'ready',
      status: pendingStatus,
    })

    expect(state.state).toBe('pending-confirmation')
    expect(state.statusLabel).toBe('待桌面确认')
    expect(state.canConfirmPairing).toBe(true)
    expect(state.canRunHostCycle).toBe(false)
    expect(state.scopeLabel).toContain('设备配对')
    expect(state.scopeLabel).toContain('桌面确认')
  })

  it('enables safe-probe host cycle and derives cancellable command from audit rows', () => {
    const auditEvents: RemoteControlAuditEventSnapshot[] = [
      {
        id: 'audit-2',
        action: 'remote_control.command.claim',
        status: 'success',
        reason_code: 'claimed',
        command_id: 'command-1234567890',
        created_at: '2026-05-09T08:20:00Z',
      },
      {
        id: 'audit-1',
        action: 'remote_control.command.enqueue',
        status: 'success',
        reason_code: 'queued',
        command_id: 'command-1234567890',
        created_at: '2026-05-09T08:19:00Z',
      },
    ]

    const state = buildRemoteControlHostState({
      mode: 'cloud',
      runtime: 'desktop',
      loadState: 'ready',
      status: readyStatus,
      auditEvents,
    })

    expect(state.state).toBe('ready')
    expect(state.canConfirmPairing).toBe(false)
    expect(state.canRunHostCycle).toBe(true)
    expect(state.canCancelCommand).toBe(true)
    expect(state.cancellableCommandId).toBe('command-1234567890')
    expect(state.executionLabel).toContain('2 条命令')
    expect(state.auditRows[0]).toMatchObject({
      title: '桌面领取命令',
      detail: '成功 · claimed',
      commandLabel: expect.stringContaining('命令'),
    })
  })

  it('does not offer cancellation once a terminal audit event exists for the command', () => {
    const auditEvents: RemoteControlAuditEventSnapshot[] = [
      {
        id: 'audit-3',
        action: 'remote_control.command.status_update',
        status: 'success',
        reason_code: 'completed',
        command_id: 'command-1234567890',
      },
      {
        id: 'audit-2',
        action: 'remote_control.command.claim',
        status: 'success',
        reason_code: 'claimed',
        command_id: 'command-1234567890',
      },
    ]

    const state = buildRemoteControlHostState({
      mode: 'hybrid',
      runtime: 'desktop',
      loadState: 'ready',
      status: readyStatus,
      auditEvents,
    })

    expect(state.canCancelCommand).toBe(false)
    expect(state.cancellableCommandId).toBeNull()
  })

  it('formats remote-control labels with stable fallbacks', () => {
    expect(formatRemoteControlRequiredControl('command_expiry_and_revocation')).toBe('命令过期/撤销')
    expect(formatRemoteControlRequiredControl('future_control')).toBe('future_control')
    expect(formatRemoteControlAuditAction('remote_control.command.cancel')).toBe('命令取消')
    expect(formatRemoteControlAuditAction('future.audit')).toBe('future.audit')
  })
})
