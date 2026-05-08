import AsyncStorage from '@react-native-async-storage/async-storage'

export type PrivacyMode = 'local' | 'hybrid' | 'cloud'

export const PRIVACY_MODE_STORAGE_KEY = 'anxin-privacy-mode'
export const DEFAULT_PRIVACY_MODE: PrivacyMode = 'cloud'

export function isPrivacyMode(value: unknown): value is PrivacyMode {
  return value === 'local' || value === 'hybrid' || value === 'cloud'
}

export async function getStoredPrivacyMode(): Promise<PrivacyMode> {
  try {
    const stored = await AsyncStorage.getItem(PRIVACY_MODE_STORAGE_KEY)
    return isPrivacyMode(stored) ? stored : DEFAULT_PRIVACY_MODE
  } catch {
    return DEFAULT_PRIVACY_MODE
  }
}

export async function setStoredPrivacyMode(mode: PrivacyMode): Promise<void> {
  await AsyncStorage.setItem(PRIVACY_MODE_STORAGE_KEY, mode)
}
