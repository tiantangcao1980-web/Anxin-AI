import Taro from '@tarojs/taro'

declare const TARO_APP_API_BASE: string | undefined
const BASE_URL = (typeof TARO_APP_API_BASE !== 'undefined' ? TARO_APP_API_BASE : '') || 'http://localhost:8001/api/v1'
const REQUEST_TIMEOUT = 30000

interface ApiResponse<T = any> {
  code: number
  data: T
  message: string
  request_id: string
}

// token 刷新锁，防止并发刷新
let refreshPromise: Promise<string> | null = null

async function refreshToken(): Promise<string> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      const rt = Taro.getStorageSync('refresh_token')
      if (!rt) throw new Error('无刷新令牌')
      const res = await Taro.request({
        url: `${BASE_URL}/auth/refresh`,
        method: 'POST',
        data: { refresh_token: rt },
        timeout: 10000,
      })
      const body = res.data as ApiResponse<{ access_token: string; refresh_token?: string }>
      if (body.code !== 200) throw new Error(body.message)
      Taro.setStorageSync('token', body.data.access_token)
      if (body.data.refresh_token) {
        Taro.setStorageSync('refresh_token', body.data.refresh_token)
      }
      return body.data.access_token
    } catch (e) {
      Taro.removeStorageSync('token')
      Taro.removeStorageSync('refresh_token')
      throw e
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
      const token = Taro.getStorageSync('token')
      const res = await Taro.request({
        url: `${BASE_URL}${url}`,
        method: method as any,
        data,
        timeout: REQUEST_TIMEOUT,
        header: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      const body = res.data as ApiResponse<T>

      // 401: 尝试刷新 token
      if (res.statusCode === 401 || body.code === 401) {
        if (attempt < retry) {
          try {
            await refreshToken()
            continue // 用新 token 重试
          } catch {
            Taro.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
            throw new Error('登录已过期')
          }
        }
      }

      if (body.code !== 200) {
        throw new Error(body.message || '请求失败')
      }
      return body.data
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
