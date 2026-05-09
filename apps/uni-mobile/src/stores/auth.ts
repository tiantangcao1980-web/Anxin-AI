import { normalizePrivacyMode, type PrivacyMode } from '@/services/privacy'

export interface AuthUser {
  id: string
  email?: string | null
  role?: string | null
  organization_id?: string | null
}

export interface AuthSession {
  accessToken: string | null
  refreshToken: string | null
  user: AuthUser | null
  privacyMode: PrivacyMode
}

export function createEmptyAuthSession(): AuthSession {
  return {
    accessToken: null,
    refreshToken: null,
    user: null,
    privacyMode: 'cloud',
  }
}

export function normalizeAuthSession(input: Partial<AuthSession> = {}): AuthSession {
  return {
    accessToken: input.accessToken ?? null,
    refreshToken: input.refreshToken ?? null,
    user: input.user ?? null,
    privacyMode: normalizePrivacyMode(input.privacyMode),
  }
}

export function isAuthenticated(session: AuthSession): boolean {
  return Boolean(session.accessToken && session.user?.id)
}
