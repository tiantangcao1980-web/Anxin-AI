// -*- coding: utf-8 -*-
/**
 * KnowledgeBase.tsx - 司法智库（知识库管理）
 *
 * 功能：
 * - 知识库 CRUD（列表 / 新建 / 编辑 / 删除）
 * - 文档列表、搜索、筛选
 * - 单文件上传 & 批量拖拽上传
 * - 文档预览（弹窗，完整内容 + 元数据）
 * - 文档编辑（标题、内容、标签、法律元数据）
 * - 知识库导出 JSON
 * - 统计面板（文档数、已索引、分类分布）
 * - Mock 数据 fallback
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { EmptyState, LoadingState } from '@/components/common'
import { PageContainer } from '@/components/ui/PageContainer'
import {
  cardStyle,
  buttonStyle,
  heading,
  statusColor,
  inputStyle,
  iconSize,
  spacing,
} from '@/lib/design-tokens'
import { StatCard as UnifiedStatCard } from '@/components/ui-unified'
import { knowledgeApi, type KnowledgeBase as KB, type KnowledgeDocument } from '@/lib/api'
import { SmartSearch } from '@/components/knowledge-center/SmartSearch'
import { toast } from 'sonner'

// ============================================================
// 常量 & 类型
// ============================================================

const kbTypeLabel: Record<string, string> = {
  law: '法律法规', regulation: '部门规章', case: '司法判例', case_law: '判例',
  interpretation: '司法解释', template: '合同模板', article: '法律文章',
  internal: '内部知识', other: '其他', general: '通用',
}

const kbTypeColor: Record<string, string> = {
  law: statusColor.info, regulation: statusColor.info,
  case: statusColor.success, case_law: statusColor.success,
  interpretation: statusColor.info, template: statusColor.warning,
  article: statusColor.neutral, internal: statusColor.neutral,
  other: statusColor.neutral, general: statusColor.neutral,
}

const kbTypeOptions = [
  { value: '', label: '全部类型' },
  { value: 'general', label: '通用' },
  { value: 'regulation', label: '法规' },
  { value: 'case_law', label: '判例' },
  { value: 'template', label: '模板' },
  { value: 'internal', label: '内部知识' },
]

interface DocDetail extends KnowledgeDocument {
  content?: string
  source_url?: string
  chunk_count?: number
  law_category?: string
  effective_date?: string
  issuing_authority?: string
}

interface BaseStats {
  kb_id: string
  name: string
  doc_count: number
  processed_count: number
  total_chunks: number
  categories: Record<string, number>
}

// (MOCK_BASES / MOCK_DOCS / MOCK_DOC_DETAILS / MOCK_DOC_DETAIL 已移除 — 使用真实 API)

// ============================================================
// 弹窗 Overlay 组件
// ============================================================

function Overlay({ open, onClose, title, wide, children }: {
  open: boolean; onClose: () => void; title: string; wide?: boolean; children: React.ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className={`bg-background border border-border rounded-2xl shadow-xl flex flex-col max-h-[85vh] ${wide ? 'w-full max-w-3xl' : 'w-full max-w-lg'}`}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <h2 className={heading.section}>{title}</h2>
          <button onClick={onClose} className={buttonStyle.icon}><icons.Close className={iconSize.md} /></button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {children}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// 主组件
// ============================================================

export default function KnowledgeBase() {
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<'manage' | 'search'>('manage')
  // ---- 列表视图状态 ----
  const [bases, setBases] = useState<KB[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('')

  // ---- 详情视图状态 ----
  const [selectedBase, setSelectedBase] = useState<KB | null>(null)
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [docLoading, setDocLoading] = useState(false)
  const [docSearch, setDocSearch] = useState('')
  const [stats, setStats] = useState<BaseStats | null>(null)
  const [showStats, setShowStats] = useState(false)
  const [docPage, setDocPage] = useState(1)
  const [docTotal, setDocTotal] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)
  const DOC_PAGE_SIZE = 50

  // ---- 弹窗状态 ----
  const [showCreate, setShowCreate] = useState(false)
  const [editingBase, setEditingBase] = useState<KB | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [previewDoc, setPreviewDoc] = useState<DocDetail | null>(null)
  const [editingDoc, setEditingDoc] = useState<DocDetail | null>(null)
  const [deletingBase, setDeletingBase] = useState<KB | null>(null)

  // ---- 表单状态 ----
  const [baseForm, setBaseForm] = useState({ name: '', description: '', knowledge_type: 'general', is_public: false })
  const [docEditForm, setDocEditForm] = useState({ title: '', content: '', source: '', tags: '', law_category: '', effective_date: '', issuing_authority: '' })

  // ---- 上传状态 ----
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const batchInputRef = useRef<HTMLInputElement>(null)

  // ============================================================
  // 数据加载
  // ============================================================

  const loadBases = useCallback(async () => {
    setLoading(true)
    try {
      const data = await knowledgeApi.listBases(filterType ? { knowledge_type: filterType } : undefined)
      setBases(data.items || [])
    } catch (err: any) {
      toast.error('加载知识库失败: ' + (err.message || '服务不可用'))
      setBases([])
    } finally {
      setLoading(false)
    }
  }, [filterType])

  const loadDocuments = useCallback(async (kbId: string, page = 1, append = false) => {
    if (page === 1) setDocLoading(true)
    else setLoadingMore(true)
    try {
      const data = await knowledgeApi.listDocuments(kbId, { page, page_size: DOC_PAGE_SIZE })
      const items = data.items || []
      setDocuments(prev => append ? [...prev, ...items] : items)
      setDocTotal(data.total || 0)
      setDocPage(page)
    } catch (err: any) {
      toast.error('加载文档失败: ' + (err.message || '服务不可用'))
      if (!append) setDocuments([])
    } finally {
      setDocLoading(false)
      setLoadingMore(false)
    }
  }, [])

  const handleLoadMore = useCallback(() => {
    if (selectedBase) loadDocuments(selectedBase.id, docPage + 1, true)
  }, [selectedBase, docPage, loadDocuments])

  const loadStats = useCallback(async (kbId: string) => {
    try {
      const data = await knowledgeApi.getBaseStats(kbId)
      setStats(data)
    } catch {
      // 统计加载失败不阻塞，设为 null
      setStats(null)
    }
  }, [])

  useEffect(() => { loadBases() }, [loadBases])

  useEffect(() => {
    if (selectedBase) {
      loadDocuments(selectedBase.id)
      loadStats(selectedBase.id)
    }
  }, [selectedBase, loadDocuments, loadStats])

  // ============================================================
  // 知识库 CRUD
  // ============================================================

  const handleCreateBase = async () => {
    if (!baseForm.name.trim()) { toast.error('请输入知识库名称'); return }
    try {
      await knowledgeApi.createBase(baseForm)
      toast.success('知识库创建成功')
      setShowCreate(false)
      setBaseForm({ name: '', description: '', knowledge_type: 'general', is_public: false })
      loadBases()
    } catch (err: any) {
      toast.error('创建失败: ' + (err.message || '未知错误'))
    }
  }

  const handleEditBase = async () => {
    if (!editingBase || !baseForm.name.trim()) { toast.error('请输入知识库名称'); return }
    try {
      await knowledgeApi.updateBase(editingBase.id, baseForm)
      toast.success('知识库更新成功')
      setEditingBase(null)
      loadBases()
      if (selectedBase?.id === editingBase.id) {
        setSelectedBase({ ...selectedBase, ...baseForm } as KB)
      }
    } catch (err: any) {
      toast.error('更新失败: ' + (err.message || '未知错误'))
    }
  }

  const handleDeleteBase = async () => {
    if (!deletingBase) return
    try {
      await knowledgeApi.deleteBase(deletingBase.id)
      toast.success('知识库已删除')
      setDeletingBase(null)
      if (selectedBase?.id === deletingBase.id) {
        setSelectedBase(null)
        setDocuments([])
      }
      loadBases()
    } catch (err: any) {
      toast.error('删除失败: ' + (err.message || '未知错误'))
    }
  }

  const handleExport = async () => {
    if (!selectedBase) return
    try {
      const data = await knowledgeApi.exportBase(selectedBase.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedBase.name}-export.json`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('导出成功')
    } catch (err: any) {
      toast.error('导出失败: ' + (err.message || '未知错误'))
    }
  }

  // ============================================================
  // 文档操作
  // ============================================================

  const handlePreviewDoc = async (doc: KnowledgeDocument) => {
    try {
      const detail = await knowledgeApi.getDocument(doc.id)
      setPreviewDoc(detail)
    } catch (err: any) {
      toast.error('加载文档详情失败: ' + (err.message || '服务不可用'))
    }
  }

  const openDocEdit = (doc: DocDetail) => {
    setDocEditForm({
      title: doc.title || '',
      content: doc.content || '',
      source: doc.source || '',
      tags: (doc.tags || []).join(', '),
      law_category: doc.law_category || '',
      effective_date: doc.effective_date || '',
      issuing_authority: doc.issuing_authority || '',
    })
    setEditingDoc(doc)
    setPreviewDoc(null)
  }

  const handleSaveDoc = async () => {
    if (!editingDoc) return
    try {
      await knowledgeApi.updateDocument(editingDoc.id, {
        title: docEditForm.title,
        content: docEditForm.content,
        source: docEditForm.source,
        tags: docEditForm.tags.split(',').map(t => t.trim()).filter(Boolean),
        law_category: docEditForm.law_category || undefined,
        effective_date: docEditForm.effective_date || undefined,
        issuing_authority: docEditForm.issuing_authority || undefined,
      })
      toast.success('文档更新成功')
      setEditingDoc(null)
      if (selectedBase) loadDocuments(selectedBase.id)
    } catch (err: any) {
      toast.error('更新失败: ' + (err.message || '未知错误'))
    }
  }

  const handleDeleteDoc = async (docId: string) => {
    try {
      await knowledgeApi.deleteDocument(docId)
      toast.success('文档已删除')
      if (selectedBase) loadDocuments(selectedBase.id)
    } catch (err: any) {
      toast.error('删除失败: ' + (err.message || '未知错误'))
    }
  }

  // ============================================================
  // 文件上传
  // ============================================================

  const handleSingleUpload = async (file: File) => {
    if (!selectedBase) return
    setUploading(true)
    try {
      await knowledgeApi.uploadDocument(selectedBase.id, file)
      toast.success(`"${file.name}" 上传成功`)
      loadDocuments(selectedBase.id)
    } catch (err: any) {
      toast.error('上传失败: ' + (err.message || '未知错误'))
    } finally {
      setUploading(false)
    }
  }

  const handleBatchUpload = async (files: FileList | File[]) => {
    if (!selectedBase) return
    const fileArr = Array.from(files)
    if (fileArr.length === 0) return
    setUploading(true)
    try {
      await knowledgeApi.batchUpload(selectedBase.id, fileArr)
      toast.success(`${fileArr.length} 个文件上传成功`)
      loadDocuments(selectedBase.id)
      setShowUpload(false)
    } catch (err: any) {
      toast.error('批量上传失败: ' + (err.message || '未知错误'))
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files.length > 0) {
      handleBatchUpload(e.dataTransfer.files)
    }
  }

  // ============================================================
  // 过滤
  // ============================================================

  const filteredBases = useMemo(() => {
    if (!searchQuery) return bases
    const q = searchQuery.toLowerCase()
    return bases.filter(kb =>
      kb.name.toLowerCase().includes(q) ||
      (kb.description || '').toLowerCase().includes(q)
    )
  }, [bases, searchQuery])

  const filteredDocs = useMemo(() => {
    if (!docSearch) return documents
    const q = docSearch.toLowerCase()
    return documents.filter(doc =>
      doc.title.toLowerCase().includes(q) ||
      (doc.source || '').toLowerCase().includes(q) ||
      (doc.tags || []).some(t => t.toLowerCase().includes(q))
    )
  }, [documents, docSearch])

  // ============================================================
  // 渲染 - 弹窗们
  // ============================================================

  const renderCreateEditModal = () => {
    const isEdit = !!editingBase
    const open = showCreate || !!editingBase
    return (
      <Overlay open={open} onClose={() => { setShowCreate(false); setEditingBase(null) }} title={isEdit ? '编辑知识库' : '新建知识库'}>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">知识库名称 *</label>
            <input
              type="text" value={baseForm.name}
              onChange={e => setBaseForm({ ...baseForm, name: e.target.value })}
              placeholder="例如：公司法规库"
              className={inputStyle.search}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">描述</label>
            <textarea
              value={baseForm.description}
              onChange={e => setBaseForm({ ...baseForm, description: e.target.value })}
              placeholder="简要描述知识库的内容和用途"
              rows={3}
              className={inputStyle.search + ' resize-none'}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">类型</label>
            <select
              value={baseForm.knowledge_type}
              onChange={e => setBaseForm({ ...baseForm, knowledge_type: e.target.value })}
              className={inputStyle.search}
            >
              {kbTypeOptions.filter(o => o.value).map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox" id="kb-public" checked={baseForm.is_public}
              onChange={e => setBaseForm({ ...baseForm, is_public: e.target.checked })}
              className="rounded border-border"
            />
            <label htmlFor="kb-public" className="text-sm text-foreground">公开知识库</label>
          </div>
          <div className="flex gap-2 justify-end pt-2 border-t border-border">
            <button onClick={() => { setShowCreate(false); setEditingBase(null) }} className={buttonStyle.ghost}>取消</button>
            <button onClick={isEdit ? handleEditBase : handleCreateBase} className={buttonStyle.primary}>
              {isEdit ? '保存' : '创建'}
            </button>
          </div>
        </div>
      </Overlay>
    )
  }

  const renderDeleteConfirm = () => (
    <Overlay open={!!deletingBase} onClose={() => setDeletingBase(null)} title="确认删除">
      <div className="space-y-4">
        <p className="text-sm text-foreground">
          确定要删除知识库 <strong>{deletingBase?.name}</strong> 吗？此操作不可撤销，所有关联文档将一并删除。
        </p>
        <div className="flex gap-2 justify-end pt-2 border-t border-border">
          <button onClick={() => setDeletingBase(null)} className={buttonStyle.ghost}>取消</button>
          <button onClick={handleDeleteBase} className={buttonStyle.danger}>确认删除</button>
        </div>
      </div>
    </Overlay>
  )

  const renderUploadModal = () => (
    <Overlay open={showUpload} onClose={() => setShowUpload(false)} title="上传文档">
      <div className="space-y-4">
        {/* 拖拽区域 */}
        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${dragOver ? 'border-primary bg-primary/5' : 'border-border'}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <icons.Save className={`${iconSize.xl} text-muted-foreground mx-auto mb-3`} />
          <p className="text-sm text-foreground font-medium mb-1">拖拽文件到此处上传</p>
          <p className="text-xs text-muted-foreground mb-4">支持 PDF、Word、TXT、Markdown 等格式</p>
          <div className="flex gap-2 justify-center">
            <button onClick={() => fileInputRef.current?.click()} className={buttonStyle.primary} disabled={uploading}>
              <icons.Upload className={`${iconSize.sm} inline-block mr-1`} />
              选择单个文件
            </button>
            <button onClick={() => batchInputRef.current?.click()} className={buttonStyle.secondary} disabled={uploading}>
              <icons.Layers className={`${iconSize.sm} inline-block mr-1`} />
              批量选择
            </button>
          </div>
          <input ref={fileInputRef} type="file" className="hidden" onChange={e => {
            if (e.target.files?.[0]) handleSingleUpload(e.target.files[0])
            e.target.value = ''
          }} />
          <input ref={batchInputRef} type="file" multiple className="hidden" onChange={e => {
            if (e.target.files?.length) handleBatchUpload(e.target.files)
            e.target.value = ''
          }} />
        </div>
        {uploading && (
          <div className="flex items-center gap-2 text-sm text-primary">
            <icons.Refresh className={`${iconSize.sm} animate-spin`} />
            正在上传，请稍候...
          </div>
        )}
      </div>
    </Overlay>
  )

  const renderDocPreview = () => (
    <Overlay open={!!previewDoc} onClose={() => setPreviewDoc(null)} title="文档详情" wide>
      {previewDoc && (
        <div className="space-y-4">
          {/* 元信息 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="text-xs text-muted-foreground">来源</span>
              <p className="text-sm text-foreground">{previewDoc.source || '未知'}</p>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">状态</span>
              <p className="text-sm">
                <span className={`inline-block px-2 py-0.5 rounded-full text-xs ${previewDoc.is_processed ? statusColor.success : statusColor.warning}`}>
                  {previewDoc.is_processed ? '已索引' : '处理中'}
                </span>
              </p>
            </div>
            {previewDoc.law_category && (
              <div>
                <span className="text-xs text-muted-foreground">法律分类</span>
                <p className="text-sm text-foreground">{previewDoc.law_category}</p>
              </div>
            )}
            {previewDoc.issuing_authority && (
              <div>
                <span className="text-xs text-muted-foreground">发布机构</span>
                <p className="text-sm text-foreground">{previewDoc.issuing_authority}</p>
              </div>
            )}
            {previewDoc.effective_date && (
              <div>
                <span className="text-xs text-muted-foreground">生效日期</span>
                <p className="text-sm text-foreground">{previewDoc.effective_date}</p>
              </div>
            )}
            {previewDoc.chunk_count != null && (
              <div>
                <span className="text-xs text-muted-foreground">向量分块</span>
                <p className="text-sm text-foreground">{previewDoc.chunk_count} 块</p>
              </div>
            )}
          </div>
          {/* 标签 */}
          {previewDoc.tags && previewDoc.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {previewDoc.tags.map(tag => (
                <span key={tag} className="text-xs px-2 py-0.5 rounded-md bg-muted text-muted-foreground">{tag}</span>
              ))}
            </div>
          )}
          {/* 摘要 */}
          {previewDoc.summary && (
            <div>
              <span className="text-xs text-muted-foreground block mb-1">摘要</span>
              <p className="text-sm text-foreground/80 leading-relaxed">{previewDoc.summary}</p>
            </div>
          )}
          {/* 正文 */}
          {previewDoc.content && (
            <div>
              <span className="text-xs text-muted-foreground block mb-1">正文内容</span>
              <div className="bg-muted/30 border border-border rounded-lg p-4 max-h-80 overflow-y-auto">
                <pre className="text-sm text-foreground whitespace-pre-wrap font-sans leading-relaxed">{previewDoc.content}</pre>
              </div>
            </div>
          )}
          {/* 操作 */}
          <div className="flex gap-2 justify-end pt-2 border-t border-border">
            <button onClick={() => openDocEdit(previewDoc)} className={buttonStyle.primary}>
              <icons.Edit className={`${iconSize.sm} inline-block mr-1`} />
              编辑
            </button>
            <button onClick={() => setPreviewDoc(null)} className={buttonStyle.ghost}>关闭</button>
          </div>
        </div>
      )}
    </Overlay>
  )

  const renderDocEdit = () => (
    <Overlay open={!!editingDoc} onClose={() => setEditingDoc(null)} title="编辑文档" wide>
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium text-foreground mb-1.5 block">标题</label>
          <input type="text" value={docEditForm.title} onChange={e => setDocEditForm({ ...docEditForm, title: e.target.value })} className={inputStyle.search} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">来源</label>
            <input type="text" value={docEditForm.source} onChange={e => setDocEditForm({ ...docEditForm, source: e.target.value })} className={inputStyle.search} />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">标签 (逗号分隔)</label>
            <input type="text" value={docEditForm.tags} onChange={e => setDocEditForm({ ...docEditForm, tags: e.target.value })} placeholder="民法, 总则" className={inputStyle.search} />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">法律分类</label>
            <input type="text" value={docEditForm.law_category} onChange={e => setDocEditForm({ ...docEditForm, law_category: e.target.value })} placeholder="民法" className={inputStyle.search} />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">生效日期</label>
            <input type="date" value={docEditForm.effective_date} onChange={e => setDocEditForm({ ...docEditForm, effective_date: e.target.value })} className={inputStyle.search} />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">发布机构</label>
            <input type="text" value={docEditForm.issuing_authority} onChange={e => setDocEditForm({ ...docEditForm, issuing_authority: e.target.value })} className={inputStyle.search} />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium text-foreground mb-1.5 block">内容</label>
          <textarea
            value={docEditForm.content}
            onChange={e => setDocEditForm({ ...docEditForm, content: e.target.value })}
            rows={12}
            className={inputStyle.search + ' resize-none font-mono text-xs'}
          />
        </div>
        <div className="flex gap-2 justify-end pt-2 border-t border-border">
          <button onClick={() => setEditingDoc(null)} className={buttonStyle.ghost}>取消</button>
          <button onClick={handleSaveDoc} className={buttonStyle.primary}>保存更改</button>
        </div>
      </div>
    </Overlay>
  )

  // ============================================================
  // 渲染 - 统计面板
  // ============================================================

  const renderStatsPanel = () => {
    if (!showStats || !stats) return null
    const categories = Object.entries(stats.categories || {})
    return (
      <div className={cardStyle.highlight + ' mb-4'}>
        <div className="flex items-center justify-between mb-3">
          <h3 className={heading.section}>知识库统计</h3>
          <button onClick={() => setShowStats(false)} className={buttonStyle.icon}><icons.Close className={iconSize.sm} /></button>
        </div>
        <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-4">
          {/* 数值等宽 + 权重 600 + tnum —— 与全站统计一致 */}
          <div className="text-center">
            <p className="num-tabular text-[28px] font-semibold leading-tight tracking-heading-md text-foreground">{stats.doc_count}</p>
            <p className="text-caption text-foreground-tertiary mt-1">文档总数</p>
          </div>
          <div className="text-center">
            <p className="num-tabular text-[28px] font-semibold leading-tight tracking-heading-md text-success">{stats.processed_count}</p>
            <p className="text-caption text-foreground-tertiary mt-1">已索引</p>
          </div>
          <div className="text-center">
            <p className="num-tabular text-[28px] font-semibold leading-tight tracking-heading-md text-primary">{stats.total_chunks}</p>
            <p className="text-caption text-foreground-tertiary mt-1">向量分块</p>
          </div>
        </div>
        {categories.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">分类分布</p>
            <div className="space-y-1.5">
              {categories.map(([cat, count]) => {
                const pct = stats.doc_count > 0 ? Math.round((count / stats.doc_count) * 100) : 0
                return (
                  <div key={cat} className="flex items-center gap-2">
                    <span className="text-xs text-foreground w-16 shrink-0">{cat}</span>
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-primary/60 rounded-full transition-[width]" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs text-muted-foreground w-12 text-right">{count} ({pct}%)</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    )
  }

  // ============================================================
  // 渲染 - 详情视图（文档列表）
  // ============================================================

  if (selectedBase) {
    return (
      <div data-ui="page-shell" className="h-full flex flex-col bg-surface-2">
        <div data-ui="page-header" className="border-b border-border bg-surface-1 px-4 py-4 shadow-card sm:px-6 shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 mb-3">
            <button onClick={() => { setSelectedBase(null); setDocuments([]); setStats(null); setShowStats(false) }}
              className="p-1.5 rounded-lg hover:bg-muted transition-colors">
              <icons.ArrowLeft className={iconSize.md} />
            </button>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className={heading.page}>{selectedBase.name}</h1>
                <span className={`text-xs px-2 py-0.5 rounded-full ${kbTypeColor[selectedBase.knowledge_type || 'general']}`}>
                  {kbTypeLabel[selectedBase.knowledge_type || 'general'] || '通用'}
                </span>
                {selectedBase.is_public && (
                  <span className="text-xs text-muted-foreground flex items-center gap-0.5">
                    <icons.Globe className={iconSize.xs} /> 公开
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5 hidden sm:block">{selectedBase.description || '暂无描述'}</p>
            </div>
            {/* 操作按钮组 */}
            <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
              <button onClick={() => setShowStats(!showStats)} className={buttonStyle.ghost} title="统计">
                <icons.BarChart3 className={iconSize.sm} />
              </button>
              <button onClick={() => { setBaseForm({ name: selectedBase.name, description: selectedBase.description || '', knowledge_type: selectedBase.knowledge_type || 'general', is_public: selectedBase.is_public || false }); setEditingBase(selectedBase) }} className={buttonStyle.ghost} title="编辑">
                <icons.Edit className={iconSize.sm} />
              </button>
              <button onClick={handleExport} className={buttonStyle.ghost} title="导出">
                <icons.Download className={iconSize.sm} />
              </button>
              <button onClick={() => setDeletingBase(selectedBase)} className={`${buttonStyle.ghost} text-destructive hover:text-destructive`} title="删除">
                <icons.Delete className={iconSize.sm} />
              </button>
            </div>
          </div>
          {/* 搜索 & 上传 */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <div className="relative flex-1">
              <icons.Search className={`${iconSize.sm} absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground`} />
              <input
                type="text" value={docSearch} onChange={e => setDocSearch(e.target.value)}
                placeholder="搜索文档标题、来源、标签..."
                className={inputStyle.search + ' pl-9'}
              />
            </div>
            <button onClick={() => setShowUpload(true)} className={buttonStyle.primary + ' whitespace-nowrap'}>
              <icons.Upload className={`${iconSize.sm} inline-block mr-1`} />
              上传文档
            </button>
          </div>
        </div>

        {/* 内容区 */}
        <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
          {renderStatsPanel()}

          {docLoading ? (
            <LoadingState />
          ) : filteredDocs.length === 0 ? (
            <EmptyState
              icon={docSearch ? 'Search' : 'FileText'}
              title={docSearch ? '没有找到匹配的文档' : '暂无文档'}
              description={docSearch ? '尝试修改搜索关键词' : '上传文件开始构建知识库'}
              action={!docSearch ? { label: '上传文档', onClick: () => setShowUpload(true) } : undefined}
            />
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground mb-2">
                显示 {filteredDocs.length} / {docTotal} 篇文档
                {docSearch && ` (搜索: "${docSearch}")`}
              </p>
              {filteredDocs.map(doc => (
                <div key={doc.id} className={cardStyle.interactive + ' group'} onClick={() => handlePreviewDoc(doc)}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <icons.FileText className={`${iconSize.sm} text-muted-foreground flex-shrink-0`} />
                        <h3 className={heading.card}>{doc.title}</h3>
                      </div>
                      {doc.summary && <p className="text-xs text-muted-foreground ml-6 line-clamp-2">{doc.summary}</p>}
                      <div className="flex items-center gap-3 mt-2 ml-6">
                        {doc.source && (
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <icons.Link className={iconSize.xs} /> {doc.source}
                          </span>
                        )}
                        {doc.created_at && (
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <icons.Calendar className={iconSize.xs} /> {doc.created_at.slice(0, 10)}
                          </span>
                        )}
                        {doc.tags?.map(tag => (
                          <span key={tag} className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{tag}</span>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${doc.is_processed ? statusColor.success : statusColor.warning}`}>
                        {doc.is_processed ? '已索引' : '处理中'}
                      </span>
                      {/* Hover 操作 */}
                      <div className="hidden group-hover:flex items-center gap-1">
                        <button
                          onClick={e => { e.stopPropagation(); handlePreviewDoc(doc).then(() => { if (previewDoc) openDocEdit(previewDoc) }) }}
                          className={buttonStyle.icon} title="编辑"
                        >
                          <icons.Edit className={iconSize.sm} />
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); handleDeleteDoc(doc.id) }}
                          className={`${buttonStyle.icon} text-destructive hover:text-destructive`} title="删除"
                        >
                          <icons.Delete className={iconSize.sm} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {/* 加载更多按钮 */}
              {!docSearch && documents.length < docTotal && (
                <div className="flex justify-center pt-4">
                  <button
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className={buttonStyle.ghost + ' text-sm'}
                  >
                    {loadingMore ? (
                      <><icons.Refresh className={`${iconSize.sm} animate-spin inline-block mr-1`} />加载中...</>
                    ) : (
                      <>加载更多 ({documents.length}/{docTotal})</>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 弹窗 */}
        {renderCreateEditModal()}
        {renderDeleteConfirm()}
        {renderUploadModal()}
        {renderDocPreview()}
        {renderDocEdit()}
      </div>
    )
  }

  // ============================================================
  // 渲染 - 知识库列表视图
  // ============================================================

  return (
    <PageContainer
      title="司法智库"
      actions={
        viewMode === 'manage' ? (
        <button onClick={() => { setBaseForm({ name: '', description: '', knowledge_type: 'general', is_public: false }); setShowCreate(true) }} className={buttonStyle.primary}>
          <icons.Plus className={`${iconSize.sm} inline-block mr-1`} />
          新建知识库
        </button>
        ) : null
      }
      toolbar={
        <div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex w-fit gap-1.5 rounded-xl bg-muted p-1">
            {[
              { key: 'manage', label: '知识库管理', icon: icons.Database },
              { key: 'search', label: '智慧搜索', icon: icons.Search },
            ].map(item => (
              <button
                key={item.key}
                type="button"
                onClick={() => setViewMode(item.key as 'manage' | 'search')}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewMode === item.key
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <item.icon className={iconSize.xs} />
                {item.label}
              </button>
            ))}
          </div>
          {viewMode === 'manage' && (
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3 w-full xl:w-auto xl:flex-1 xl:justify-end">
          <div className="relative flex-1 max-w-md">
            <icons.Search className={`${iconSize.sm} absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground`} />
            <input
              type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
              placeholder="搜索知识库名称或描述..."
              className={inputStyle.search + ' pl-9'}
            />
          </div>
          <select value={filterType} onChange={e => setFilterType(e.target.value)} className={inputStyle.search + ' w-full sm:w-32'}>
            {kbTypeOptions.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          </div>
          )}
        </div>
      }
    >
      {viewMode === 'search' ? (
        <div className="min-h-[720px] overflow-hidden rounded-xl border border-border bg-background">
          <SmartSearch />
        </div>
      ) : (
      <div>
        {loading ? (
          <LoadingState />
        ) : filteredBases.length === 0 ? (
          <EmptyState
            icon={searchQuery || filterType ? 'Search' : 'BookOpen'}
            title={searchQuery || filterType ? '没有找到匹配的知识库' : '暂无知识库'}
            description={searchQuery || filterType ? '尝试修改搜索条件' : '创建第一个知识库开始管理法律知识'}
            action={!searchQuery && !filterType ? { label: '新建知识库', onClick: () => { setBaseForm({ name: '', description: '', knowledge_type: 'general', is_public: false }); setShowCreate(true) } } : undefined}
          />
        ) : (
          <>
            {/* 统计摘要 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              {[
                { label: '知识库', value: filteredBases.length, icon: icons.BookOpen, tone: 'primary' as const },
                { label: '总文档', value: filteredBases.reduce((sum, kb) => sum + ((kb as any).document_count || kb.doc_count || 0), 0), icon: icons.FileText, tone: 'success' as const },
                { label: '类型', value: new Set(filteredBases.map(kb => kb.knowledge_type)).size, icon: icons.Tag, tone: 'warning' as const },
                { label: '公开', value: filteredBases.filter(kb => kb.is_public).length, icon: icons.Globe, tone: 'default' as const },
              ].map((stat, index) => (
                <UnifiedStatCard
                  key={stat.label}
                  index={index}
                  icon={stat.icon}
                  tone={stat.tone}
                  label={stat.label}
                  value={stat.value}
                />
              ))}
            </div>

            <p className="text-xs text-muted-foreground mb-3">
              共 {filteredBases.length} 个知识库
              {searchQuery && ` (搜索: "${searchQuery}")`}
              {filterType && ` (类型: ${kbTypeLabel[filterType] || filterType})`}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredBases.map(kb => (
                <div key={kb.id} className={cardStyle.interactive + ' group relative'} onClick={() => setSelectedBase(kb)}>
                  {/* 操作菜单 */}
                  <div className="absolute top-3 right-3 hidden group-hover:flex items-center gap-1 z-10">
                    <button onClick={e => { e.stopPropagation(); setBaseForm({ name: kb.name, description: kb.description || '', knowledge_type: kb.knowledge_type || 'general', is_public: kb.is_public || false }); setEditingBase(kb) }}
                      className="p-1 rounded hover:bg-muted" title="编辑">
                      <icons.Edit className={iconSize.xs} />
                    </button>
                    <button onClick={e => { e.stopPropagation(); setDeletingBase(kb) }}
                      className="p-1 rounded hover:bg-muted text-destructive" title="删除">
                      <icons.Delete className={iconSize.xs} />
                    </button>
                  </div>

                  <div className="flex items-start justify-between mb-3">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                      <icons.BookOpen className={`${iconSize.md} text-primary`} />
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${kbTypeColor[kb.knowledge_type || 'general']}`}>
                      {kbTypeLabel[kb.knowledge_type || 'general'] || '通用'}
                    </span>
                  </div>
                  <h3 className={heading.card + ' mb-1'}>{kb.name}</h3>
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{kb.description || '暂无描述'}</p>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <icons.FileText className={iconSize.xs} />
                      {(kb as any).document_count || kb.doc_count || 0} 篇文档
                    </span>
                    <span className="flex items-center gap-1">
                      {kb.is_public ? <><icons.Globe className={iconSize.xs} /> 公开</> : <><icons.Lock className={iconSize.xs} /> 私有</>}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
      )}

      {/* 弹窗 */}
      {renderCreateEditModal()}
      {renderDeleteConfirm()}
    </PageContainer>
  )
}
