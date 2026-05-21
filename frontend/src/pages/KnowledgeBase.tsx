// -*- coding: utf-8 -*-
/**
 * KnowledgeBase · 司法智库（Editorial Luxury 改造 · Phase 1.18）
 *
 * 旧版：PageContainer + cardStyle.interactive 3 列卡片 + statusColor 色块 + 圆形药丸 Tab。
 * 新版：EditorialPageHeader + 1px hairline 三列网格 + tone-only ToneTag + Editorial Tab 下划线。
 *
 * 功能保留：知识库 CRUD / 文档列表+搜索+筛选 / 单/批量上传 / 文档预览/编辑 /
 * 导出 JSON / 统计面板 / SmartSearch 嵌入。
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  Plus, Search, Upload, Layers, BookOpen, FileText, Tag, Globe, Lock,
  ArrowLeft, Edit2, Trash2, Download, BarChart3, Database, X, Link2, Calendar,
  Loader2, AlertCircle,
} from 'lucide-react'
import { toast } from 'sonner'

import { knowledgeApi, type KnowledgeBase as KB, type KnowledgeDocument } from '@/lib/api'
import { SmartSearch } from '@/components/knowledge-center/SmartSearch'
import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import { cn } from '@/components/ui/utils'

// =============== 常量 ===============
const kbTypeMeta: Record<string, { label: string; labelEn: string; tone: 'normal' | 'success' | 'warning' }> = {
  law:            { label: '法律法规', labelEn: 'Law',     tone: 'normal' },
  regulation:     { label: '部门规章', labelEn: 'Reg',     tone: 'normal' },
  case:           { label: '司法判例', labelEn: 'Case',    tone: 'success' },
  case_law:       { label: '判例',     labelEn: 'Case',    tone: 'success' },
  interpretation: { label: '司法解释', labelEn: 'Interp',  tone: 'normal' },
  template:       { label: '合同模板', labelEn: 'Tpl',     tone: 'warning' },
  article:        { label: '法律文章', labelEn: 'Article', tone: 'normal' },
  internal:       { label: '内部知识', labelEn: 'Intern',  tone: 'normal' },
  other:          { label: '其他',     labelEn: 'Other',   tone: 'normal' },
  general:        { label: '通用',     labelEn: 'General', tone: 'normal' },
}

const kbTypeOptions = [
  { value: '',          label: '全部类型' },
  { value: 'general',    label: '通用' },
  { value: 'regulation', label: '法规' },
  { value: 'case_law',   label: '判例' },
  { value: 'template',   label: '模板' },
  { value: 'internal',   label: '内部知识' },
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

// =============== 通用 UI ===============
const inputBase = 'w-full bg-card border border-border px-3 py-2 text-[14px] text-foreground placeholder:text-muted-foreground/70 transition-colors focus:outline-none focus:border-primary'

function ToneTag({ tone, labelEn, label }: { tone: 'normal' | 'success' | 'warning' | 'error'; labelEn: string; label: string }) {
  const toneClass = {
    normal:  'text-muted-foreground',
    success: 'text-success',
    warning: 'text-warning',
    error:   'text-destructive',
  }[tone]
  return (
    <span className={cn('inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em]', toneClass)}>
      <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
      <span>{labelEn}</span>
      <span className="text-foreground/30" aria-hidden>·</span>
      <span className="normal-case tracking-normal text-foreground/80">{label}</span>
    </span>
  )
}

function Overlay({ open, onClose, tracker, title, wide, children }: {
  open: boolean
  onClose: () => void
  tracker: string
  title: string
  wide?: boolean
  children: React.ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-foreground/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className={cn(
          'bg-background border border-border flex flex-col max-h-[85vh]',
          wide ? 'w-full max-w-3xl' : 'w-full max-w-lg',
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between px-6 py-5 border-b border-border shrink-0">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              {tracker}
            </div>
            <h2 className="font-serif text-[20px] mt-1">{title}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
            title="关闭"
          >
            <X className="w-5 h-5 stroke-[1.5]" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
      </div>
    </div>
  )
}

// =============== 主组件 ===============
export default function KnowledgeBase() {
  const [viewMode, setViewMode] = useState<'manage' | 'search'>('manage')
  const [bases, setBases] = useState<KB[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('')

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

  const [showCreate, setShowCreate] = useState(false)
  const [editingBase, setEditingBase] = useState<KB | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [previewDoc, setPreviewDoc] = useState<DocDetail | null>(null)
  const [editingDoc, setEditingDoc] = useState<DocDetail | null>(null)
  const [deletingBase, setDeletingBase] = useState<KB | null>(null)

  const [baseForm, setBaseForm] = useState({ name: '', description: '', knowledge_type: 'general', is_public: false })
  const [docEditForm, setDocEditForm] = useState({ title: '', content: '', source: '', tags: '', law_category: '', effective_date: '', issuing_authority: '' })

  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const batchInputRef = useRef<HTMLInputElement>(null)

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
      setDocuments((prev) => append ? [...prev, ...items] : items)
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
    try { setStats(await knowledgeApi.getBaseStats(kbId)) }
    catch { setStats(null) }
  }, [])

  useEffect(() => { void loadBases() }, [loadBases])

  useEffect(() => {
    if (selectedBase) {
      void loadDocuments(selectedBase.id)
      void loadStats(selectedBase.id)
    }
  }, [selectedBase, loadDocuments, loadStats])

  // ===== CRUD =====
  const handleCreateBase = async () => {
    if (!baseForm.name.trim()) { toast.error('请输入知识库名称'); return }
    try {
      await knowledgeApi.createBase(baseForm)
      toast.success('知识库创建成功')
      setShowCreate(false)
      setBaseForm({ name: '', description: '', knowledge_type: 'general', is_public: false })
      void loadBases()
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
      void loadBases()
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
      void loadBases()
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

  // ===== 文档操作 =====
  const handlePreviewDoc = async (doc: KnowledgeDocument) => {
    try {
      setPreviewDoc(await knowledgeApi.getDocument(doc.id))
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
        tags: docEditForm.tags.split(',').map((t) => t.trim()).filter(Boolean),
        law_category: docEditForm.law_category || undefined,
        effective_date: docEditForm.effective_date || undefined,
        issuing_authority: docEditForm.issuing_authority || undefined,
      })
      toast.success('文档更新成功')
      setEditingDoc(null)
      if (selectedBase) void loadDocuments(selectedBase.id)
    } catch (err: any) {
      toast.error('更新失败: ' + (err.message || '未知错误'))
    }
  }

  const handleDeleteDoc = async (docId: string) => {
    try {
      await knowledgeApi.deleteDocument(docId)
      toast.success('文档已删除')
      if (selectedBase) void loadDocuments(selectedBase.id)
    } catch (err: any) {
      toast.error('删除失败: ' + (err.message || '未知错误'))
    }
  }

  // ===== 上传 =====
  const handleSingleUpload = async (file: File) => {
    if (!selectedBase) return
    setUploading(true)
    try {
      await knowledgeApi.uploadDocument(selectedBase.id, file)
      toast.success(`"${file.name}" 上传成功`)
      void loadDocuments(selectedBase.id)
    } catch (err: any) {
      toast.error('上传失败: ' + (err.message || '未知错误'))
    } finally { setUploading(false) }
  }

  const handleBatchUpload = async (files: FileList | File[]) => {
    if (!selectedBase) return
    const fileArr = Array.from(files)
    if (fileArr.length === 0) return
    setUploading(true)
    try {
      await knowledgeApi.batchUpload(selectedBase.id, fileArr)
      toast.success(`${fileArr.length} 个文件上传成功`)
      void loadDocuments(selectedBase.id)
      setShowUpload(false)
    } catch (err: any) {
      toast.error('批量上传失败: ' + (err.message || '未知错误'))
    } finally { setUploading(false) }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files.length > 0) handleBatchUpload(e.dataTransfer.files)
  }

  // ===== 过滤 =====
  const filteredBases = useMemo(() => {
    if (!searchQuery) return bases
    const q = searchQuery.toLowerCase()
    return bases.filter((kb) =>
      kb.name.toLowerCase().includes(q) ||
      (kb.description || '').toLowerCase().includes(q),
    )
  }, [bases, searchQuery])

  const filteredDocs = useMemo(() => {
    if (!docSearch) return documents
    const q = docSearch.toLowerCase()
    return documents.filter((doc) =>
      doc.title.toLowerCase().includes(q) ||
      (doc.source || '').toLowerCase().includes(q) ||
      (doc.tags || []).some((t) => t.toLowerCase().includes(q)),
    )
  }, [documents, docSearch])

  // ===== 弹窗 =====
  const renderCreateEditModal = () => {
    const isEdit = !!editingBase
    const open = showCreate || !!editingBase
    return (
      <Overlay
        open={open}
        onClose={() => { setShowCreate(false); setEditingBase(null) }}
        tracker={isEdit ? 'Knowledge · Edit' : 'Knowledge · New'}
        title={isEdit ? '编辑知识库' : '新建知识库'}
      >
        <div className="space-y-5">
          <Field label="Name · 知识库名称 *">
            <input
              type="text"
              value={baseForm.name}
              onChange={(e) => setBaseForm({ ...baseForm, name: e.target.value })}
              placeholder="例如：公司法规库"
              className={inputBase}
            />
          </Field>
          <Field label="Description · 描述">
            <textarea
              value={baseForm.description}
              onChange={(e) => setBaseForm({ ...baseForm, description: e.target.value })}
              placeholder="简要描述知识库的内容和用途"
              rows={3}
              className={cn(inputBase, 'resize-none')}
            />
          </Field>
          <Field label="Type · 类型">
            <select
              value={baseForm.knowledge_type}
              onChange={(e) => setBaseForm({ ...baseForm, knowledge_type: e.target.value })}
              className={inputBase}
            >
              {kbTypeOptions.filter((o) => o.value).map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </Field>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="kb-public"
              checked={baseForm.is_public}
              onChange={(e) => setBaseForm({ ...baseForm, is_public: e.target.checked })}
              className="border-border"
            />
            <label htmlFor="kb-public" className="text-[13px] text-foreground">公开知识库</label>
          </div>
          <div className="flex gap-3 justify-end pt-4 border-t border-border">
            <button
              type="button"
              onClick={() => { setShowCreate(false); setEditingBase(null) }}
              className="border border-border bg-card hover:bg-surface-2 px-5 py-2 text-[13px] text-foreground transition-colors"
            >
              取消
            </button>
            <button
              type="button"
              onClick={isEdit ? handleEditBase : handleCreateBase}
              className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              {isEdit ? '保存' : '创建'}
            </button>
          </div>
        </div>
      </Overlay>
    )
  }

  const renderDeleteConfirm = () => (
    <Overlay
      open={!!deletingBase}
      onClose={() => setDeletingBase(null)}
      tracker="Knowledge · Delete"
      title="确认删除"
    >
      <div className="space-y-5">
        <aside className="border-l-2 border-destructive/60 pl-4 py-1">
          <div className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-destructive mb-1">
            <AlertCircle className="w-3 h-3 stroke-[1.5]" />
            <span>Warning</span>
          </div>
          <p className="text-[13px] text-foreground/80 leading-relaxed">
            确定要删除知识库 <strong className="text-foreground">{deletingBase?.name}</strong> 吗？此操作不可撤销，所有关联文档将一并删除。
          </p>
        </aside>
        <div className="flex gap-3 justify-end pt-4 border-t border-border">
          <button
            type="button"
            onClick={() => setDeletingBase(null)}
            className="border border-border bg-card hover:bg-surface-2 px-5 py-2 text-[13px] text-foreground transition-colors"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleDeleteBase}
            className="bg-destructive hover:bg-destructive/90 text-destructive-foreground px-5 py-2 text-[13px] font-medium transition-colors"
          >
            确认删除
          </button>
        </div>
      </div>
    </Overlay>
  )

  const renderUploadModal = () => (
    <Overlay
      open={showUpload}
      onClose={() => setShowUpload(false)}
      tracker="Knowledge · Upload"
      title="上传文档"
    >
      <div className="space-y-5">
        <div
          className={cn(
            'border border-dashed p-10 text-center transition-colors',
            dragOver ? 'border-primary bg-surface-2/50' : 'border-border',
          )}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <Upload className="w-10 h-10 stroke-[1] text-muted-foreground mx-auto mb-4" />
          <p className="font-serif text-[18px] text-foreground mb-1">拖拽文件到此处上传</p>
          <p className="text-[12px] text-muted-foreground mb-5">支持 PDF、Word、TXT、Markdown 等格式</p>
          <div className="flex gap-3 justify-center">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 disabled:opacity-50 text-primary-foreground px-4 py-2 text-[13px] font-medium transition-colors"
            >
              <Upload className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>选择单个文件</span>
            </button>
            <button
              type="button"
              onClick={() => batchInputRef.current?.click()}
              disabled={uploading}
              className="inline-flex items-center gap-1.5 border border-border bg-card hover:bg-surface-2 disabled:opacity-50 px-4 py-2 text-[13px] text-foreground transition-colors"
            >
              <Layers className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>批量选择</span>
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) handleSingleUpload(e.target.files[0])
              e.target.value = ''
            }}
          />
          <input
            ref={batchInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) handleBatchUpload(e.target.files)
              e.target.value = ''
            }}
          />
        </div>
        {uploading && (
          <div className="inline-flex items-center gap-2 text-[12px] uppercase tracking-[0.12em] text-primary">
            <Loader2 className="w-3.5 h-3.5 stroke-[1.5] animate-spin" />
            <span>正在上传…</span>
          </div>
        )}
      </div>
    </Overlay>
  )

  const renderDocPreview = () => (
    <Overlay
      open={!!previewDoc}
      onClose={() => setPreviewDoc(null)}
      tracker="Knowledge · Document"
      title="文档详情"
      wide
    >
      {previewDoc && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-px bg-border border-t border-l border-border">
            <MetaCell label="Source · 来源" value={previewDoc.source || '未知'} />
            <MetaCell
              label="Status · 状态"
              valueNode={
                <ToneTag
                  tone={previewDoc.is_processed ? 'success' : 'warning'}
                  labelEn={previewDoc.is_processed ? 'Indexed' : 'Processing'}
                  label={previewDoc.is_processed ? '已索引' : '处理中'}
                />
              }
            />
            {previewDoc.law_category && <MetaCell label="Category · 法律分类" value={previewDoc.law_category} />}
            {previewDoc.issuing_authority && <MetaCell label="Issuer · 发布机构" value={previewDoc.issuing_authority} />}
            {previewDoc.effective_date && <MetaCell label="Effective · 生效日期" value={previewDoc.effective_date} />}
            {previewDoc.chunk_count != null && <MetaCell label="Chunks · 向量分块" value={`${previewDoc.chunk_count} 块`} />}
          </div>

          {previewDoc.tags && previewDoc.tags.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                Tags
              </span>
              {previewDoc.tags.map((tag) => (
                <span key={tag} className="text-[12px] text-foreground/80 border border-border px-2 py-0.5">{tag}</span>
              ))}
            </div>
          )}

          {previewDoc.summary && (
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
                Summary · 摘要
              </div>
              <p className="text-[14px] text-foreground/85 leading-relaxed">{previewDoc.summary}</p>
            </div>
          )}

          {previewDoc.content && (
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
                Content · 正文
              </div>
              <div className="bg-surface-2/40 border border-border p-4 max-h-80 overflow-y-auto">
                <pre className="text-[13px] text-foreground whitespace-pre-wrap font-sans leading-relaxed">{previewDoc.content}</pre>
              </div>
            </div>
          )}

          <div className="flex gap-3 justify-end pt-4 border-t border-border">
            <button
              type="button"
              onClick={() => setPreviewDoc(null)}
              className="border border-border bg-card hover:bg-surface-2 px-5 py-2 text-[13px] text-foreground transition-colors"
            >
              关闭
            </button>
            <button
              type="button"
              onClick={() => openDocEdit(previewDoc)}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>编辑</span>
            </button>
          </div>
        </div>
      )}
    </Overlay>
  )

  const renderDocEdit = () => (
    <Overlay
      open={!!editingDoc}
      onClose={() => setEditingDoc(null)}
      tracker="Knowledge · Edit Document"
      title="编辑文档"
      wide
    >
      <div className="space-y-5">
        <Field label="Title · 标题">
          <input
            type="text"
            value={docEditForm.title}
            onChange={(e) => setDocEditForm({ ...docEditForm, title: e.target.value })}
            className={inputBase}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Source · 来源">
            <input
              type="text"
              value={docEditForm.source}
              onChange={(e) => setDocEditForm({ ...docEditForm, source: e.target.value })}
              className={inputBase}
            />
          </Field>
          <Field label="Tags · 标签（逗号分隔）">
            <input
              type="text"
              value={docEditForm.tags}
              onChange={(e) => setDocEditForm({ ...docEditForm, tags: e.target.value })}
              placeholder="民法, 总则"
              className={inputBase}
            />
          </Field>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Field label="Category · 法律分类">
            <input
              type="text"
              value={docEditForm.law_category}
              onChange={(e) => setDocEditForm({ ...docEditForm, law_category: e.target.value })}
              placeholder="民法"
              className={inputBase}
            />
          </Field>
          <Field label="Effective · 生效日期">
            <input
              type="date"
              value={docEditForm.effective_date}
              onChange={(e) => setDocEditForm({ ...docEditForm, effective_date: e.target.value })}
              className={inputBase}
            />
          </Field>
          <Field label="Issuer · 发布机构">
            <input
              type="text"
              value={docEditForm.issuing_authority}
              onChange={(e) => setDocEditForm({ ...docEditForm, issuing_authority: e.target.value })}
              className={inputBase}
            />
          </Field>
        </div>
        <Field label="Content · 内容">
          <textarea
            value={docEditForm.content}
            onChange={(e) => setDocEditForm({ ...docEditForm, content: e.target.value })}
            rows={12}
            className={cn(inputBase, 'resize-none font-mono text-[12px]')}
          />
        </Field>
        <div className="flex gap-3 justify-end pt-4 border-t border-border">
          <button
            type="button"
            onClick={() => setEditingDoc(null)}
            className="border border-border bg-card hover:bg-surface-2 px-5 py-2 text-[13px] text-foreground transition-colors"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleSaveDoc}
            className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
          >
            保存更改
          </button>
        </div>
      </div>
    </Overlay>
  )

  const renderStatsPanel = () => {
    if (!showStats || !stats) return null
    const categories = Object.entries(stats.categories || {})
    return (
      <section className="mb-8 border border-border bg-card">
        <header className="flex items-center justify-between px-5 py-3 border-b border-border">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Statistics · 知识库统计
          </div>
          <button
            type="button"
            onClick={() => setShowStats(false)}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4 stroke-[1.5]" />
          </button>
        </header>
        <div className="grid grid-cols-3 gap-px bg-border">
          <StatsCell tracker="Docs"      label="文档总数"  value={stats.doc_count} />
          <StatsCell tracker="Indexed"   label="已索引"    value={stats.processed_count} tone="success" />
          <StatsCell tracker="Chunks"    label="向量分块"  value={stats.total_chunks}   tone="primary" />
        </div>
        {categories.length > 0 && (
          <div className="px-5 py-4 border-t border-border">
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-3">
              Categories · 分类分布
            </div>
            <div className="space-y-2">
              {categories.map(([cat, count]) => {
                const pct = stats.doc_count > 0 ? Math.round((count / stats.doc_count) * 100) : 0
                return (
                  <div key={cat} className="flex items-center gap-3">
                    <span className="text-[12px] text-foreground w-20 shrink-0 truncate">{cat}</span>
                    <div className="flex-1 h-px bg-border relative">
                      <div
                        className="absolute top-0 left-0 h-px bg-primary transition-[width]"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-[11px] text-muted-foreground tabular-nums w-16 text-right">
                      {count} ({pct}%)
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </section>
    )
  }

  // ===== 详情视图 =====
  if (selectedBase) {
    const typeMeta = kbTypeMeta[selectedBase.knowledge_type || 'general'] || kbTypeMeta.general
    return (
      <div className="h-full flex flex-col bg-background">
        <header className="shrink-0 px-6 sm:px-8 lg:px-12 xl:px-16 pt-8 pb-4 border-b border-border">
          <div className="flex items-center gap-3 mb-3">
            <button
              type="button"
              onClick={() => { setSelectedBase(null); setDocuments([]); setStats(null); setShowStats(false) }}
              className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
              title="返回"
            >
              <ArrowLeft className="w-5 h-5 stroke-[1.5]" />
            </button>
            <div className="flex-1 min-w-0">
              <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-1">
                Knowledge
                <span className="text-foreground/30 mx-1.5" aria-hidden>·</span>
                <span className="text-foreground/70 normal-case tracking-normal">司法智库</span>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="font-serif text-[28px] leading-tight text-foreground truncate">{selectedBase.name}</h1>
                <ToneTag tone={typeMeta.tone} labelEn={typeMeta.labelEn} label={typeMeta.label} />
                {selectedBase.is_public && (
                  <span className="inline-flex items-center gap-1 text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                    <Globe className="w-3 h-3 stroke-[1.5]" />
                    Public
                  </span>
                )}
              </div>
              {selectedBase.description && (
                <p className="text-[13px] text-muted-foreground mt-1 hidden sm:block">{selectedBase.description}</p>
              )}
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <IconBtn title="统计" onClick={() => setShowStats(!showStats)} icon={BarChart3} />
              <IconBtn title="编辑" onClick={() => { setBaseForm({ name: selectedBase.name, description: selectedBase.description || '', knowledge_type: selectedBase.knowledge_type || 'general', is_public: selectedBase.is_public || false }); setEditingBase(selectedBase) }} icon={Edit2} />
              <IconBtn title="导出" onClick={handleExport} icon={Download} />
              <IconBtn title="删除" onClick={() => setDeletingBase(selectedBase)} icon={Trash2} tone="destructive" />
            </div>
          </div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 stroke-[1.5] absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={docSearch}
                onChange={(e) => setDocSearch(e.target.value)}
                placeholder="搜索文档标题、来源、标签…"
                className={cn(inputBase, 'pl-10')}
              />
            </div>
            <button
              type="button"
              onClick={() => setShowUpload(true)}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors whitespace-nowrap"
            >
              <Upload className="w-4 h-4 stroke-[1.5]" />
              <span>上传文档</span>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-6">
          {renderStatsPanel()}

          {docLoading ? (
            <div className="text-center py-16">
              <Loader2 className="w-6 h-6 stroke-[1.5] animate-spin text-muted-foreground mx-auto" />
            </div>
          ) : filteredDocs.length === 0 ? (
            <EmptyBlock
              tracker="Documents · 空状态"
              title={docSearch ? '没有找到匹配的文档' : '暂无文档'}
              description={docSearch ? '尝试修改搜索关键词。' : '上传文件开始构建知识库。'}
              action={!docSearch && (
                <button
                  type="button"
                  onClick={() => setShowUpload(true)}
                  className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
                >
                  上传文档
                </button>
              )}
            />
          ) : (
            <>
              <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mb-4">
                显示 {filteredDocs.length} / {docTotal} 篇文档
                {docSearch && ` · 搜索 “${docSearch}”`}
              </p>
              <ol className="space-y-px">
                {filteredDocs.map((doc, i) => (
                  <li key={doc.id} className="group border-b border-border/60">
                    <button
                      type="button"
                      onClick={() => void handlePreviewDoc(doc)}
                      className="w-full text-left flex items-start gap-6 py-5 px-3 -mx-3 transition-colors hover:bg-surface-2/40"
                    >
                      <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 pt-1 tabular-nums">
                        {String(i + 1).padStart(3, '0')}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                          <ToneTag
                            tone={doc.is_processed ? 'success' : 'warning'}
                            labelEn={doc.is_processed ? 'Indexed' : 'Processing'}
                            label={doc.is_processed ? '已索引' : '处理中'}
                          />
                        </div>
                        <h3 className="font-serif text-[16px] leading-tight text-foreground inline-flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5 stroke-[1.5] text-muted-foreground" />
                          {doc.title}
                        </h3>
                        {doc.summary && (
                          <p className="text-[13px] text-muted-foreground line-clamp-2 mt-1 leading-relaxed">{doc.summary}</p>
                        )}
                        <div className="flex items-center gap-3 text-[12px] text-muted-foreground mt-2 flex-wrap">
                          {doc.source && (
                            <span className="inline-flex items-center gap-1">
                              <Link2 className="w-3 h-3 stroke-[1.5]" /> {doc.source}
                            </span>
                          )}
                          {doc.created_at && (
                            <span className="inline-flex items-center gap-1 tabular-nums">
                              <Calendar className="w-3 h-3 stroke-[1.5]" /> {doc.created_at.slice(0, 10)}
                            </span>
                          )}
                          {doc.tags?.map((tag) => (
                            <span key={tag} className="text-foreground/60">· {tag}</span>
                          ))}
                        </div>
                      </div>
                      <div
                        role="group"
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => e.stopPropagation()}
                        className="hidden group-hover:flex items-center gap-1 shrink-0 pt-1"
                      >
                        <IconBtn
                          title="编辑"
                          onClick={async () => {
                            const detail = await knowledgeApi.getDocument(doc.id)
                            openDocEdit(detail)
                          }}
                          icon={Edit2}
                        />
                        <IconBtn
                          title="删除"
                          onClick={() => handleDeleteDoc(doc.id)}
                          icon={Trash2}
                          tone="destructive"
                        />
                      </div>
                    </button>
                  </li>
                ))}
              </ol>
              {!docSearch && documents.length < docTotal && (
                <div className="flex justify-center pt-6">
                  <button
                    type="button"
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="text-[12px] uppercase tracking-[0.12em] text-primary hover:text-primary-700 disabled:opacity-50 transition-colors"
                  >
                    {loadingMore
                      ? <><Loader2 className="w-3.5 h-3.5 stroke-[1.5] animate-spin inline mr-1" />加载中…</>
                      : <>加载更多 ({documents.length}/{docTotal}) →</>}
                  </button>
                </div>
              )}
            </>
          )}
        </main>

        {renderCreateEditModal()}
        {renderDeleteConfirm()}
        {renderUploadModal()}
        {renderDocPreview()}
        {renderDocEdit()}
      </div>
    )
  }

  // ===== 列表视图 =====
  return (
    <div className="min-h-screen flex flex-col">
      <div className="max-w-7xl w-full mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-10">
        <EditorialPageHeader
          tracker={['Knowledge', '司法智库']}
          title="司法智库"
          description="知识库管理 · 法律文档全文检索 · AI 向量索引。"
          actions={viewMode === 'manage' ? (
            <button
              type="button"
              onClick={() => { setBaseForm({ name: '', description: '', knowledge_type: 'general', is_public: false }); setShowCreate(true) }}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              <Plus className="w-4 h-4 stroke-[1.5]" />
              <span>新建知识库</span>
            </button>
          ) : undefined}
        />

        {/* viewMode 切换 */}
        <nav className="flex items-end gap-8 border-b border-border mb-8" role="tablist" aria-label="视图模式">
          {[
            { key: 'manage' as const, labelEn: 'Manage', label: '知识库管理', icon: Database },
            { key: 'search' as const, labelEn: 'Search', label: '智慧搜索',   icon: Search },
          ].map((item) => {
            const active = viewMode === item.key
            const Icon = item.icon
            return (
              <button
                key={item.key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setViewMode(item.key)}
                className={cn(
                  'relative py-3 inline-flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.16em] transition-colors',
                  active
                    ? 'text-foreground after:absolute after:left-0 after:right-0 after:bottom-0 after:h-px after:bg-primary'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="w-3.5 h-3.5 stroke-[1.5]" />
                <span>{item.labelEn}</span>
                <span className="text-foreground/30" aria-hidden>·</span>
                <span className="normal-case tracking-normal">{item.label}</span>
              </button>
            )
          })}
        </nav>

        {viewMode === 'search' ? (
          <div className="min-h-[720px] border border-border bg-background">
            <SmartSearch />
          </div>
        ) : (
          <>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-8">
              <div className="relative flex-1 max-w-md">
                <Search className="w-4 h-4 stroke-[1.5] absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索知识库名称或描述…"
                  className={cn(inputBase, 'pl-10')}
                />
              </div>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className={cn(inputBase, 'sm:w-48')}
              >
                {kbTypeOptions.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {loading ? (
              <div className="text-center py-16">
                <Loader2 className="w-6 h-6 stroke-[1.5] animate-spin text-muted-foreground mx-auto" />
              </div>
            ) : filteredBases.length === 0 ? (
              <EmptyBlock
                tracker="Knowledge · 空状态"
                title={searchQuery || filterType ? '没有找到匹配的知识库' : '暂无知识库'}
                description={searchQuery || filterType ? '尝试修改搜索条件。' : '创建第一个知识库开始管理法律知识。'}
                action={!searchQuery && !filterType && (
                  <button
                    type="button"
                    onClick={() => { setBaseForm({ name: '', description: '', knowledge_type: 'general', is_public: false }); setShowCreate(true) }}
                    className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
                  >
                    新建知识库
                  </button>
                )}
              />
            ) : (
              <>
                {/* KPI grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border border-t border-l border-border mb-8">
                  <StatsCell tracker="Bases"   label="知识库" value={filteredBases.length} icon={BookOpen} />
                  <StatsCell tracker="Docs"    label="总文档" value={filteredBases.reduce((sum, kb) => sum + (((kb as any).document_count) || kb.doc_count || 0), 0)} icon={FileText} tone="success" />
                  <StatsCell tracker="Types"   label="类型"   value={new Set(filteredBases.map((kb) => kb.knowledge_type)).size} icon={Tag} tone="warning" />
                  <StatsCell tracker="Public"  label="公开"   value={filteredBases.filter((kb) => kb.is_public).length} icon={Globe} />
                </div>

                <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mb-4">
                  共 {filteredBases.length} 个知识库
                  {searchQuery && ` · 搜索 “${searchQuery}”`}
                  {filterType && ` · 类型 ${kbTypeMeta[filterType]?.label || filterType}`}
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-border border-t border-l border-border">
                  {filteredBases.map((kb) => {
                    const typeMeta = kbTypeMeta[kb.knowledge_type || 'general'] || kbTypeMeta.general
                    return (
                      <article
                        key={kb.id}
                        onClick={() => setSelectedBase(kb)}
                        className="group relative bg-card border-r border-b border-border p-5 cursor-pointer transition-colors hover:bg-surface-2/40"
                      >
                        <div
                          role="group"
                          onClick={(e) => e.stopPropagation()}
                          onKeyDown={(e) => e.stopPropagation()}
                          className="absolute top-3 right-3 hidden group-hover:flex items-center gap-1 z-10"
                        >
                          <IconBtn
                            title="编辑"
                            onClick={() => {
                              setBaseForm({ name: kb.name, description: kb.description || '', knowledge_type: kb.knowledge_type || 'general', is_public: kb.is_public || false })
                              setEditingBase(kb)
                            }}
                            icon={Edit2}
                            size="sm"
                          />
                          <IconBtn
                            title="删除"
                            onClick={() => setDeletingBase(kb)}
                            icon={Trash2}
                            tone="destructive"
                            size="sm"
                          />
                        </div>

                        <header className="flex items-start justify-between mb-4">
                          <BookOpen className="w-5 h-5 stroke-[1.5] text-primary" />
                          <ToneTag tone={typeMeta.tone} labelEn={typeMeta.labelEn} label={typeMeta.label} />
                        </header>
                        <h3 className="font-serif text-[18px] leading-tight text-foreground mb-1">{kb.name}</h3>
                        <p className="text-[13px] text-muted-foreground line-clamp-2 leading-relaxed mb-4 min-h-[2.6em]">
                          {kb.description || '暂无描述'}
                        </p>
                        <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.12em] text-muted-foreground border-t border-border/60 pt-3">
                          <span className="inline-flex items-center gap-1">
                            <FileText className="w-3 h-3 stroke-[1.5]" />
                            {((kb as any).document_count) || kb.doc_count || 0} 篇
                          </span>
                          <span className="inline-flex items-center gap-1">
                            {kb.is_public ? <><Globe className="w-3 h-3 stroke-[1.5]" /> Public</> : <><Lock className="w-3 h-3 stroke-[1.5]" /> Private</>}
                          </span>
                        </div>
                      </article>
                    )
                  })}
                </div>
              </>
            )}
          </>
        )}
      </div>

      {renderCreateEditModal()}
      {renderDeleteConfirm()}
    </div>
  )
}

// =============== 子组件 ===============
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
        {label}
      </label>
      {children}
    </div>
  )
}

function MetaCell({ label, value, valueNode }: { label: string; value?: string; valueNode?: React.ReactNode }) {
  return (
    <div className="bg-card border-r border-b border-border px-4 py-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <div className="text-[14px] text-foreground mt-1">{valueNode ?? value}</div>
    </div>
  )
}

function StatsCell({
  tracker, label, value, icon: Icon, tone = 'normal',
}: {
  tracker: string
  label: string
  value: number
  icon?: typeof BookOpen
  tone?: 'normal' | 'success' | 'warning' | 'primary'
}) {
  const toneClass = {
    normal:  'text-foreground',
    success: 'text-success',
    warning: 'text-warning',
    primary: 'text-primary',
  }[tone]
  return (
    <div className="bg-card border-r border-b border-border px-5 py-4">
      <div className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {Icon && <Icon className="w-3 h-3 stroke-[1.5]" />}
        <span>{tracker}</span>
        <span className="text-foreground/30" aria-hidden>·</span>
        <span className="normal-case tracking-normal text-foreground/70">{label}</span>
      </div>
      <div className={cn('font-serif text-[28px] leading-[1.1] mt-2 tabular-nums', toneClass)}>{value}</div>
    </div>
  )
}

function IconBtn({
  title, onClick, icon: Icon, tone = 'normal', size = 'md',
}: {
  title: string
  onClick: () => void
  icon: typeof Edit2
  tone?: 'normal' | 'destructive'
  size?: 'sm' | 'md'
}) {
  const sizeClass = size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'
  const toneClass = tone === 'destructive'
    ? 'text-muted-foreground hover:text-destructive'
    : 'text-muted-foreground hover:text-foreground'
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={cn('p-1.5 transition-colors', toneClass)}
    >
      <Icon className={cn(sizeClass, 'stroke-[1.5]')} />
    </button>
  )
}

function EmptyBlock({
  tracker, title, description, action,
}: {
  tracker: string
  title: string
  description: string
  action?: React.ReactNode
}) {
  return (
    <div className="text-center py-16">
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
        {tracker}
      </div>
      <h3 className="font-serif text-[22px] text-foreground mb-2">{title}</h3>
      <p className="text-[13px] text-muted-foreground max-w-md mx-auto mb-6">{description}</p>
      {action && <div>{action}</div>}
    </div>
  )
}
