/**
 * Personas zustand store (V3 P8-C)
 *
 * 集中管理 10 个 user-facing persona 的列表 / 选中 / 过滤 / chat 历史。
 *
 * 通过 API 层 (VITE_PERSONAS_MOCK=true) 透明切换 mock。
 */

import { create } from 'zustand'

import {
  personasApi,
  type ChatHistoryItem,
  type ChatRequest,
  type Persona,
  type PersonaDetail,
} from '@/lib/api/personas'

export type PersonaImplementedFilter = 'all' | 'implemented' | 'planned'

interface ChatThread {
  personaId: string
  history: ChatHistoryItem[]
  /** 最后一次 chat 的 metadata（含 is_implemented 等） */
  lastMetadata?: Record<string, unknown>
}

interface PersonasState {
  // 数据
  personas: Persona[]
  selectedPersonaId: string | null
  selectedPersonaDetail: PersonaDetail | null

  // UI 筛选
  searchQuery: string
  implementedFilter: PersonaImplementedFilter

  // 加载态
  loading: boolean
  detailLoading: boolean
  chatPending: boolean
  loadError: string | null

  // chat 历史（按 personaId 分线程）
  threads: Record<string, ChatThread>

  // ===== actions =====
  loadPersonas: () => Promise<void>
  selectPersona: (personaId: string | null) => Promise<void>
  setSearch: (q: string) => void
  setImplementedFilter: (f: PersonaImplementedFilter) => void
  chat: (personaId: string, message: string, extra?: Record<string, unknown>) => Promise<void>
  clearThread: (personaId: string) => void

  // ===== selectors =====
  getFilteredPersonas: () => Persona[]
  getPersonaById: (personaId: string) => Persona | undefined
  getThread: (personaId: string) => ChatThread
}

const emptyThread = (personaId: string): ChatThread => ({
  personaId,
  history: [],
})

export const usePersonasStore = create<PersonasState>((set, get) => ({
  personas: [],
  selectedPersonaId: null,
  selectedPersonaDetail: null,

  searchQuery: '',
  implementedFilter: 'all',

  loading: false,
  detailLoading: false,
  chatPending: false,
  loadError: null,

  threads: {},

  loadPersonas: async () => {
    set({ loading: true, loadError: null })
    try {
      const personas = await personasApi.list()
      set({ personas, loading: false })
    } catch (e) {
      set({
        loading: false,
        loadError: e instanceof Error ? e.message : '加载 persona 列表失败',
      })
    }
  },

  selectPersona: async (personaId) => {
    set({ selectedPersonaId: personaId })
    if (!personaId) {
      set({ selectedPersonaDetail: null })
      return
    }
    set({ detailLoading: true })
    try {
      const detail = await personasApi.get(personaId)
      set({ selectedPersonaDetail: detail, detailLoading: false })
    } catch (e) {
      set({
        detailLoading: false,
        loadError: e instanceof Error ? e.message : '加载 persona 详情失败',
      })
    }
  },

  setSearch: (q) => set({ searchQuery: q }),

  setImplementedFilter: (f) => set({ implementedFilter: f }),

  chat: async (personaId, message, extra) => {
    const thread = get().getThread(personaId)
    const userMsg: ChatHistoryItem = { role: 'user', content: message }

    // 乐观先把 user 消息推进 thread
    set((s) => ({
      threads: {
        ...s.threads,
        [personaId]: {
          ...thread,
          history: [...thread.history, userMsg],
        },
      },
      chatPending: true,
    }))

    try {
      const body: ChatRequest = {
        message,
        history: thread.history,
        extra,
      }
      const resp = await personasApi.chat(personaId, body)
      const aiMsg: ChatHistoryItem = { role: 'assistant', content: resp.content }
      set((s) => {
        const t = s.threads[personaId] ?? emptyThread(personaId)
        return {
          threads: {
            ...s.threads,
            [personaId]: {
              ...t,
              history: [...t.history, aiMsg],
              lastMetadata: resp.metadata,
            },
          },
          chatPending: false,
        }
      })
    } catch (e) {
      const aiMsg: ChatHistoryItem = {
        role: 'assistant',
        content: `❌ 调用失败：${e instanceof Error ? e.message : '未知错误'}`,
      }
      set((s) => {
        const t = s.threads[personaId] ?? emptyThread(personaId)
        return {
          threads: {
            ...s.threads,
            [personaId]: {
              ...t,
              history: [...t.history, aiMsg],
            },
          },
          chatPending: false,
          loadError: e instanceof Error ? e.message : 'chat 失败',
        }
      })
    }
  },

  clearThread: (personaId) =>
    set((s) => ({
      threads: { ...s.threads, [personaId]: emptyThread(personaId) },
    })),

  getFilteredPersonas: () => {
    const { personas, searchQuery, implementedFilter } = get()
    const q = searchQuery.trim().toLowerCase()
    return personas.filter((p) => {
      if (implementedFilter === 'implemented' && !p.is_implemented) return false
      if (implementedFilter === 'planned' && p.is_implemented) return false
      if (!q) return true
      return (
        p.display_name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.persona_id.toLowerCase().includes(q) ||
        p.capabilities.some((c) => c.toLowerCase().includes(q)) ||
        (p.domain ?? '').toLowerCase().includes(q)
      )
    })
  },

  getPersonaById: (personaId) => get().personas.find((p) => p.persona_id === personaId),

  getThread: (personaId) => get().threads[personaId] ?? emptyThread(personaId),
}))
