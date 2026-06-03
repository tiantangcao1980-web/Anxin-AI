// -*- coding: utf-8 -*-
/**
 * IM Pairing API（V3 移动端镜像）。
 *
 * 与 frontend/src/lib/api/imPairing.ts 同形契约，走真实后端：
 *   - GET    /im/pairing/pending               待审批列表（im_pairing.py:81）
 *   - POST   /im/pairing/{id}/approve          批准（im_pairing.py:120）
 *   - POST   /im/pairing/{id}/reject           拒绝（im_pairing.py:140）
 *   - GET    /im/pairing/authorized            已绑定（im_pairing.py:98）
 */

import { getApiClient } from './client'

export type ChannelType =
  | 'feishu'
  | 'wechat'
  | 'dingtalk'
  | 'telegram'
  | 'discord'
  | 'slack'

export type PairingStatus = 'pending' | 'approved' | 'rejected' | 'expired'

export interface PairingRequest {
  id: string
  channel_id: string
  channel_type: ChannelType
  channel_name: string
  external_user_id: string
  external_user_name: string
  external_user_avatar?: string
  external_group_name?: string
  status: PairingStatus
  expires_at: string
  created_at: string
  approved_at: string | null
  approved_by: string | null
  rejection_reason: string | null
}

export interface IMBinding {
  id: string
  channel_id: string
  channel_type: ChannelType
  channel_name: string
  external_user_id: string
  external_user_name: string
  external_user_avatar?: string
  internal_user_id: string
  bound_at: string
  last_active_at: string | null
}

interface PairingRequestListOut {
  items?: PairingRequest[]
}

export async function listPending(): Promise<PairingRequest[]> {
  const client = getApiClient()
  // 后端 response_model=PairingRequestListOut（含 items 包装），兼容裸数组。
  const res = await client.get<PairingRequest[] | PairingRequestListOut>(
    '/im/pairing/pending',
  )
  const data = res.data as PairingRequest[] | PairingRequestListOut
  if (Array.isArray(data)) return data
  return data?.items ?? []
}

export async function approvePairing(id: string): Promise<IMBinding> {
  const client = getApiClient()
  const res = await client.post<IMBinding>(
    `/im/pairing/${encodeURIComponent(id)}/approve`,
  )
  return res.data
}

export async function rejectPairing(id: string, reason: string): Promise<PairingRequest> {
  const client = getApiClient()
  const res = await client.post<PairingRequest>(
    `/im/pairing/${encodeURIComponent(id)}/reject`,
    { reason },
  )
  return res.data
}

export const pairingApi = {
  listPending,
  approve: approvePairing,
  reject: rejectPairing,
}
