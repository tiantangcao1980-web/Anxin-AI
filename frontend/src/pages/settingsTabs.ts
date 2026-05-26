export const SETTINGS_TABS = ['profile', 'workstation', 'notifications', 'about'] as const

const SETTINGS_TAB_SET = new Set<string>(SETTINGS_TABS)

export function normalizeSettingsTab(tab: string | null): string {
  if (tab === 'privacy') return 'workstation'
  if (tab && SETTINGS_TAB_SET.has(tab)) return tab
  return 'profile'
}
