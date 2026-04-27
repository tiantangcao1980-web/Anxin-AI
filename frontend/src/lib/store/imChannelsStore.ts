/**
 * IM Channels zustand store (V3 消息渠道 P3-C)
 *
 * 集中管理 5 个 IM 渠道的状态、配置与智能体绑定。
 */

import { create } from 'zustand'

import {
  imChannelsApi,
  type IMChannel,
  type IMChannelType,
  type SetupChannelRequest,
  type TestConnectionResult,
} from '@/lib/api/imChannels'

interface IMChannelsState {
  channels: IMChannel[]
  loading: boolean
  loadError: string | null

  // actions
  loadChannels: () => Promise<void>
  setupChannel: (
    channelType: IMChannelType,
    body: SetupChannelRequest,
  ) => Promise<IMChannel>
  bindAgent: (id: string, agentPersona: string) => Promise<IMChannel>
  enableChannel: (id: string) => Promise<void>
  disableChannel: (id: string) => Promise<void>
  testConnection: (id: string) => Promise<TestConnectionResult>
  upsertChannel: (channel: IMChannel) => void
}

export const useIMChannelsStore = create<IMChannelsState>((set, get) => ({
  channels: [],
  loading: false,
  loadError: null,

  loadChannels: async () => {
    set({ loading: true, loadError: null })
    try {
      const channels = await imChannelsApi.listChannels()
      set({ channels, loading: false })
    } catch (e) {
      set({
        loading: false,
        loadError: e instanceof Error ? e.message : '加载失败',
      })
    }
  },

  setupChannel: async (channelType, body) => {
    const updated = await imChannelsApi.setupChannel(channelType, body)
    get().upsertChannel(updated)
    return updated
  },

  bindAgent: async (id, agentPersona) => {
    const updated = await imChannelsApi.bindAgent(id, { agent_persona: agentPersona })
    get().upsertChannel(updated)
    return updated
  },

  enableChannel: async (id) => {
    const updated = await imChannelsApi.enableChannel(id)
    get().upsertChannel(updated)
  },

  disableChannel: async (id) => {
    const updated = await imChannelsApi.disableChannel(id)
    get().upsertChannel(updated)
  },

  testConnection: async (id) => {
    return imChannelsApi.testConnection(id)
  },

  upsertChannel: (channel) =>
    set((s) => {
      const idx = s.channels.findIndex((c) => c.id === channel.id)
      if (idx === -1) return { channels: [...s.channels, channel] }
      const next = s.channels.slice()
      next[idx] = channel
      return { channels: next }
    }),
}))
