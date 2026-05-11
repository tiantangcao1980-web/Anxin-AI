// -*- coding: utf-8 -*-
/**
 * V3 移动端 HTTP 客户端（axios）。
 *
 * 与 web 端的 contract 保持一致：
 *   - 所有请求附 `Authorization: Bearer <access_token>`
 *   - response 401 自动尝试 `/auth/refresh` 续签，单飞 + 重放原请求
 *   - 网络错误 / 超时 / 5xx 抛出标准化 `ApiError`
 *
 * 与 `@/services/api`（手写 fetch + ApiResponse 包装）共存：
 *   - 老代码继续用 services/api（V2 业务页）
 *   - V3 业务（personas / agentTasks / imChannels / skills）统一用本 client
 */

import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios'
import Constants from 'expo-constants'
import { Platform } from 'react-native'
import { getAuthStorage } from '../auth-storage'

const FALLBACK_DEV_BASE = Platform.OS === 'android'
  ? 'http://10.0.2.2:8001/api/v1'
  : 'http://localhost:8001/api/v1'

const FALLBACK_PROD_BASE = 'https://api.anxinagent.com/api/v1'

function resolveBaseUrl(): string {
  const fromExtra = Constants.expoConfig?.extra as Record<string, string> | undefined
  if (__DEV__) {
    return fromExtra?.apiBaseUrlDev || FALLBACK_DEV_BASE
  }
  return fromExtra?.apiBaseUrl || FALLBACK_PROD_BASE
}

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

let refreshPromise: Promise<string> | null = null

async function performRefresh(client: AxiosInstance): Promise<string> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      const storage = getAuthStorage()
      const rt = await storage.getRefreshToken()
      if (!rt) throw new ApiError('无刷新令牌', 401, 'NO_REFRESH_TOKEN')
      const res = await axios.post(
        `${client.defaults.baseURL}/auth/refresh`,
        { refresh_token: rt },
        { headers: { 'Content-Type': 'application/json' } },
      )
      // 兼容两种响应：扁平 `{ access_token, refresh_token }`
      // 与 ApiResponse 包装 `{ code, data: { access_token, ... } }`
      const payload = res.data?.data ?? res.data
      const accessToken = payload?.access_token
      const refreshToken = payload?.refresh_token
      if (!accessToken) throw new ApiError('刷新响应缺少 access_token', 500)
      await storage.setAccessToken(accessToken)
      if (refreshToken) await storage.setRefreshToken(refreshToken)
      return accessToken
    } catch (err) {
      await getAuthStorage().clearAuth()
      throw err
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

function normalizeError(err: AxiosError): ApiError {
  if (err.response) {
    const data = err.response.data as Record<string, unknown> | undefined
    const message =
      (data?.message as string) ||
      (data?.detail as string) ||
      err.message ||
      `HTTP ${err.response.status}`
    return new ApiError(
      message,
      err.response.status,
      (data?.code as string) ?? undefined,
      data,
    )
  }
  if (err.code === 'ECONNABORTED') {
    return new ApiError('请求超时', 0, 'TIMEOUT')
  }
  return new ApiError(err.message || '网络错误', 0, 'NETWORK_ERROR')
}

export function createApiClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: resolveBaseUrl(),
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
  })

  instance.interceptors.request.use(async (config) => {
    const token = await getAuthStorage().getAccessToken()
    if (token) {
      config.headers = config.headers ?? {}
      ;(config.headers as Record<string, string>).Authorization = `Bearer ${token}`
    }
    return config
  })

  instance.interceptors.response.use(
    (res) => res,
    async (err: AxiosError) => {
      const original = err.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined
      // 401 + 未重试过 -> 尝试 refresh 后重放
      if (
        err.response?.status === 401 &&
        original &&
        !original._retried &&
        !original.url?.includes('/auth/refresh') &&
        !original.url?.includes('/auth/login')
      ) {
        original._retried = true
        try {
          const newToken = await performRefresh(instance)
          original.headers = original.headers ?? {}
          ;(original.headers as Record<string, string>).Authorization = `Bearer ${newToken}`
          return instance.request(original)
        } catch (refreshErr) {
          return Promise.reject(normalizeError(err))
        }
      }
      return Promise.reject(normalizeError(err))
    },
  )

  return instance
}

let singleton: AxiosInstance | null = null

export function getApiClient(): AxiosInstance {
  if (!singleton) singleton = createApiClient()
  return singleton
}

/** 仅给测试用：重置实例 */
export function __resetApiClient() {
  singleton = null
  refreshPromise = null
}
