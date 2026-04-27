/**
 * IM Pairing zustand store (V3 配对授权 P3)
 *
 * 集中管理待审请求 + 已授权绑定列表。
 */

import { create } from 'zustand'

import {
  imPairingApi,
  type IMBinding,
  type PairingRequest,
} from '@/lib/api/imPairing'

interface ImPairingState {
  pendingRequests: PairingRequest[]
  bindings: IMBinding[]

  pendingLoading: boolean
  authorizedLoading: boolean

  pendingError: string | null
  authorizedError: string | null

  // actions
  loadPending: () => Promise<void>
  loadAuthorized: () => Promise<void>
  approve: (id: string) => Promise<void>
  reject: (id: string, reason: string) => Promise<void>
  revokeBinding: (id: string) => Promise<void>
}

export const useImPairingStore = create<ImPairingState>((set, get) => ({
  pendingRequests: [],
  bindings: [],

  pendingLoading: false,
  authorizedLoading: false,

  pendingError: null,
  authorizedError: null,

  loadPending: async () => {
    set({ pendingLoading: true, pendingError: null })
    try {
      const list = await imPairingApi.listPending()
      set({ pendingRequests: list, pendingLoading: false })
    } catch (e) {
      set({
        pendingLoading: false,
        pendingError: e instanceof Error ? e.message : '加载失败',
      })
    }
  },

  loadAuthorized: async () => {
    set({ authorizedLoading: true, authorizedError: null })
    try {
      const list = await imPairingApi.listAuthorized()
      set({ bindings: list, authorizedLoading: false })
    } catch (e) {
      set({
        authorizedLoading: false,
        authorizedError: e instanceof Error ? e.message : '加载失败',
      })
    }
  },

  approve: async (id) => {
    await imPairingApi.approvePairing(id)
    // 审批后从 pending 移除,并刷新已授权
    set((s) => ({
      pendingRequests: s.pendingRequests.filter((p) => p.id !== id),
    }))
    await get().loadAuthorized()
  },

  reject: async (id, reason) => {
    await imPairingApi.rejectPairing(id, { reason })
    set((s) => ({
      pendingRequests: s.pendingRequests.filter((p) => p.id !== id),
    }))
  },

  revokeBinding: async (id) => {
    await imPairingApi.revokeBinding(id)
    set((s) => ({
      bindings: s.bindings.filter((b) => b.id !== id),
    }))
  },
}))
