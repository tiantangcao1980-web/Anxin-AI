/**
 * IM Channels Mock 适配层
 *
 * 在 VITE_IM_MOCK=true 时启用，供 P3-C 阶段在后端 IM API 就绪前完成前端联调。
 *
 * 默认返回 5 个渠道：
 *   - 飞书（已连接，绑定 contract_steward，12 用户 / 3 群聊 / 1 待处理）
 *   - 微信（已连接，绑定 anxin_assistant，5 用户 / 0 群聊 / 0 待处理）
 *   - 钉钉、Telegram、Discord（未配置，统计全 0）
 */

import type {
  BindAgentRequest,
  IMChannel,
  IMChannelType,
  SetupChannelRequest,
  TestConnectionResult,
} from '../imChannels'

const now = () => new Date().toISOString()
const minutesAgo = (n: number) => new Date(Date.now() - n * 60_000).toISOString()
const daysAgo = (n: number) => new Date(Date.now() - n * 86_400_000).toISOString()

const seedChannels: IMChannel[] = [
  {
    id: 'mock-ch-feishu',
    channel_type: 'feishu',
    name: '飞书机器人',
    config: {
      app_id: 'cli_a1b2c3d4',
      verify_token: '***',
    },
    enabled: true,
    status: 'connected',
    bound_agent_persona: 'contract_steward',
    stats: {
      bound_users: 12,
      bound_groups: 3,
      pending_pairings: 1,
    },
    created_at: daysAgo(7),
  },
  {
    id: 'mock-ch-wechat',
    channel_type: 'wechat',
    name: '微信ClawBot',
    config: {
      corp_id: 'ww1234567890',
    },
    enabled: true,
    status: 'connected',
    bound_agent_persona: 'anxin_assistant',
    stats: {
      bound_users: 5,
      bound_groups: 0,
      pending_pairings: 0,
    },
    created_at: daysAgo(3),
  },
  {
    id: 'mock-ch-dingtalk',
    channel_type: 'dingtalk',
    name: '钉钉机器人',
    config: {},
    enabled: false,
    status: 'unconfigured',
    bound_agent_persona: null,
    stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 },
    created_at: daysAgo(0),
  },
  {
    id: 'mock-ch-telegram',
    channel_type: 'telegram',
    name: 'Telegram Bot',
    config: {},
    enabled: false,
    status: 'unconfigured',
    bound_agent_persona: null,
    stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 },
    created_at: daysAgo(0),
  },
  {
    id: 'mock-ch-discord',
    channel_type: 'discord',
    name: 'Discord Bot',
    config: {},
    enabled: false,
    status: 'unconfigured',
    bound_agent_persona: null,
    stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 },
    created_at: daysAgo(0),
  },
]

const channels: IMChannel[] = [...seedChannels]

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

function findByType(type: IMChannelType): IMChannel | undefined {
  return channels.find((c) => c.channel_type === type)
}

export async function mockListChannels(): Promise<IMChannel[]> {
  await new Promise((r) => setTimeout(r, 120))
  return clone(channels)
}

export async function mockSetupChannel(
  channelType: IMChannelType,
  body: SetupChannelRequest,
): Promise<IMChannel> {
  await new Promise((r) => setTimeout(r, 220))
  const existing = findByType(channelType)
  if (existing) {
    existing.config = { ...existing.config, ...body.config }
    existing.status = 'connected'
    existing.enabled = true
    return clone(existing)
  }
  // 兜底：未在 seed 中的 channel_type（理论上不会触发）
  const fresh: IMChannel = {
    id: `mock-ch-${channelType}-${Date.now()}`,
    channel_type: channelType,
    name: channelType,
    config: body.config,
    enabled: true,
    status: 'connected',
    bound_agent_persona: null,
    stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 },
    created_at: now(),
  }
  channels.push(fresh)
  return clone(fresh)
}

export async function mockBindAgent(
  id: string,
  body: BindAgentRequest,
): Promise<IMChannel> {
  await new Promise((r) => setTimeout(r, 100))
  const ch = channels.find((c) => c.id === id)
  if (!ch) throw new Error(`mock channel not found: ${id}`)
  ch.bound_agent_persona = body.agent_persona
  return clone(ch)
}

export async function mockEnableChannel(id: string): Promise<IMChannel> {
  await new Promise((r) => setTimeout(r, 80))
  const ch = channels.find((c) => c.id === id)
  if (!ch) throw new Error(`mock channel not found: ${id}`)
  ch.enabled = true
  if (ch.status === 'unconfigured') {
    // 未配置不能 enable，保持 unconfigured
    ch.enabled = false
  }
  return clone(ch)
}

export async function mockDisableChannel(id: string): Promise<IMChannel> {
  await new Promise((r) => setTimeout(r, 80))
  const ch = channels.find((c) => c.id === id)
  if (!ch) throw new Error(`mock channel not found: ${id}`)
  ch.enabled = false
  return clone(ch)
}

export async function mockTestConnection(id: string): Promise<TestConnectionResult> {
  await new Promise((r) => setTimeout(r, 400))
  const ch = channels.find((c) => c.id === id)
  if (!ch) throw new Error(`mock channel not found: ${id}`)
  if (ch.status !== 'connected') {
    return { ok: false, message: '渠道尚未配置' }
  }
  return {
    ok: true,
    message: '连接正常',
    detail: { ping_at: minutesAgo(0) },
  }
}
