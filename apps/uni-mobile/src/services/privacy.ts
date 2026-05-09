export type PrivacyMode = 'local' | 'hybrid' | 'cloud' | 'top-secret'

export class UniPrivacyNetworkBlockedError extends Error {
  constructor(message = '当前隐私模式已阻止联网请求') {
    super(message)
    this.name = 'UniPrivacyNetworkBlockedError'
  }
}

export function normalizePrivacyMode(value: unknown): PrivacyMode {
  return value === 'local' || value === 'hybrid' || value === 'cloud' || value === 'top-secret'
    ? value
    : 'cloud'
}

export function isDataNetworkBlockedMode(mode: PrivacyMode): boolean {
  return mode === 'local' || mode === 'top-secret'
}

export function assertDataNetworkAllowed(mode: PrivacyMode): void {
  if (isDataNetworkBlockedMode(mode)) {
    throw new UniPrivacyNetworkBlockedError()
  }
}

export function privacyHeaders(mode: PrivacyMode): Record<string, string> {
  return { 'X-Privacy-Mode': mode }
}
