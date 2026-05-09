declare const uni: {
  request(options: {
    url: string
    method?: string
    data?: unknown
    timeout?: number
    header?: Record<string, string>
    success?: (result: { statusCode: number; data: unknown }) => void
    fail?: (error: unknown) => void
  }): void
  login(options: {
    provider?: string
    success?: (result: { code?: string; errMsg?: string }) => void
    fail?: (error: unknown) => void
  }): void
  getStorageSync(key: string): unknown
  setStorageSync(key: string, value: unknown): void
  removeStorageSync(key: string): void
}
