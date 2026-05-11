/**
 * RAG zustand store (V3 P13-D)
 *
 * 集中管理：
 *   - ingest 队列（taskId → IngestResult，含进度轮询）
 *   - 文档库（documents 列表 + 当前选中 doc_id + 详情）
 *   - 当前文档的 KG（cross-modal 实体 / 关系）
 *   - 查询历史 + 当前 VLM 答案
 *   - 模态权重（用于 query 调优）
 *
 * 透明走 lib/api/rag.ts，VITE_RAG_MOCK=true 时切 mock。
 */

import { create } from 'zustand'

import {
  ragApi,
  type CrossModalKG,
  type DocumentDetail,
  type DocumentSummary,
  type IngestResult,
  type ModalityWeights,
  type QueryHistoryItem,
  type VLMQueryRequest,
  type VLMQueryResponse,
} from '@/lib/api/rag'

const DEFAULT_WEIGHTS: ModalityWeights = {
  text: 0.4,
  image: 0.15,
  table: 0.25,
  formula: 0.1,
  seal: 0.1,
}

interface RagState {
  // ===== Ingest 队列 =====
  ingestTasks: Record<string, IngestResult>
  ingestPolling: Record<string, number> // taskId → setInterval handle
  enqueueIngest: (file: File) => Promise<string>
  pollIngest: (taskId: string) => Promise<void>
  stopAllPolling: () => void

  // ===== 文档库 =====
  documents: DocumentSummary[]
  documentsLoading: boolean
  documentsError: string | null
  currentDocument: DocumentDetail | null
  currentDocumentLoading: boolean
  loadDocuments: () => Promise<void>
  loadDocument: (docId: string) => Promise<void>

  // ===== KG =====
  currentKG: CrossModalKG | null
  kgLoading: boolean
  kgError: string | null
  loadKGForDoc: (docId: string) => Promise<void>
  loadAggregateKG: () => Promise<void>

  // ===== Query =====
  modalityWeights: ModalityWeights
  setModalityWeights: (w: Partial<ModalityWeights>) => void
  resetModalityWeights: () => void

  visualGrounding: boolean
  setVisualGrounding: (b: boolean) => void

  selectedDocIdsForQuery: string[]
  setSelectedDocIdsForQuery: (ids: string[]) => void

  currentAnswer: VLMQueryResponse | null
  queryPending: boolean
  queryError: string | null
  runQuery: (q: string) => Promise<void>

  history: QueryHistoryItem[]
  historyLoading: boolean
  loadHistory: () => Promise<void>
}

export const useRagStore = create<RagState>((set, get) => ({
  // ----- ingest -----
  ingestTasks: {},
  ingestPolling: {},

  enqueueIngest: async (file) => {
    const initial = await ragApi.ingest(file)
    set((s) => ({ ingestTasks: { ...s.ingestTasks, [initial.task_id]: initial } }))
    // 启动轮询
    void get().pollIngest(initial.task_id)
    return initial.task_id
  },

  pollIngest: async (taskId) => {
    const existing = get().ingestPolling[taskId]
    if (existing) return // 已在轮询

    const tick = async () => {
      try {
        const next = await ragApi.ingestStatus(taskId)
        set((s) => ({ ingestTasks: { ...s.ingestTasks, [taskId]: next } }))
        if (next.status === 'completed' || next.status === 'failed') {
          const handle = get().ingestPolling[taskId]
          if (handle) {
            window.clearInterval(handle)
            set((s) => {
              const { [taskId]: _drop, ...rest } = s.ingestPolling
              return { ingestPolling: rest }
            })
          }
        }
      } catch (e) {
        console.warn('[ragStore] poll ingest failed:', e)
      }
    }
    // 立即跑一次再开周期
    await tick()
    const handle = window.setInterval(() => void tick(), 800)
    set((s) => ({ ingestPolling: { ...s.ingestPolling, [taskId]: handle } }))
  },

  stopAllPolling: () => {
    const handles = get().ingestPolling
    Object.values(handles).forEach((h) => window.clearInterval(h))
    set({ ingestPolling: {} })
  },

  // ----- 文档库 -----
  documents: [],
  documentsLoading: false,
  documentsError: null,
  currentDocument: null,
  currentDocumentLoading: false,

  loadDocuments: async () => {
    set({ documentsLoading: true, documentsError: null })
    try {
      const documents = await ragApi.listDocuments()
      set({ documents, documentsLoading: false })
    } catch (e) {
      set({
        documentsLoading: false,
        documentsError: e instanceof Error ? e.message : '加载文档库失败',
      })
    }
  },

  loadDocument: async (docId) => {
    set({ currentDocumentLoading: true })
    try {
      const detail = await ragApi.getDocument(docId)
      set({ currentDocument: detail, currentDocumentLoading: false })
    } catch (e) {
      set({
        currentDocumentLoading: false,
        documentsError: e instanceof Error ? e.message : '加载文档详情失败',
      })
    }
  },

  // ----- KG -----
  currentKG: null,
  kgLoading: false,
  kgError: null,

  loadKGForDoc: async (docId) => {
    set({ kgLoading: true, kgError: null })
    try {
      const { kg_id } = await ragApi.buildKG(docId)
      const kg = await ragApi.getCrossModalKG(kg_id)
      set({ currentKG: kg, kgLoading: false })
    } catch (e) {
      set({
        kgLoading: false,
        kgError: e instanceof Error ? e.message : '加载 KG 失败',
      })
    }
  },

  loadAggregateKG: async () => {
    set({ kgLoading: true, kgError: null })
    try {
      const kg = await ragApi.getCrossModalKG('kg_aggregate')
      set({ currentKG: kg, kgLoading: false })
    } catch (e) {
      set({
        kgLoading: false,
        kgError: e instanceof Error ? e.message : '加载聚合 KG 失败',
      })
    }
  },

  // ----- Query -----
  modalityWeights: { ...DEFAULT_WEIGHTS },
  setModalityWeights: (w) =>
    set((s) => ({ modalityWeights: { ...s.modalityWeights, ...w } })),
  resetModalityWeights: () => set({ modalityWeights: { ...DEFAULT_WEIGHTS } }),

  visualGrounding: true,
  setVisualGrounding: (b) => set({ visualGrounding: b }),

  selectedDocIdsForQuery: [],
  setSelectedDocIdsForQuery: (ids) => set({ selectedDocIdsForQuery: ids }),

  currentAnswer: null,
  queryPending: false,
  queryError: null,

  runQuery: async (q) => {
    set({ queryPending: true, queryError: null })
    try {
      const req: VLMQueryRequest = {
        query: q,
        doc_ids: get().selectedDocIdsForQuery,
        modality_weights: get().modalityWeights,
        visual_grounding: get().visualGrounding,
        top_k: 6,
      }
      const ans = await ragApi.query(req)
      set({ currentAnswer: ans, queryPending: false })
      // 顺便刷新历史
      void get().loadHistory()
    } catch (e) {
      set({
        queryPending: false,
        queryError: e instanceof Error ? e.message : 'Query 失败',
      })
    }
  },

  history: [],
  historyLoading: false,
  loadHistory: async () => {
    set({ historyLoading: true })
    try {
      const items = await ragApi.history()
      set({ history: items, historyLoading: false })
    } catch (e) {
      console.warn('[ragStore] load history failed:', e)
      set({ historyLoading: false })
    }
  },
}))
