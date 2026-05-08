import Taro from '@tarojs/taro'

declare const TARO_APP_API_BASE: string | undefined
const BASE_URL = (typeof TARO_APP_API_BASE !== 'undefined' ? TARO_APP_API_BASE : '') || 'http://localhost:8001/api/v1'
const REQUEST_TIMEOUT = 30000
const PRIVACY_MODE_STORAGE_KEY = 'anxin-privacy-mode'
const DEFAULT_PRIVACY_MODE: MiniProgramPrivacyMode = 'cloud'

export type MiniProgramPrivacyMode = 'local' | 'hybrid' | 'cloud' | 'top-secret'

const DATA_NETWORK_BLOCKED_MODES = new Set<MiniProgramPrivacyMode>(['local', 'top-secret'])

interface ApiResponse<T = any> {
  code: number
  data: T
  message: string
  request_id: string
}

function isApiResponse<T>(body: unknown): body is ApiResponse<T> {
  return !!body && typeof body === 'object' && 'code' in body && 'data' in body
}

function getErrorMessage(body: any, fallback: string): string {
  return body?.detail || body?.message || body?.errmsg || fallback
}

function unwrapResponse<T>(body: unknown): T {
  if (isApiResponse<T>(body)) {
    if (body.code !== 200) throw new Error(body.message || '请求失败')
    return body.data
  }
  return body as T
}

// token 刷新锁，防止并发刷新
let refreshPromise: Promise<string> | null = null

class MiniProgramAuthExpiredError extends Error {
  constructor(message = '登录已过期') {
    super(message)
    this.name = 'MiniProgramAuthExpiredError'
  }
}

class MiniProgramRefreshUnavailableError extends Error {
  constructor(message = '暂时无法刷新登录状态，请稍后重试') {
    super(message)
    this.name = 'MiniProgramRefreshUnavailableError'
  }
}

export class MiniProgramPrivacyNetworkBlockedError extends Error {
  constructor(message = '当前隐私模式已阻止小程序联网请求') {
    super(message)
    this.name = 'MiniProgramPrivacyNetworkBlockedError'
  }
}

function normalizePrivacyMode(value: unknown): MiniProgramPrivacyMode {
  return value === 'local' || value === 'hybrid' || value === 'cloud' || value === 'top-secret'
    ? value
    : DEFAULT_PRIVACY_MODE
}

export function getStoredPrivacyMode(): MiniProgramPrivacyMode {
  try {
    const value = Taro.getStorageSync(PRIVACY_MODE_STORAGE_KEY)
    return normalizePrivacyMode(typeof value === 'string' ? value : value?.mode)
  } catch {
    return DEFAULT_PRIVACY_MODE
  }
}

export function setStoredPrivacyMode(mode: MiniProgramPrivacyMode): void {
  Taro.setStorageSync(PRIVACY_MODE_STORAGE_KEY, mode)
}

export function isMiniProgramDataNetworkBlockedMode(mode: MiniProgramPrivacyMode): boolean {
  return DATA_NETWORK_BLOCKED_MODES.has(mode)
}

export function assertMiniProgramDataNetworkAllowed(mode = getStoredPrivacyMode()): void {
  if (isMiniProgramDataNetworkBlockedMode(mode)) {
    throw new MiniProgramPrivacyNetworkBlockedError()
  }
}

export function isMiniProgramPrivacyNetworkBlockedError(
  error: unknown,
): error is MiniProgramPrivacyNetworkBlockedError {
  return error instanceof MiniProgramPrivacyNetworkBlockedError
}

function privacyHeaders(mode: MiniProgramPrivacyMode): Record<string, string> {
  return { 'X-Privacy-Mode': mode }
}

function isRefreshAuthFailure(statusCode: number, code?: number): boolean {
  return statusCode === 401 || statusCode === 403 || code === 401 || code === 403
}

function isAuthExpiredError(error: unknown): error is MiniProgramAuthExpiredError {
  return error instanceof MiniProgramAuthExpiredError
}

function clearStoredAuth(): void {
  Taro.removeStorageSync('token')
  Taro.removeStorageSync('refresh_token')
}

async function refreshToken(): Promise<string> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    const privacyMode = getStoredPrivacyMode()
    assertMiniProgramDataNetworkAllowed(privacyMode)
    const rt = Taro.getStorageSync('refresh_token')
    if (!rt) {
      clearStoredAuth()
      throw new MiniProgramAuthExpiredError()
    }
    try {
      const res = await Taro.request({
        url: `${BASE_URL}/auth/refresh`,
        method: 'POST',
        data: { refresh_token: rt },
        timeout: 10000,
        header: privacyHeaders(privacyMode),
      })
      const apiCode = isApiResponse(res.data) ? res.data.code : undefined
      if (isRefreshAuthFailure(res.statusCode, apiCode)) {
        clearStoredAuth()
        throw new MiniProgramAuthExpiredError(getErrorMessage(res.data, '登录已过期'))
      }
      if (res.statusCode < 200 || res.statusCode >= 300) {
        throw new MiniProgramRefreshUnavailableError(getErrorMessage(res.data, '刷新登录失败'))
      }
      const body = unwrapResponse<{ access_token: string; refresh_token?: string }>(res.data)
      Taro.setStorageSync('token', body.access_token)
      if (body.refresh_token) {
        Taro.setStorageSync('refresh_token', body.refresh_token)
      }
      return body.access_token
    } catch (error) {
      if (isAuthExpiredError(error) || error instanceof MiniProgramRefreshUnavailableError) {
        throw error
      }
      throw new MiniProgramRefreshUnavailableError()
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

export async function request<T>(options: {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
  retry?: number
}): Promise<T> {
  const { url, method = 'GET', data, retry = 2 } = options

  for (let attempt = 0; attempt <= retry; attempt++) {
    try {
      const privacyMode = getStoredPrivacyMode()
      assertMiniProgramDataNetworkAllowed(privacyMode)
      const token = Taro.getStorageSync('token')
      const res = await Taro.request({
        url: `${BASE_URL}${url}`,
        method: method as any,
        data,
        timeout: REQUEST_TIMEOUT,
        header: {
          'Content-Type': 'application/json',
          ...privacyHeaders(privacyMode),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      const body = res.data as any

      // 401: 尝试刷新 token
      if (res.statusCode === 401 || body?.code === 401) {
        if (attempt < retry) {
          try {
            await refreshToken()
            continue // 用新 token 重试
          } catch (error) {
            if (isAuthExpiredError(error)) {
              Taro.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
              throw new Error('登录已过期')
            }
            Taro.showToast({ title: '网络异常，暂时无法刷新登录', icon: 'none' })
            throw error instanceof Error ? error : new Error('暂时无法刷新登录状态，请稍后重试')
          }
        }
      }

      if (res.statusCode < 200 || res.statusCode >= 300) {
        throw new Error(getErrorMessage(body, '请求失败'))
      }
      return unwrapResponse<T>(body)
    } catch (e: any) {
      // 网络错误（超时、连接失败等），指数退避重试
      const isNetworkError =
        e.errMsg?.includes('timeout') ||
        e.errMsg?.includes('fail') ||
        e.errMsg?.includes('abort')
      if (isNetworkError && attempt < retry) {
        await new Promise((r) => setTimeout(r, 1000 * Math.pow(2, attempt)))
        continue
      }
      throw e
    }
  }
  throw new Error('请求失败')
}

// 便捷方法
export const api = {
  get: <T>(url: string) => request<T>({ url, method: 'GET' }),
  post: <T>(url: string, data?: any) => request<T>({ url, method: 'POST', data }),
  put: <T>(url: string, data?: any) => request<T>({ url, method: 'PUT', data }),
  delete: <T>(url: string) => request<T>({ url, method: 'DELETE' }),
}
