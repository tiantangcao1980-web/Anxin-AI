/**
 * App Authorizations zustand store (V3 应用授权 P4-F)
 *
 * 集中管理 provider 列表 + 当前用户已连接授权 + 搜索与分类筛选状态。
 *
 * 切换 mock 模式只在 API 层 (VITE_APP_AUTH_MOCK=true) 透明完成。
 */

import { create } from 'zustand'

import {
  appAuthorizationsApi,
  type AppAuthorization,
  type AppCategory,
  type AppProvider,
} from '@/lib/api/appAuthorizations'

/** 分类筛选 — "all" 表示全部 */
export type AppCategoryFilter = 'all' | AppCategory

interface AppAuthorizationsState {
  // 数据
  providers: AppProvider[]
  authorizations: AppAuthorization[]

  // UI 筛选
  searchQuery: string
  selectedCategory: AppCategoryFilter

  // 加载态
  providersLoading: boolean
  authorizationsLoading: boolean
  loadError: string | null

  // ===== actions =====
  loadProviders: () => Promise<void>
  loadAuthorizations: () => Promise<void>
  startConnect: (providerId: string) => Promise<{ authorize_url: string; state: string }>
  /** mock 模式下专用：模拟完成 OAuth 回写授权（真实环境由 callback 触发） */
  completeMockConnect: (providerId: string) => Promise<AppAuthorization>
  refresh: (id: string) => Promise<void>
  disconnect: (id: string) => Promise<void>
  setSearch: (q: string) => void
  setCategory: (c: AppCategoryFilter) => void

  // ===== selectors =====
  /** 按 query + category 过滤 provider 列表 */
  getFilteredProviders: () => AppProvider[]
  /** 取某 provider 的当前授权，未连接返回 null */
  getAuthorizationFor: (providerId: string) => AppAuthorization | null
  /** 已连接 provider_id 集合 */
  getConnectedProviderIds: () => Set<string>
}

export const useAppAuthorizationsStore = create<AppAuthorizationsState>((set, get) => ({
  providers: [],
  authorizations: [],
  searchQuery: '',
  selectedCategory: 'all',
  providersLoading: false,
  authorizationsLoading: false,
  loadError: null,

  loadProviders: async () => {
    set({ providersLoading: true, loadError: null })
    try {
      const providers = await appAuthorizationsApi.listProviders()
      set({ providers, providersLoading: false })
    } catch (e) {
      set({
        providersLoading: false,
        loadError: e instanceof Error ? e.message : '加载应用列表失败',
      })
    }
  },

  loadAuthorizations: async () => {
    set({ authorizationsLoading: true })
    try {
      const authorizations = await appAuthorizationsApi.listAuthorizations()
      set({ authorizations, authorizationsLoading: false })
    } catch (e) {
      set({
        authorizationsLoading: false,
        loadError: e instanceof Error ? e.message : '加载授权列表失败',
      })
    }
  },

  startConnect: async (providerId) => {
    return appAuthorizationsApi.startConnect(providerId)
  },

  completeMockConnect: async (providerId) => {
    // 仅在 mock 模式下生效；真实模式建议 callback 回写后 reload
    const mod = await import('@/lib/api/__mocks__/appAuthorizations.mock')
    const auth = await mod.mockCompleteConnect(providerId)
    set((s) => {
      const idx = s.authorizations.findIndex((a) => a.id === auth.id)
      if (idx === -1) return { authorizations: [...s.authorizations, auth] }
      const next = s.authorizations.slice()
      next[idx] = auth
      return { authorizations: next }
    })
    return auth
  },

  refresh: async (id) => {
    const updated = await appAuthorizationsApi.refresh(id)
    set((s) => {
      const idx = s.authorizations.findIndex((a) => a.id === id)
      if (idx === -1) return { authorizations: [...s.authorizations, updated] }
      const next = s.authorizations.slice()
      next[idx] = updated
      return { authorizations: next }
    })
  },

  disconnect: async (id) => {
    await appAuthorizationsApi.disconnect(id)
    set((s) => ({
      authorizations: s.authorizations.filter((a) => a.id !== id),
    }))
  },

  setSearch: (q) => set({ searchQuery: q }),
  setCategory: (c) => set({ selectedCategory: c }),

  // ===== selectors =====
  getFilteredProviders: () => {
    const { providers, searchQuery, selectedCategory } = get()
    const q = searchQuery.trim().toLowerCase()
    return providers.filter((p) => {
      if (selectedCategory !== 'all' && p.category !== selectedCategory) return false
      if (!q) return true
      return (
        p.display_name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.provider_id.toLowerCase().includes(q)
      )
    })
  },

  getAuthorizationFor: (providerId) => {
    return get().authorizations.find((a) => a.provider_id === providerId) ?? null
  },

  getConnectedProviderIds: () => {
    return new Set(
      get()
        .authorizations.filter((a) => a.status === 'connected')
        .map((a) => a.provider_id),
    )
  },
}))
