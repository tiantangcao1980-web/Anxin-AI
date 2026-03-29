import AsyncStorage from '@react-native-async-storage/async-storage'
import { Platform } from 'react-native'
import type { ApiResponse } from '../types/api'

const BASE_URL = __DEV__
  ? Platform.OS === 'android' ? 'http://10.0.2.2:8001/api/v1' : 'http://localhost:8001/api/v1'
  : 'https://api.anxinlegal.com/api/v1'

const REQUEST_TIMEOUT = 30000

let refreshPromise: Promise<string> | null = null

async function getToken(): Promise<string | null> {
  return await AsyncStorage.getItem('token')
}

async function setToken(token: string): Promise<void> {
  await AsyncStorage.setItem('token', token)
}

async function clearAuth(): Promise<void> {
  await AsyncStorage.multiRemove(['token', 'refresh_token', 'user'])
}

async function refreshToken(): Promise<string> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      const rt = await AsyncStorage.getItem('refresh_token')
      if (!rt) throw new Error('无刷新令牌')
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      })
      const body: ApiResponse<{ access_token: string; refresh_token?: string }> = await res.json()
      if (body.code !== 200) throw new Error(body.message)
      await setToken(body.data.access_token)
      if (body.data.refresh_token) await AsyncStorage.setItem('refresh_token', body.data.refresh_token)
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
  data?: any
  retry?: number
}): Promise<T> {
  const { url, method = 'GET', data, retry = 2 } = options

  for (let attempt = 0; attempt <= retry; attempt++) {
    try {
      const token = await getToken()
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

      const res = await fetch(`${BASE_URL}${url}`, {
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
          try { await refreshToken(); continue } catch { throw new Error('登录已过期') }
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
  post: <T>(url: string, data?: any) => request<T>({ url, method: 'POST', data }),
  put: <T>(url: string, data?: any) => request<T>({ url, method: 'PUT', data }),
  delete: <T>(url: string) => request<T>({ url, method: 'DELETE' }),
}
