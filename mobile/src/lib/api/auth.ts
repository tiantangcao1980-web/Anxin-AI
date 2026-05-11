// -*- coding: utf-8 -*-
/**
 * Auth API（V3 移动端）。
 *
 * 与 web 端契约对齐：
 *   - POST /auth/login           -> { access_token, refresh_token, token_type, user }
 *   - POST /auth/register        -> User
 *   - POST /auth/refresh         -> { access_token, refresh_token? }
 *   - GET  /auth/me              -> User
 *   - POST /auth/logout
 *
 * 后端如果用了 ApiResponse 包装，client 已经在 interceptor 里把 .data 解开。
 * 这里默认走扁平契约（直接 access_token 在顶层）。如果后端实际是
 * `{ code, data: {...} }` 包装，调用方要显式访问 res.data。
 */

import { getApiClient } from './client'
import { getAuthStorage } from '../auth-storage'

export interface LoginRequest {
  email: string
  password: string
  captcha_token?: string
}

export interface AuthUser {
  id: string
  email: string
  name: string
  role: string
  user_type?: string
  avatar_url?: string
  email_verified?: boolean
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: AuthUser
}

export interface RegisterRequest {
  email: string
  password: string
  name: string
  user_type?: string
  phone?: string
  captcha_token?: string
}

function unwrap<T>(payload: any): T {
  // 兼容两种响应：扁平 / ApiResponse 包装
  if (payload && typeof payload === 'object' && 'code' in payload && 'data' in payload) {
    return payload.data as T
  }
  return payload as T
}

export async function login(req: LoginRequest): Promise<LoginResponse> {
  const client = getApiClient()
  const res = await client.post('/auth/login', req)
  const data = unwrap<LoginResponse>(res.data)
  if (data?.access_token) {
    const storage = getAuthStorage()
    await storage.setAccessToken(data.access_token)
    if (data.refresh_token) await storage.setRefreshToken(data.refresh_token)
  }
  return data
}

export async function register(req: RegisterRequest): Promise<AuthUser> {
  const client = getApiClient()
  const res = await client.post('/auth/register', req)
  return unwrap<AuthUser>(res.data)
}

export async function getCurrentUser(): Promise<AuthUser> {
  const client = getApiClient()
  const res = await client.get('/auth/me')
  return unwrap<AuthUser>(res.data)
}

export async function logout(): Promise<void> {
  const client = getApiClient()
  try {
    await client.post('/auth/logout')
  } catch {
    // 即使 server 端失败也清本地
  }
  await getAuthStorage().clearAuth()
}

export const authApiV3 = {
  login,
  register,
  getCurrentUser,
  logout,
}
