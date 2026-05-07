import { describe, expect, it } from 'vitest'

import { normalizeSettingsTab } from './settingsTabs'

describe('settings tab normalization', () => {
  it('keeps supported settings tabs addressable', () => {
    expect(normalizeSettingsTab('workstation')).toBe('workstation')
    expect(normalizeSettingsTab('mcp')).toBe('mcp')
    expect(normalizeSettingsTab('notifications')).toBe('notifications')
  })

  it('maps legacy privacy links to the workstation tab', () => {
    expect(normalizeSettingsTab('privacy')).toBe('workstation')
  })

  it('falls back unknown or empty tabs to profile', () => {
    expect(normalizeSettingsTab(null)).toBe('profile')
    expect(normalizeSettingsTab('')).toBe('profile')
    expect(normalizeSettingsTab('billing')).toBe('profile')
  })
})
