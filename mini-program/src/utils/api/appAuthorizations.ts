// -*- coding: utf-8 -*-
/**
 * App Authorizations API（小程序 V3 真实客户端，对标 mobile/src/lib/api/appAuthorizations.ts）。
 *
 * 走真实后端（已实测端点）：
 *   - GET    /app-authorizations/providers   provider 目录（app_authorizations.py:72，{items,total}）
 *   - GET    /app-authorizations             已授权列表（app_authorizations.py:102，{items,total}）
 *   - POST   /app-authorizations/{id}/start  发起 OAuth（app_authorizations.py:119，返回 {authorize_url,state}）
 *   - DELETE /app-authorizations/{id}         断开（app_authorizations.py:230）
 *
 * ⚠️ 小程序 apiClient 已 unwrap；list 类端点后端用 {items,total} 包装，读 .items。
 * ⚠️ 后端 ProviderMetadataOut 无 description、AppAuthorizationOut 无 account_label，
 *    页面用到的这两个字段在类型上声明为可选，运行时缺省即 undefined（页面已容错）。
 */

import { apiClient } from './client'

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
  /** 后端 ProviderMetadataOut 暂未返回，可选。 */
  description?: string
  category: AppCategory
  icon_url: string | null
  default_scopes: string[]
}

export interface AppAuthorization {
  id: string
  provider_id: string
  status: AppAuthorizationStatus
  scopes: string[]
  connected_at: string
  /** 后端 AppAuthorizationOut 暂未返回，可选。 */
  account_label?: string
}

interface ListOut<T> {
  items?: T[]
  total?: number
}

interface StartAuthorizeOut {
  authorize_url: string
  state?: string
}

export async function listProviders(): Promise<AppProvider[]> {
  const res = await apiClient.get<AppProvider[] | ListOut<AppProvider>>(
    '/app-authorizations/providers',
  )
  if (Array.isArray(res)) return res
  return res?.items ?? []
}

export async function listAuthorizations(): Promise<AppAuthorization[]> {
  const res = await apiClient.get<AppAuthorization[] | ListOut<AppAuthorization>>(
    '/app-authorizations',
  )
  if (Array.isArray(res)) return res
  return res?.items ?? []
}

export async function startConnect(
  providerId: string,
): Promise<{ authorize_url: string }> {
  const res = await apiClient.post<StartAuthorizeOut>(
    `/app-authorizations/${encodeURIComponent(providerId)}/start`,
  )
  return { authorize_url: res.authorize_url }
}

export async function disconnectAuthorization(id: string): Promise<void> {
  await apiClient.delete<void>(`/app-authorizations/${encodeURIComponent(id)}`)
}

export const appAuthApi = {
  listProviders,
  listAuthorizations,
  startConnect,
  disconnect: disconnectAuthorization,
}

// ===== 页面所需的应用分类常量（原置于 _mock，迁出以便去 mock）=====

export const APP_CATEGORY_LABELS: Record<AppCategory, string> = {
  office: '办公',
  office_storage: '云盘文档',
  crm: 'CRM',
  ecommerce: '电商',
  info_source: '情报源',
  design: '设计',
  compliance: '合规',
  finance: '财务',
}

export const APP_CATEGORY_ORDER: AppCategory[] = [
  'office',
  'office_storage',
  'crm',
  'ecommerce',
  'info_source',
  'design',
  'compliance',
  'finance',
]
