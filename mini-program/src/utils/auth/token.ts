// -*- coding: utf-8 -*-
/**
 * Token 持久化（基于 Taro.setStorageSync）
 *
 * 与 web (localStorage)、mobile (SecureStore) 端 contract 对齐：
 *   - getAccessToken() / setAccessToken(t)
 *   - getRefreshToken() / setRefreshToken(t)
 *   - clearAuth()
 *
 * 微信小程序 Storage 是同步 / 异步双 API，单条最大 1MB，总量 10MB —— 对 JWT 完全够用。
 */

import Taro from '@tarojs/taro'

const ACCESS_KEY = 'anxin:access_token'
const REFRESH_KEY = 'anxin:refresh_token'
const USER_KEY = 'anxin:user'

export interface StoredUser {
  id: string
  email: string
  name: string
  role: string
  avatar_url?: string
  login_type?: string
}

export const tokenStorage = {
  getAccessToken(): string | null {
    try {
      return Taro.getStorageSync<string>(ACCESS_KEY) || null
    } catch {
      return null
    }
  },
  setAccessToken(token: string): void {
    Taro.setStorageSync(ACCESS_KEY, token)
  },
  getRefreshToken(): string | null {
    try {
      return Taro.getStorageSync<string>(REFRESH_KEY) || null
    } catch {
      return null
    }
  },
  setRefreshToken(token: string): void {
    Taro.setStorageSync(REFRESH_KEY, token)
  },
  getUser(): StoredUser | null {
    try {
      const raw = Taro.getStorageSync<string | StoredUser>(USER_KEY)
      if (!raw) return null
      return typeof raw === 'string' ? (JSON.parse(raw) as StoredUser) : raw
    } catch {
      return null
    }
  },
  setUser(user: StoredUser): void {
    Taro.setStorageSync(USER_KEY, user)
  },
  clearAuth(): void {
    Taro.removeStorageSync(ACCESS_KEY)
    Taro.removeStorageSync(REFRESH_KEY)
    Taro.removeStorageSync(USER_KEY)
  },
  isAuthenticated(): boolean {
    return !!this.getAccessToken()
  },
}
