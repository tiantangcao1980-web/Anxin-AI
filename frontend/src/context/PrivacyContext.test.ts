import { describe, expect, it } from 'vitest'
import { desktopAppModeToPrivacyMode, PrivacyMode } from './PrivacyContext'

describe('desktopAppModeToPrivacyMode', () => {
  it('maps desktop top-secret mode to local privacy gates', () => {
    expect(desktopAppModeToPrivacyMode('top-secret')).toBe(PrivacyMode.LOCAL)
  })

  it('preserves hybrid and cloud desktop modes', () => {
    expect(desktopAppModeToPrivacyMode('hybrid')).toBe(PrivacyMode.HYBRID)
    expect(desktopAppModeToPrivacyMode('cloud')).toBe(PrivacyMode.CLOUD)
  })

  it('fails back to hybrid for unknown desktop mode values', () => {
    expect(desktopAppModeToPrivacyMode('unknown')).toBe(PrivacyMode.HYBRID)
    expect(desktopAppModeToPrivacyMode(null)).toBe(PrivacyMode.HYBRID)
  })
})
