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
  // 导航
  navigateTo(options: { url: string; success?: () => void; fail?: (err: unknown) => void }): void
  redirectTo(options: { url: string }): void
  reLaunch(options: { url: string }): void
  switchTab(options: { url: string }): void
  navigateBack(options?: { delta?: number }): void
  // UI
  showToast(options: {
    title: string
    icon?: 'success' | 'error' | 'loading' | 'none'
    duration?: number
  }): void
  showModal(options: {
    title?: string
    content?: string
    showCancel?: boolean
    confirmText?: string
    cancelText?: string
    success?: (res: { confirm: boolean; cancel: boolean }) => void
  }): void
  showLoading(options: { title?: string; mask?: boolean }): void
  hideLoading(): void
  // 导航栏
  setNavigationBarTitle(options: { title: string }): void
}

declare function getCurrentPages(): Array<{ options?: Record<string, string>; route?: string }>
