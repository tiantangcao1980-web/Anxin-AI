import { Platform } from 'react-native'
import { getAuthStorage } from '../lib/auth-storage'
import type { ApiResponse, User } from '../types/api'

const DEFAULT_BASE_URL = __DEV__
  ? Platform.OS === 'android' ? 'http://10.0.2.2:8001/api/v1' : 'http://localhost:8001/api/v1'
  : 'https://api.anxinlegal.com/api/v1'

const REQUEST_TIMEOUT = 30000

let refreshPromise: Promise<string> | null = null

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token?: string
  token_type: string
  user: User
}

async function getToken(): Promise<string | null> {
  return getAuthStorage().getAccessToken()
}

async function setToken(token: string): Promise<void> {
  await getAuthStorage().setAccessToken(token)
}

async function clearAuth(): Promise<void> {
  await getAuthStorage().clearAuth()
}

async function getBaseUrl(): Promise<string> {
  return (await getAuthStorage().getBackendUrl()) ?? DEFAULT_BASE_URL
}

async function refreshToken(): Promise<string> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      const storage = getAuthStorage()
      const rt = await storage.getRefreshToken()
      if (!rt) throw new Error('无刷新令牌')
      const res = await fetch(`${await getBaseUrl()}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      })
      const body: ApiResponse<{ access_token: string; refresh_token?: string }> = await res.json()
      if (body.code !== 200) throw new Error(body.message)
      await setToken(body.data.access_token)
      if (body.data.refresh_token) await storage.setRefreshToken(body.data.refresh_token)
      return body.data.access_token
    } catch {
      await clearAuth()
      throw new Error('登录已过期')
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

export async function request<T>(options: {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  retry?: number
}): Promise<T> {
  const { url, method = 'GET', data, retry = 2 } = options

  for (let attempt = 0; attempt <= retry; attempt++) {
    try {
      const token = await getToken()
      const baseUrl = await getBaseUrl()
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

      const res = await fetch(`${baseUrl}${url}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: data ? JSON.stringify(data) : undefined,
        signal: controller.signal,
      })
      clearTimeout(timeout)

      const body: ApiResponse<T> = await res.json()

      if (res.status === 401 || body.code === 401) {
        if (attempt < retry) {
          try {
            await refreshToken()
            // 刷新成功后同步 zustand 登录态，避免 store 与 SecureStore 不一致导致越权判断错位
            const { useAuthStore } = await import('../lib/store')
            await useAuthStore.getState().syncAuth()
            continue
          } catch {
            // 刷新失败：清登录态，让守卫重定向到登录页
            const { useAuthStore } = await import('../lib/store')
            await useAuthStore.getState().logout()
            throw new Error('登录已过期')
          }
        }
      }

      if (body.code !== 200) throw new Error(body.message || '请求失败')
      return body.data
    } catch (e: any) {
      if (e.name === 'AbortError' || e.message?.includes('Network')) {
        if (attempt < retry) {
          await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt)))
          continue
        }
      }
      throw e
    }
  }
  throw new Error('请求失败')
}

export const api = {
  get: <T>(url: string) => request<T>({ url, method: 'GET' }),
  post: <T>(url: string, data?: unknown) => request<T>({ url, method: 'POST', data }),
  put: <T>(url: string, data?: unknown) => request<T>({ url, method: 'PUT', data }),
  delete: <T>(url: string) => request<T>({ url, method: 'DELETE' }),
}

export const authApi = {
  login: (data: LoginRequest) => api.post<LoginResponse>('/auth/login', data),
}
