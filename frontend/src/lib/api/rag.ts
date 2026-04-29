/**
 * RAG Multimodal API Client (V3 P13-D)
 *
 * 与 P13-A/B/C 后端约定的 8 个 endpoint 的 REST 封装：
 *   1. POST /api/v1/rag/ingest/multimodal   → 触发多模态文档解析（文件上传 / URL）
 *   2. GET  /api/v1/rag/ingest/{task_id}    → 查询解析进度 + 各 segment / layout
 *   3. GET  /api/v1/rag/documents           → 文档库列表
 *   4. GET  /api/v1/rag/documents/{doc_id}  → 文档详情（含 segments + layout tree）
 *   5. POST /api/v1/rag/kg/build            → 触发 KG 构建（基于已 ingest 文档）
 *   6. GET  /api/v1/rag/kg/{kg_id}/cross-modal → 跨模态实体 / 关系
 *   7. POST /api/v1/rag/query/multimodal    → VLM 多模态查询（含模态权重 / visual grounding）
 *   8. GET  /api/v1/rag/query/history       → 查询历史
 *
 * 通过环境变量 `VITE_RAG_MOCK=true` 切换到 mock 适配层
 * （P13-A/B/C 真接口尚未 ready 之前用于前端联调）。
 *
 * 注意：upload 走 multipart/form-data，其它 8 个走 JSON。
 */

import { getTokenStorage } from '@/lib/platform/storage'

// ============================================================
// 类型（与后端 P13-A/B/C schema 对齐 - 跨包契约）
// ============================================================

/** 多模态 segment 的 5 种 modality（后端 layout parser 输出） */
export type Modality = 'text' | 'image' | 'table' | 'formula' | 'seal'

/** 文档 ingest 状态机 */
export type IngestStatus = 'pending' | 'parsing' | 'embedding' | 'completed' | 'failed'

export interface BoundingBox {
  /** 页码（PDF 1-based） */
  page: number
  /** 0~1 归一化坐标 */
  x: number
  y: number
  w: number
  h: number
}

/** 单个 segment（章 / 条 / 款 / 项 / 段 / 表 / 图 / 公式 / 印章 / OCR 块） */
export interface Segment {
  segment_id: string
  doc_id: string
  modality: Modality
  /** 文本内容 / OCR / 表格 markdown / latex */
  content: string
  /** 仅 image / seal modality 时存在 */
  image_url?: string
  /** 仅 image / seal 模态有可读 caption */
  caption?: string
  /** layout 层级路径，例如 "第三章 / 第二条 / 款3" */
  layout_path?: string
  /** 文档内层级深度：0=章 1=条 2=款 3=项 4=段 */
  layout_level?: number
  /** 父 segment id，用于构建 layout tree */
  parent_segment_id?: string | null
  /** 文档源坐标 */
  bbox?: BoundingBox
  /** embedding 向量维度（仅展示用，不返回向量本体） */
  embedding_dim?: number
  /** 检索到此 segment 时的 score（query 返回时使用） */
  score?: number
}

export interface IngestResult {
  task_id: string
  doc_id: string
  filename: string
  status: IngestStatus
  /** 0~100 */
  progress: number
  /** 当前阶段简短文案 */
  stage_label: string
  segments_total: number
  segments_done: number
  /** 解析完成时返回的所有 segments（partial 时可能只返回部分） */
  segments: Segment[]
  /** 错误信息（status === failed） */
  error?: string
  created_at: string
  updated_at: string
}

export interface DocumentSummary {
  doc_id: string
  filename: string
  doc_type: '合同' | '财报' | '公告' | '诉讼文书' | '研报' | string
  page_count: number
  segments_count: number
  /** 各模态计数 — 用于卡片小柱图 */
  modality_breakdown: Record<Modality, number>
  ingest_status: IngestStatus
  ingest_progress: number
  created_at: string
}

export interface DocumentDetail extends DocumentSummary {
  segments: Segment[]
  /** kg_id（已 build 时） */
  kg_id?: string
}

// ----- KG -----

export type EntityType =
  | 'person'
  | 'organization'
  | 'amount'
  | 'date'
  | 'clause'
  | 'figure'
  | 'table_cell'
  | 'formula'
  | 'seal_subject'

export interface KGEntity {
  entity_id: string
  name: string
  entity_type: EntityType
  /** entity 主要锚定的 segment（可点击跳转） */
  anchor_segment_id?: string
  /** entity 出现的 modality（多模态可叠加） */
  modalities: Modality[]
  /** 文档内出现频次 */
  mentions: number
  /** 用于强调的 confidence */
  confidence?: number
}

export interface KGRelation {
  relation_id: string
  source: string
  target: string
  /** 关系名（中文，例如 "签署方 / 涉及金额 / 适用条款"） */
  label: string
  /** 跨模态边：true 时前端用特殊样式（虚线 + 渐变） */
  cross_modal: boolean
  /** 关系来源 modality 对（仅 cross_modal=true 有意义） */
  modality_pair?: [Modality, Modality]
  weight: number
}

export interface CrossModalKG {
  kg_id: string
  doc_id: string
  entities: KGEntity[]
  relations: KGRelation[]
  /** 跨模态边占比 */
  cross_modal_ratio: number
  built_at: string
}

// ----- VLM Query -----

export interface ModalityWeights {
  text: number
  image: number
  table: number
  formula: number
  seal: number
}

export interface VLMQueryRequest {
  query: string
  doc_ids?: string[]
  modality_weights?: Partial<ModalityWeights>
  /** 是否要求 visual grounding（在 segment 上画 bbox） */
  visual_grounding?: boolean
  top_k?: number
}

export interface Citation {
  citation_id: string
  segment_id: string
  doc_id: string
  modality: Modality
  /** 标注用 - 命中片段 */
  snippet: string
  layout_path?: string
  bbox?: BoundingBox
  score: number
}

export interface VLMQueryResponse {
  query_id: string
  query: string
  /** VLM 综合答案（markdown） */
  answer: string
  citations: Citation[]
  /** visual grounding：bbox 列表 */
  groundings: Array<{
    segment_id: string
    bbox: BoundingBox
    label: string
  }>
  /** 命中各模态的 score 直方图 — 用于绘制权重对比 */
  modality_scores: Record<Modality, number>
  used_weights: ModalityWeights
  latency_ms: number
  created_at: string
}

export interface QueryHistoryItem {
  query_id: string
  query: string
  doc_ids: string[]
  citations_count: number
  created_at: string
}

// ============================================================
// Mock 切换
// ============================================================

const USE_MOCK = import.meta.env.VITE_RAG_MOCK === 'true'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// ============================================================
// 通用 fetch 封装
// ============================================================

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const storage = getTokenStorage()
  const token = await storage.getAccessToken()
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  }
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers })
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<T>
}

// ============================================================
// 真实 API 实现
// ============================================================

async function realIngestMultimodal(file: File): Promise<IngestResult> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await authFetch('/rag/ingest/multimodal', { method: 'POST', body: fd })
  return jsonOrThrow<IngestResult>(res)
}

async function realGetIngestStatus(taskId: string): Promise<IngestResult> {
  const res = await authFetch(`/rag/ingest/${encodeURIComponent(taskId)}`)
  return jsonOrThrow<IngestResult>(res)
}

async function realListDocuments(): Promise<DocumentSummary[]> {
  const res = await authFetch('/rag/documents')
  return jsonOrThrow<DocumentSummary[]>(res)
}

async function realGetDocument(docId: string): Promise<DocumentDetail> {
  const res = await authFetch(`/rag/documents/${encodeURIComponent(docId)}`)
  return jsonOrThrow<DocumentDetail>(res)
}

async function realBuildKG(docId: string): Promise<{ kg_id: string }> {
  const res = await authFetch('/rag/kg/build', {
    method: 'POST',
    body: JSON.stringify({ doc_id: docId }),
  })
  return jsonOrThrow<{ kg_id: string }>(res)
}

async function realGetCrossModalKG(kgId: string): Promise<CrossModalKG> {
  const res = await authFetch(`/rag/kg/${encodeURIComponent(kgId)}/cross-modal`)
  return jsonOrThrow<CrossModalKG>(res)
}

async function realQueryMultimodal(req: VLMQueryRequest): Promise<VLMQueryResponse> {
  const res = await authFetch('/rag/query/multimodal', {
    method: 'POST',
    body: JSON.stringify(req),
  })
  return jsonOrThrow<VLMQueryResponse>(res)
}

async function realGetQueryHistory(): Promise<QueryHistoryItem[]> {
  const res = await authFetch('/rag/query/history')
  return jsonOrThrow<QueryHistoryItem[]>(res)
}

// ============================================================
// Mock 适配（懒加载）
// ============================================================

type MockApi = typeof import('./__mocks__/rag.mock')

let mockPromise: Promise<MockApi> | null = null
async function mock(): Promise<MockApi> {
  if (!mockPromise) {
    mockPromise = import('./__mocks__/rag.mock')
  }
  return mockPromise
}

// ============================================================
// 对外导出（按 USE_MOCK 路由）
// ============================================================

export async function ingestMultimodal(file: File): Promise<IngestResult> {
  if (USE_MOCK) return (await mock()).mockIngestMultimodal(file)
  return realIngestMultimodal(file)
}

export async function getIngestStatus(taskId: string): Promise<IngestResult> {
  if (USE_MOCK) return (await mock()).mockGetIngestStatus(taskId)
  return realGetIngestStatus(taskId)
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  if (USE_MOCK) return (await mock()).mockListDocuments()
  return realListDocuments()
}

export async function getDocument(docId: string): Promise<DocumentDetail> {
  if (USE_MOCK) return (await mock()).mockGetDocument(docId)
  return realGetDocument(docId)
}

export async function buildKG(docId: string): Promise<{ kg_id: string }> {
  if (USE_MOCK) return (await mock()).mockBuildKG(docId)
  return realBuildKG(docId)
}

export async function getCrossModalKG(kgId: string): Promise<CrossModalKG> {
  if (USE_MOCK) return (await mock()).mockGetCrossModalKG(kgId)
  return realGetCrossModalKG(kgId)
}

export async function queryMultimodal(req: VLMQueryRequest): Promise<VLMQueryResponse> {
  if (USE_MOCK) return (await mock()).mockQueryMultimodal(req)
  return realQueryMultimodal(req)
}

export async function getQueryHistory(): Promise<QueryHistoryItem[]> {
  if (USE_MOCK) return (await mock()).mockGetQueryHistory()
  return realGetQueryHistory()
}

export const ragApi = {
  ingest: ingestMultimodal,
  ingestStatus: getIngestStatus,
  listDocuments,
  getDocument,
  buildKG,
  getCrossModalKG,
  query: queryMultimodal,
  history: getQueryHistory,
}
