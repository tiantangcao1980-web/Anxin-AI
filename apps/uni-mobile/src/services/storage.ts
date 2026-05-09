import { normalizePrivacyMode, type PrivacyMode } from './privacy'

export interface UniStorageAdapter {
  get(key: string): unknown
  set(key: string, value: unknown): void
  remove(key: string): void
}

export const storageKeys = {
  accessToken: 'anxin.access_token',
  refreshToken: 'anxin.refresh_token',
  backendUrl: 'anxin.backend_url',
  privacyMode: 'anxin.privacy_mode',
} as const

export function createUniStorageAdapter(): UniStorageAdapter {
  return {
    get: (key) => uni.getStorageSync(key),
    set: (key, value) => uni.setStorageSync(key, value),
    remove: (key) => uni.removeStorageSync(key),
  }
}

export function getStoredPrivacyMode(storage: UniStorageAdapter): PrivacyMode {
  const value = storage.get(storageKeys.privacyMode)
  return normalizePrivacyMode(typeof value === 'string' ? value : (value as { mode?: unknown } | null)?.mode)
}

export function setStoredPrivacyMode(storage: UniStorageAdapter, mode: PrivacyMode): void {
  storage.set(storageKeys.privacyMode, mode)
}

export function clearStoredAuth(storage: UniStorageAdapter): void {
  storage.remove(storageKeys.accessToken)
  storage.remove(storageKeys.refreshToken)
}
