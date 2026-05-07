import { describe, expect, it } from 'vitest'

import {
  buildDesktopWorkstationResources,
  getUnsafeEnabledTopSecretActions,
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
})
