// -*- coding: utf-8 -*-
/**
 * App Authorizations API（V3 移动端镜像）。
 *
 * 与 frontend/src/lib/api/appAuthorizations.ts 同形契约，走真实后端：
 *   - GET    /app-authorizations/providers          provider 目录（app_authorizations.py:72）
 *   - GET    /app-authorizations                     已授权列表（app_authorizations.py:102）
 *   - POST   /app-authorizations/{id}/start          发起 OAuth（app_authorizations.py:119）
 *   - POST   /app-authorizations/{id}/refresh        刷新（app_authorizations.py:197）
 *   - DELETE /app-authorizations/{id}                断开（app_authorizations.py:230）
 */

import { getApiClient } from './client'

export type AppCategory =
  | 'office'
  | 'office_storage'
  | 'crm'
  | 'ecommerce'
  | 'info_source'
  | 'design'
  | 'compliance'
  | 'finance'

export type AppAuthorizationStatus = 'connected' | 'expired' | 'revoked' | 'error'

export interface AppProvider {
  provider_id: string
  display_name: string
  description: string
  category: AppCategory
  icon_url: string | null
  default_scopes: string[]
  documentation_url?: string
}

export interface AppAuthorization {
  id: string
  user_id: string
  provider_id: string
  status: AppAuthorizationStatus
  scopes: string[]
  connected_at: string
  last_refresh_at: string | null
  error_message: string | null
  account_label?: string
}

export interface StartConnectResponse {
  authorize_url: string
  state: string
}

export async function listProviders(): Promise<AppProvider[]> {
  const client = getApiClient()
  const res = await client.get<AppProvider[]>('/app-authorizations/providers')
  return res.data ?? []
}

export async function listAuthorizations(): Promise<AppAuthorization[]> {
  const client = getApiClient()
  const res = await client.get<AppAuthorization[]>('/app-authorizations')
  return res.data ?? []
}

export async function startConnect(providerId: string): Promise<StartConnectResponse> {
  const client = getApiClient()
  const res = await client.post<StartConnectResponse>(
    `/app-authorizations/${encodeURIComponent(providerId)}/start`,
  )
  return res.data
}

export async function refreshAuthorization(id: string): Promise<AppAuthorization> {
  const client = getApiClient()
  const res = await client.post<AppAuthorization>(
    `/app-authorizations/${encodeURIComponent(id)}/refresh`,
  )
  return res.data
}

export async function disconnectAuthorization(id: string): Promise<void> {
  const client = getApiClient()
  await client.delete(`/app-authorizations/${encodeURIComponent(id)}`)
}

export const appAuthApi = {
  listProviders,
  listAuthorizations,
  startConnect,
  refresh: refreshAuthorization,
  disconnect: disconnectAuthorization,
}
