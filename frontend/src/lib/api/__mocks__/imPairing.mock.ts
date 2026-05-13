/**
 * IM Pairing Mock 适配层
 *
 * 在 VITE_PAIRING_MOCK=true 时启用,供 P3 阶段在后端就绪前完成前端联调。
 *
 * 种子数据:
 *   - 3 条 pending(飞书 1 + 钉钉 1 + 微信群 1),剩余 23h / 12h / 2h
 *   - 5 条已授权(飞书 3 + 微信 2)
 */

import type {
  IMBinding,
  PairingRequest,
  RejectPairingRequest,
} from '../imPairing'

const now = () => new Date().toISOString()
const hoursFromNow = (h: number) => new Date(Date.now() + h * 3_600_000).toISOString()
const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString()
const daysAgo = (d: number) => new Date(Date.now() - d * 86_400_000).toISOString()
const minutesAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString()

// pending 创建时间 = 24h - 剩余时间
const pendingCreatedAt = (remainingH: number) => hoursAgo(24 - remainingH)

const seedPending: PairingRequest[] = [
  {
    id: 'mock-pair-1',
    channel_id: 'feishu-org-001',
    channel_type: 'feishu',
    channel_name: '安心智能助手·总部飞书',
    external_user_id: 'fs-uid-1001',
    external_user_name: '张明远',
    external_user_avatar: undefined,
    external_group_name: undefined,
    status: 'pending',
    expires_at: hoursFromNow(23),
    created_at: pendingCreatedAt(23),
    approved_at: null,
    approved_by: null,
    rejection_reason: null,
  },
  {
    id: 'mock-pair-2',
    channel_id: 'dingtalk-org-002',
    channel_type: 'dingtalk',
    channel_name: '北京分公司钉钉',
    external_user_id: 'dt-uid-2002',
    external_user_name: '李雪',
    external_user_avatar: undefined,
    external_group_name: undefined,
    status: 'pending',
    expires_at: hoursFromNow(12),
    created_at: pendingCreatedAt(12),
    approved_at: null,
    approved_by: null,
    rejection_reason: null,
  },
  {
    id: 'mock-pair-3',
    channel_id: 'wechat-grp-003',
    channel_type: 'wechat',
    channel_name: '法务支持企微',
    external_user_id: 'wx-uid-3003',
    external_user_name: '王建国',
    external_user_avatar: undefined,
    external_group_name: '客户A合同评审群',
    status: 'pending',
    expires_at: hoursFromNow(2),
    created_at: pendingCreatedAt(2),
    approved_at: null,
    approved_by: null,
    rejection_reason: null,
  },
]

const seedBindings: IMBinding[] = [
  {
    id: 'mock-bind-1',
    channel_id: 'feishu-org-001',
    channel_type: 'feishu',
    channel_name: '安心智能助手·总部飞书',
    external_user_id: 'fs-uid-9001',
    external_user_name: '陈思颖',
    external_user_avatar: undefined,
    internal_user_id: 'mock-user',
    bound_at: daysAgo(45),
    last_active_at: minutesAgo(8),
  },
  {
    id: 'mock-bind-2',
    channel_id: 'feishu-org-001',
    channel_type: 'feishu',
    channel_name: '安心智能助手·总部飞书',
    external_user_id: 'fs-uid-9002',
    external_user_name: '赵伟',
    external_user_avatar: undefined,
    internal_user_id: 'mock-user',
    bound_at: daysAgo(30),
    last_active_at: hoursAgo(3),
  },
  {
    id: 'mock-bind-3',
    channel_id: 'feishu-org-001',
    channel_type: 'feishu',
    channel_name: '安心智能助手·总部飞书',
    external_user_id: 'fs-uid-9003',
    external_user_name: '刘婷',
    external_user_avatar: undefined,
    internal_user_id: 'mock-user',
    bound_at: daysAgo(12),
    last_active_at: daysAgo(2),
  },
  {
    id: 'mock-bind-4',
    channel_id: 'wechat-corp-008',
    channel_type: 'wechat',
    channel_name: '法务支持企微',
    external_user_id: 'wx-uid-9004',
    external_user_name: '黄志强',
    external_user_avatar: undefined,
    internal_user_id: 'mock-user',
    bound_at: daysAgo(60),
    last_active_at: hoursAgo(20),
  },
  {
    id: 'mock-bind-5',
    channel_id: 'wechat-corp-008',
    channel_type: 'wechat',
    channel_name: '法务支持企微',
    external_user_id: 'wx-uid-9005',
    external_user_name: '周芳',
    external_user_avatar: undefined,
    internal_user_id: 'mock-user',
    bound_at: daysAgo(7),
    last_active_at: minutesAgo(45),
  },
]

const pending: PairingRequest[] = [...seedPending]
const bindings: IMBinding[] = [...seedBindings]

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

let nextBindId = 100
const newBindId = () => `mock-bind-auto-${nextBindId++}`

export async function mockListPending(): Promise<PairingRequest[]> {
  await new Promise((r) => setTimeout(r, 100))
  // 过滤已过期(剩余 <= 0)
  const fresh = pending.filter((p) => {
    if (p.status !== 'pending') return false
    return new Date(p.expires_at).getTime() > Date.now()
  })
  return clone(fresh)
}

export async function mockApprovePairing(id: string): Promise<PairingRequest> {
  await new Promise((r) => setTimeout(r, 120))
  const idx = pending.findIndex((p) => p.id === id)
  if (idx === -1) throw new Error(`mock pairing not found: ${id}`)
  const req = pending[idx]
  req.status = 'approved'
  req.approved_at = now()
  req.approved_by = 'mock-user'
  // 写入 binding
  bindings.unshift({
    id: newBindId(),
    channel_id: req.channel_id,
    channel_type: req.channel_type,
    channel_name: req.channel_name,
    external_user_id: req.external_user_id,
    external_user_name: req.external_user_name,
    external_user_avatar: req.external_user_avatar,
    internal_user_id: 'mock-user',
    bound_at: now(),
    last_active_at: null,
  })
  // 从 pending 列表移除
  pending.splice(idx, 1)
  return clone(req)
}

export async function mockRejectPairing(
  id: string,
  body: RejectPairingRequest,
): Promise<PairingRequest> {
  await new Promise((r) => setTimeout(r, 120))
  const idx = pending.findIndex((p) => p.id === id)
  if (idx === -1) throw new Error(`mock pairing not found: ${id}`)
  const req = pending[idx]
  req.status = 'rejected'
  req.rejection_reason = body.reason
  pending.splice(idx, 1)
  return clone(req)
}

export async function mockListAuthorized(): Promise<IMBinding[]> {
  await new Promise((r) => setTimeout(r, 100))
  return clone(bindings)
}

export async function mockRevokeBinding(id: string): Promise<void> {
  await new Promise((r) => setTimeout(r, 120))
  const idx = bindings.findIndex((b) => b.id === id)
  if (idx === -1) throw new Error(`mock binding not found: ${id}`)
  bindings.splice(idx, 1)
}
