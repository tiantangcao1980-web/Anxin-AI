// -*- coding: utf-8 -*-
/**
 * 认证 API（V3 P21-A 基础层）
 *
 * 微信小程序登录流：
 *   1. wx.login() → js_code
 *   2. POST /auth/oauth/wechat/callback { code: js_code }（复用 H5 OAuth 端点；
 *      后端依据 settings.OAUTH_WECHAT_ENABLED 走 wx_login 适配器）
 *   3. 后端返回 { access_token, refresh_token, user }
 *
 * 后端契约：backend/src/api/routes/auth.py:742 wechat_oauth_callback
 *
 * 邮箱 / 手机号登录端点同 web 端（/auth/login），用于体验阶段「跳过微信登录」。
 */

import Taro from '@tarojs/taro'
import { apiClient } from './client'
import { tokenStorage, type StoredUser } from '../auth/token'
import { assertMiniProgramDataNetworkAllowed, getStoredPrivacyMode } from '../privacy'

export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type?: string
  user: StoredUser
  is_new_user?: boolean
}

export interface PasswordLoginRequest {
  email: string
  password: string
}

/**
 * 微信小程序登录：调 wx.login 拿 code，再换后端 token
 */
export async function wechatMiniprogramLogin(): Promise<LoginResult> {
  // 隐私模式 fail-closed：Taro.login 触发与微信后台通信，敏感模式禁止
  const currentMode = getStoredPrivacyMode()
  assertMiniProgramDataNetworkAllowed(currentMode)

  const loginRes = await Taro.login()
  if (!loginRes.code) {
    throw new Error('微信登录失败：未获取到 code')
  }
  const result = await apiClient.post<LoginResult>('/auth/oauth/wechat/callback', {
    code: loginRes.code,
    state: 'miniprogram',
  })
  // 持久化
  tokenStorage.setAccessToken(result.access_token)
  if (result.refresh_token) tokenStorage.setRefreshToken(result.refresh_token)
  if (result.user) tokenStorage.setUser(result.user)
  return result
}

/** 邮箱密码登录（开发体验入口） */
export async function passwordLogin(body: PasswordLoginRequest): Promise<LoginResult> {
  const result = await apiClient.post<LoginResult>('/auth/login', body)
  tokenStorage.setAccessToken(result.access_token)
  if (result.refresh_token) tokenStorage.setRefreshToken(result.refresh_token)
  if (result.user) tokenStorage.setUser(result.user)
  return result
}

/** 当前用户信息（依赖已登录） */
export async function getCurrentUser(): Promise<StoredUser> {
  const user = await apiClient.get<StoredUser>('/auth/me')
  tokenStorage.setUser(user)
  return user
}

/** 登出 */
export async function logout(): Promise<void> {
  try {
    await apiClient.post<void>('/auth/logout')
  } catch {
    // 后端 logout 失败不阻塞前端清除
  } finally {
    tokenStorage.clearAuth()
  }
}

export const authApi = {
  wechatMiniprogramLogin,
  passwordLogin,
  getCurrentUser,
  logout,
}
