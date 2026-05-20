// -*- coding: utf-8 -*-
/**
 * V3 微信小程序 HTTP 客户端
 *
 * 基于 Taro.request，与 web/mobile 端契约对齐：
 *   - 自动附 Authorization: Bearer
 *   - 401 → 自动 refresh + 重放（单飞）
 *   - 5xx / 网络错误 → 指数退避重试 (默认 2 次)
 *   - 错误统一抛出 ApiError
 *
 * P21-B/C/D 直接通过 `apiClient.get/post/...` 调用，不需要再写 boilerplate。
 */

import Taro from '@tarojs/taro'
import { tokenStorage } from '../auth/token'
import { refreshAccessToken } from '../auth/refresh'
import { assertMiniProgramDataNetworkAllowed, getStoredPrivacyMode } from '../privacy'
import { resolveBaseUrl } from './baseUrl'

const DEFAULT_TIMEOUT = 30_000

export class ApiError extends Error {
  status: number
  code?: string
  detail?: unknown
  constructor(message: string, status = 0, code?: string, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail
  }
}

export interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  data?: unknown
  query?: Record<string, string | number | boolean | undefined>
  headers?: Record<string, string>
  timeout?: number
  /** 网络错误重试次数，默认 2 */
  retry?: number
  /** 是否跳过 401 自动续签（用于 /auth/login 等本身就是登录的 endpoint） */
  skipAuthRefresh?: boolean
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const base = resolveBaseUrl()
  const fullPath = path.startsWith('http') ? path : `${base}${path}`
  if (!query) return fullPath
  const parts: string[] = []
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null) continue
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
  }
  if (!parts.length) return fullPath
  return `${fullPath}${fullPath.includes('?') ? '&' : '?'}${parts.join('&')}`
}

function unwrap<T>(body: unknown, status: number): T {
  if (typeof body !== 'object' || body === null) {
    return body as T
  }
  const wrapped = body as Record<string, unknown>
  // 兼容 ApiResponse 包装 { code, data, message }
  if ('code' in wrapped && 'data' in wrapped) {
    const code = wrapped.code as number
    if (code === 200 || code === 0) return wrapped.data as T
    throw new ApiError(
      (wrapped.message as string) || 'API error',
      status,
      String(code),
      wrapped,
    )
  }
  return body as T
}

async function rawRequest<T>(opts: RequestOptions): Promise<T> {
  const {
    url,
    method = 'GET',
    data,
    query,
    headers,
    timeout = DEFAULT_TIMEOUT,
    skipAuthRefresh = false,
  } = opts

  // 隐私模式 fail-closed：local / top-secret 模式禁止任何数据网络请求
  const privacyMode = getStoredPrivacyMode()
  assertMiniProgramDataNetworkAllowed(privacyMode)

  const token = tokenStorage.getAccessToken()
  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Privacy-Mode': privacyMode,
    ...(headers || {}),
  }
  if (token && !finalHeaders.Authorization) {
    finalHeaders.Authorization = `Bearer ${token}`
  }

  const fullUrl = buildUrl(url, query)

  let res: Taro.request.SuccessCallbackResult<string | Record<string, unknown>>
  try {
    res = await Taro.request({
      url: fullUrl,
      method: method as keyof Taro.request.Method,
      data: data as Record<string, unknown> | undefined,
      header: finalHeaders,
      timeout,
    })
  } catch (e) {
    const err = e as { errMsg?: string }
    const msg = err.errMsg || '网络错误'
    if (msg.includes('timeout')) {
      throw new ApiError('请求超时', 0, 'TIMEOUT')
    }
    throw new ApiError(msg, 0, 'NETWORK_ERROR')
  }

  const status = res.statusCode ?? 0

  // 401 → refresh + retry once
  if (status === 401 && !skipAuthRefresh && !url.includes('/auth/refresh')) {
    try {
      const newToken = await refreshAccessToken()
      const retryHeaders = { ...finalHeaders, Authorization: `Bearer ${newToken}` }
      const retried = await Taro.request({
        url: fullUrl,
        method: method as keyof Taro.request.Method,
        data: data as Record<string, unknown> | undefined,
        header: retryHeaders,
        timeout,
      })
      const retriedStatus = retried.statusCode ?? 0
      if (retriedStatus >= 200 && retriedStatus < 300) {
        return unwrap<T>(retried.data, retriedStatus)
      }
      throw new ApiError(
        '登录已过期，请重新登录',
        retriedStatus,
        'AUTH_EXPIRED',
        retried.data,
      )
    } catch (e) {
      if (e instanceof ApiError) throw e
      throw new ApiError('登录已过期，请重新登录', 401, 'AUTH_EXPIRED')
    }
  }

  if (status >= 200 && status < 300) {
    return unwrap<T>(res.data, status)
  }

  // 错误响应
  const body = res.data as Record<string, unknown> | undefined
  const message =
    (body?.message as string) ||
    (body?.detail as string) ||
    `HTTP ${status}`
  throw new ApiError(message, status, body?.code as string | undefined, body)
}

/**
 * 带指数退避重试的请求（仅对 5xx / 网络错误重试，4xx 不重试）。
 */
export async function request<T>(opts: RequestOptions): Promise<T> {
  const retry = opts.retry ?? 2
  let lastErr: unknown
  for (let i = 0; i <= retry; i++) {
    try {
      return await rawRequest<T>(opts)
    } catch (e) {
      lastErr = e
      const err = e as ApiError
      const isRetriable =
        err.code === 'TIMEOUT' ||
        err.code === 'NETWORK_ERROR' ||
        (err.status >= 500 && err.status < 600)
      if (!isRetriable || i === retry) throw e
      await new Promise((r) => setTimeout(r, 1_000 * Math.pow(2, i)))
    }
  }
  throw lastErr
}

export const apiClient = {
  get: <T>(url: string, query?: RequestOptions['query']) =>
    request<T>({ url, method: 'GET', query }),
  post: <T>(url: string, data?: unknown) =>
    request<T>({ url, method: 'POST', data }),
  put: <T>(url: string, data?: unknown) =>
    request<T>({ url, method: 'PUT', data }),
  patch: <T>(url: string, data?: unknown) =>
    request<T>({ url, method: 'PATCH', data }),
  delete: <T>(url: string) => request<T>({ url, method: 'DELETE' }),
  request,
}
