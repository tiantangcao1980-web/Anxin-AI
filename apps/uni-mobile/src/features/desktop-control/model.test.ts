import { describe, expect, it } from 'vitest'
import { buildDesktopControlGate, canCancelRemoteControlCommand } from './model'

describe('uni-mobile desktop control gate', () => {
  it('blocks safe-probe actions in top-secret mode', () => {
    const gate = buildDesktopControlGate({
      privacyMode: 'top-secret',
      status: {
        available: true,
        status: 'ready',
        desktop_device_id: 'desktop-1',
        pairing_id: 'pair-1',
        required_controls: [],
        message: 'ready',
      },
    })

    expect(gate.state).toBe('blocked')
    expect(gate.canSendSafeProbe).toBe(false)
  })

  it('allows only safe-probe request readiness when desktop and pairing ids exist', () => {
    const gate = buildDesktopControlGate({
      privacyMode: 'hybrid',
      status: {
        available: true,
        status: 'ready',
        desktop_device_id: 'desktop-1',
        pairing_id: 'pair-1',
        required_controls: ['capability_route_token'],
        message: 'safe probe ready',
      },
    })

    expect(gate.state).toBe('ready')
    expect(gate.canRequestPairing).toBe(true)
    expect(gate.canSendSafeProbe).toBe(true)
    expect(gate.requiredControls).toEqual(['短期能力路由 token'])
  })

  it('can cancel only queued or claimed safe probes', () => {
    expect(canCancelRemoteControlCommand({ status: 'queued' } as never)).toBe(true)
    expect(canCancelRemoteControlCommand({ status: 'claimed' } as never)).toBe(true)
    expect(canCancelRemoteControlCommand({ status: 'completed' } as never)).toBe(false)
  })
})
