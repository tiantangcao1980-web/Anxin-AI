// -*- coding: utf-8 -*-
/**
 * IM Pairing API（小程序 V3 真实客户端，对标 mobile/src/lib/api/imPairing.ts）。
 *
 * 走真实后端（已实测端点，均需管理员态）：
 *   - GET  /im/pairing/pending          待审批（im_pairing.py:81，{items,limit}）
 *   - GET  /im/pairing/authorized       已绑定（im_pairing.py:98，{items,limit}，返回 IMBinding）
 *   - POST /im/pairing/{id}/approve     批准（im_pairing.py:120，返回 IMBinding）
 *   - POST /im/pairing/{id}/reject      驳回（im_pairing.py:140，请求体 {reason}，返回 PairingRequest）
 *
 * ⚠️ 契约差异（已核实 backend/src/api/routes/schemas/im_pairing.py）：
 *   - 后端 PairingRequestOut / IMBindingOut 是「精简 DTO」，不含
 *     channel_type / channel_name / external_user_name / external_group_name。
 *     页面需要这些展示字段，故此处 map 时给安全 fallback（用 external_user_id /
 *     channel_id 兜底），避免渲染空白；类型上声明这些字段，运行时尽力填充。
 *   - 「已授权」后端返回的是 IMBinding（绑定），此处映射成页面用的
 *     PairingRequest 形状（status='approved'，approved_at=bound_at）。
 *   - approve 后端返回 IMBinding，亦映射回 PairingRequest 形状供页面更新列表。
 *   - reject 后端必填 reason，小程序无独立填写入口 → 传默认理由。
 *
 * ⚠️ revoke（撤销已授权绑定）后端暂无端点（im_pairing.py 仅 request/pending/
 *    authorized/approve/reject 五个路由）→ 见下方 TODO，调用即抛错，页面 catch 提示。
 */

import { apiClient, ApiError } from './client'

export type IMChannelType =
  | 'feishu'
  | 'wechat'
  | 'dingtalk'
  | 'telegram'
  | 'discord'

export type PairingStatus = 'pending' | 'approved' | 'rejected' | 'expired'

/** 页面渲染所需的 PairingRequest 形状（后端 DTO 更精简，展示字段为兜底填充）。 */
export interface PairingRequest {
  id: string
  channel_id: string
  channel_type: IMChannelType
  channel_name: string
  external_user_id: string
  external_user_name: string
  external_group_name?: string
  status: PairingStatus
  expires_at: string
  created_at: string
  approved_at: string | null
}

// ===== 后端精简 DTO（实际 wire shape）=====

interface PairingRequestDTO {
  id: string
  channel_id: string
  channel_type?: IMChannelType
  channel_name?: string
  external_user_id: string
  external_user_name?: string
  external_group_name?: string
  status: PairingStatus
  expires_at: string
  approved_at: string | null
  created_at: string
}

interface IMBindingDTO {
  id: string
  channel_id: string
  channel_type?: IMChannelType
  channel_name?: string
  external_user_id: string
  external_user_name?: string
  bound_at: string
  created_at: string
}

interface PairingListOut {
  items?: PairingRequestDTO[]
}

interface BindingListOut {
  items?: IMBindingDTO[]
}

function fromRequestDTO(d: PairingRequestDTO): PairingRequest {
  return {
    id: d.id,
    channel_id: d.channel_id,
    channel_type: d.channel_type ?? 'feishu',
    channel_name: d.channel_name ?? d.channel_id,
    external_user_id: d.external_user_id,
    external_user_name: d.external_user_name ?? d.external_user_id,
    external_group_name: d.external_group_name,
    status: d.status,
    expires_at: d.expires_at,
    created_at: d.created_at,
    approved_at: d.approved_at,
  }
}

function fromBindingDTO(d: IMBindingDTO): PairingRequest {
  return {
    id: d.id,
    channel_id: d.channel_id,
    channel_type: d.channel_type ?? 'feishu',
    channel_name: d.channel_name ?? d.channel_id,
    external_user_id: d.external_user_id,
    external_user_name: d.external_user_name ?? d.external_user_id,
    external_group_name: undefined,
    status: 'approved',
    expires_at: '',
    created_at: d.created_at,
    approved_at: d.bound_at ?? d.created_at,
  }
}

export async function listPending(): Promise<PairingRequest[]> {
  const res = await apiClient.get<PairingRequestDTO[] | PairingListOut>(
    '/im/pairing/pending',
  )
  const items = Array.isArray(res) ? res : res?.items ?? []
  return items.map(fromRequestDTO)
}

export async function listApproved(): Promise<PairingRequest[]> {
  const res = await apiClient.get<IMBindingDTO[] | BindingListOut>(
    '/im/pairing/authorized',
  )
  const items = Array.isArray(res) ? res : res?.items ?? []
  return items.map(fromBindingDTO)
}

export async function approvePairing(id: string): Promise<PairingRequest> {
  // 后端返回 IMBinding，映射回页面用的 PairingRequest 形状。
  const binding = await apiClient.post<IMBindingDTO>(
    `/im/pairing/${encodeURIComponent(id)}/approve`,
  )
  return fromBindingDTO(binding)
}

export async function rejectPairing(
  id: string,
  reason = '管理员驳回',
): Promise<PairingRequest> {
  const dto = await apiClient.post<PairingRequestDTO>(
    `/im/pairing/${encodeURIComponent(id)}/reject`,
    { reason },
  )
  return fromRequestDTO(dto)
}

/**
 * TODO(backend): 撤销已生效的 IM 绑定。
 * 后端 im_pairing.py 当前无 unbind/revoke 端点（仅 request/pending/authorized/
 * approve/reject）。待后端补 DELETE /im/pairing/bindings/{id} 后再接真实。
 * 现阶段调用即抛 NOT_SUPPORTED，页面 catch 弹「操作失败」toast。
 */
export async function revokePairing(_id: string): Promise<void> {
  throw new ApiError('撤销绑定暂未开放', 501, 'NOT_SUPPORTED')
}

export const pairingApi = {
  listPending,
  listApproved,
  approve: approvePairing,
  reject: rejectPairing,
  revoke: revokePairing,
}
