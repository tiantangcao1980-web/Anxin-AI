import { assertDataNetworkAllowed, privacyHeaders, type PrivacyMode } from './privacy'
import {
  clearStoredAuth,
  createUniStorageAdapter,
  getStoredPrivacyMode,
  storageKeys,
  type UniStorageAdapter,
} from './storage'

const DEFAULT_BASE_URL = 'https://api.anxinlegal.com/api/v1'
const REQUEST_TIMEOUT = 30000

export interface ApiResponse<T> {
  code: number
  data: T
  message?: string
  request_id?: string
}

export interface UniRequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  timeout?: number
  header?: Record<string, string>
}

export interface UniRequestResult {
  statusCode: number
  data: unknown
}

export type UniRequestAdapter = (options: UniRequestOptions) => Promise<UniRequestResult>

export interface ApiClientOptions {
  baseUrl?: string
  storage?: UniStorageAdapter
  request?: UniRequestAdapter
  getPrivacyMode?: () => PrivacyMode
}

export interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  routeToken?: string
  retry?: number
}

class UniAuthExpiredError extends Error {
  constructor(message = '登录已过期') {
    super(message)
    this.name = 'UniAuthExpiredError'
  }
}

class UniRefreshUnavailableError extends Error {
  constructor(message = '暂时无法刷新登录状态，请稍后重试') {
    super(message)
    this.name = 'UniRefreshUnavailableError'
  }
}

export function createUniRequestAdapter(): UniRequestAdapter {
  return (options) =>
    new Promise((resolve, reject) => {
      uni.request({
        ...options,
        success: resolve,
        fail: reject,
      })
    })
}

function isApiResponse<T>(value: unknown): value is ApiResponse<T> {
  return !!value && typeof value === 'object' && 'code' in value && 'data' in value
}

function unwrapResponse<T>(body: unknown): T {
  if (!isApiResponse<T>(body)) return body as T
  if (body.code !== 200) throw new Error(body.message || '请求失败')
  return body.data
}

function isRefreshAuthFailure(statusCode: number, body: unknown): boolean {
  const code = isApiResponse(body) ? body.code : undefined
  return statusCode === 401 || statusCode === 403 || code === 401 || code === 403
}

export function createApiClient(options: ApiClientOptions = {}) {
  const storage = options.storage ?? createUniStorageAdapter()
  const requestAdapter = options.request ?? createUniRequestAdapter()
  const readPrivacyMode = options.getPrivacyMode ?? (() => getStoredPrivacyMode(storage))
  let refreshPromise: Promise<string> | null = null

  function getBaseUrl(): string {
    return options.baseUrl ?? String(storage.get(storageKeys.backendUrl) || DEFAULT_BASE_URL)
  }

  async function refreshToken(): Promise<string> {
    if (refreshPromise) return refreshPromise
    refreshPromise = (async () => {
      const mode = readPrivacyMode()
      assertDataNetworkAllowed(mode)
      const refreshTokenValue = storage.get(storageKeys.refreshToken)
      if (!refreshTokenValue) {
        clearStoredAuth(storage)
        throw new UniAuthExpiredError()
      }
      const response = await requestAdapter({
        url: `${getBaseUrl()}/auth/refresh`,
        method: 'POST',
        timeout: REQUEST_TIMEOUT,
        data: { refresh_token: refreshTokenValue },
        header: {
          'Content-Type': 'application/json',
          ...privacyHeaders(mode),
        },
      })
      if (isRefreshAuthFailure(response.statusCode, response.data)) {
        clearStoredAuth(storage)
        throw new UniAuthExpiredError()
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw new UniRefreshUnavailableError()
      }
      const payload = unwrapResponse<{ access_token: string; refresh_token?: string }>(response.data)
      storage.set(storageKeys.accessToken, payload.access_token)
      if (payload.refresh_token) storage.set(storageKeys.refreshToken, payload.refresh_token)
      return payload.access_token
    })()
    try {
      return await refreshPromise
    } finally {
      refreshPromise = null
    }
  }

  async function request<T>(input: RequestOptions): Promise<T> {
    const { url, method = 'GET', data, routeToken, retry = 1 } = input
    for (let attempt = 0; attempt <= retry; attempt += 1) {
      const mode = readPrivacyMode()
      assertDataNetworkAllowed(mode)
      const token = storage.get(storageKeys.accessToken)
      const response = await requestAdapter({
        url: `${getBaseUrl()}${url}`,
        method,
        data,
        timeout: REQUEST_TIMEOUT,
        header: {
          'Content-Type': 'application/json',
          ...privacyHeaders(mode),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(routeToken ? { 'X-Route-Token': routeToken } : {}),
        },
      })
      if (isRefreshAuthFailure(response.statusCode, response.data) && attempt < retry) {
        try {
          await refreshToken()
          continue
        } catch (error) {
          if (error instanceof UniAuthExpiredError) throw new Error('登录已过期')
          throw error instanceof Error ? error : new UniRefreshUnavailableError()
        }
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw new Error('请求失败')
      }
      return unwrapResponse<T>(response.data)
    }
    throw new Error('请求失败')
  }

  return {
    request,
    get: <T>(url: string, routeToken?: string) => request<T>({ url, method: 'GET', routeToken }),
    post: <T>(url: string, data?: unknown, routeToken?: string) =>
      request<T>({ url, method: 'POST', data, routeToken }),
    put: <T>(url: string, data?: unknown, routeToken?: string) =>
      request<T>({ url, method: 'PUT', data, routeToken }),
    delete: <T>(url: string, routeToken?: string) => request<T>({ url, method: 'DELETE', routeToken }),
  }
}

export const api = createApiClient()
