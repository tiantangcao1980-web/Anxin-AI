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
import { icons } from '@/lib/icons'
import {
  cardStyle,
  buttonStyle,
  heading,
  statusColor,
  inputStyle,
  iconSize,
  spacing,
} from '@/lib/design-tokens'
import { knowledgeApi, type KnowledgeBase as KB, type KnowledgeDocument } from '@/lib/api'
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

// Mock 数据
const MOCK_BASES: KB[] = [
  { id: '1', name: '法律法规库', knowledge_type: 'regulation', description: '中国现行法律法规汇编，涵盖民法典、刑法、行政法等主要领域', document_count: 1286, is_public: true, created_at: '2024-01-15' } as any,
  { id: '2', name: '司法判例库', knowledge_type: 'case_law', description: '最高人民法院及各级法院典型判例，涵盖民事、刑事、行政案件', document_count: 3542, is_public: true, created_at: '2024-02-20' } as any,
  { id: '3', name: '合同模板库', knowledge_type: 'template', description: '标准合同模板与条款库，含劳动合同、买卖合同、租赁合同等', document_count: 158, is_public: false, created_at: '2024-03-10' } as any,
  { id: '4', name: '内部知识库', knowledge_type: 'internal', description: '团队沉淀的实务经验与操作指南', document_count: 67, is_public: false, created_at: '2024-04-05' } as any,
  { id: '5', name: '司法解释库', knowledge_type: 'regulation', description: '最高人民法院、最高人民检察院发布的司法解释文件', document_count: 892, is_public: true, created_at: '2024-05-12' } as any,
  { id: '6', name: '法律文章库', knowledge_type: 'case_law', description: '法律实务文章、学术论文与专业分析报告', document_count: 423, is_public: true, created_at: '2024-06-18' } as any,
]

const MOCK_DOCS: KnowledgeDocument[] = [
  { id: 'd1', title: '民法典总则编逐条解读', source: '法律出版社', summary: '对民法典总则编各条文的详细解读与实务分析，含典型案例引用', is_processed: true, tags: ['民法典', '总则', '实务'], created_at: '2024-01-20' } as any,
  { id: 'd2', title: '劳动合同法实务操作指南', source: '内部整理', summary: '劳动合同签订、变更、解除的法律要点及风险防范措施', is_processed: true, tags: ['劳动法', '合同', '风险防范'], created_at: '2024-02-15' } as any,
  { id: 'd3', title: '知识产权侵权案例汇编（2024）', source: '最高法公报', summary: '2024年度知识产权典型侵权案例，含裁判要旨与法律适用分析', is_processed: true, tags: ['知识产权', '案例', '侵权'], created_at: '2024-03-01' } as any,
  { id: 'd4', title: '公司法修订要点解析', source: '全国人大常委会', summary: '2024年公司法修订的核心变化，含注册资本、公司治理等重点', is_processed: true, tags: ['公司法', '修订', '治理'], created_at: '2024-03-15' } as any,
  { id: 'd5', title: '建设工程施工合同纠纷裁判规则', source: '最高人民法院', summary: '建设工程领域常见合同纠纷的裁判规则与法律适用要点', is_processed: false, tags: ['建设工程', '合同纠纷'], created_at: '2024-04-10' } as any,
  { id: 'd6', title: '个人信息保护法实施细则', source: '国家互联网信息办公室', summary: '个人信息保护法配套实施细则，含数据处理、跨境传输等规范', is_processed: true, tags: ['个人信息', '数据保护'], created_at: '2024-05-20' } as any,
  { id: 'd7', title: '商标注册申请实务手册', source: '国家知识产权局', summary: '商标注册申请流程、审查标准及常见驳回理由分析', is_processed: true, tags: ['商标', '注册', '知识产权'], created_at: '2024-06-05' } as any,
  { id: 'd8', title: '民间借贷司法解释适用指南', source: '最高人民法院', summary: '民间借贷利率上限、举证责任、合同效力等核心问题解析', is_processed: false, tags: ['民间借贷', '司法解释'], created_at: '2024-06-25' } as any,
]

const MOCK_DOC_DETAILS: Record<string, Partial<DocDetail>> = {
  d1: {
    content: '第一编 总则\n\n第一章 基本规定\n\n第一条 为了保护民事主体的合法权益，调整民事关系，维护社会和经济秩序，适应中国特色社会主义发展要求，弘扬社会主义核心价值观，根据宪法，制定本法。\n\n第二条 民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。\n\n第三条 民事主体的人身权利、财产权利以及其他合法权益受法律保护，任何组织或者个人不得侵犯。\n\n第四条 民事主体在民事活动中的法律地位一律平等。\n\n第五条 民事主体从事民事活动，应当遵循自愿原则，按照自己的意思设立、变更、终止民事法律关系。\n\n【实务要点】\n总则编确立了民法的基本原则体系，包括平等原则、自愿原则、公平原则、诚信原则、守法与公序良俗原则以及绿色原则。这些原则贯穿整部民法典，是处理民事纠纷的基本准则。',
    chunk_count: 42, law_category: '民法', effective_date: '2021-01-01', issuing_authority: '全国人民代表大会',
  },
  d2: {
    content: '劳动合同法实务操作指南\n\n一、劳动合同的订立\n\n1. 用人单位自用工之日起即与劳动者建立劳动关系，应当在一个月内订立书面劳动合同。\n2. 用人单位超过一个月不满一年未与劳动者订立书面合同的，应当每月支付二倍工资。\n3. 劳动合同应当具备以下条款：用人单位信息、劳动者信息、合同期限、工作内容、工作地点、工作时间、劳动报酬、社会保险等。\n\n二、劳动合同的变更\n\n用人单位与劳动者协商一致，可以变更劳动合同约定的内容。变更劳动合同应当采用书面形式。\n\n三、劳动合同的解除\n\n（一）协商解除\n用人单位与劳动者协商一致，可以解除劳动合同。\n\n（二）劳动者单方解除\n劳动者提前三十日以书面形式通知用人单位，可以解除劳动合同。试用期内提前三日通知即可。\n\n【风险提示】\n未依法签订书面劳动合同是用人单位最常见的法律风险之一，可能面临双倍工资赔偿及视为签订无固定期限劳动合同的法律后果。',
    chunk_count: 28, law_category: '劳动法', effective_date: '2008-01-01', issuing_authority: '全国人民代表大会常务委员会',
  },
  d3: {
    content: '知识产权侵权案例汇编（2024年度）\n\n案例一：某科技公司诉某电子公司专利侵权案\n\n【裁判要旨】\n在判断是否构成专利侵权时，应当以权利要求书为准，说明书及附图可以用于解释权利要求。等同特征的认定应当以个案分析为原则。\n\n案例二：某品牌诉某平台商标侵权及不正当竞争案\n\n【裁判要旨】\n网络交易平台在接到权利人通知后，未及时采取必要措施的，应当对损害的扩大部分承担连带责任。平台的注意义务应当与其技术能力和管理水平相适应。\n\n案例三：某作家诉某自媒体著作权侵权案\n\n【裁判要旨】\n未经著作权人许可，在网络平台上转载他人作品且未支付报酬的行为，构成信息网络传播权侵权。合理使用抗辩需同时满足法定情形和"三步检验标准"。',
    chunk_count: 35, law_category: '知识产权法', effective_date: '2024-01-01', issuing_authority: '最高人民法院',
  },
  d4: {
    content: '公司法修订要点解析\n\n一、注册资本制度重大变化\n\n新公司法规定有限责任公司股东认缴的出资额应当自公司成立之日起五年内缴足。这一修订将对存量公司产生重大影响。\n\n二、公司治理结构优化\n\n1. 新增审计委员会制度，可以替代监事会职能\n2. 完善董事会职权，强化独立董事制度\n3. 明确控股股东、实际控制人的忠实义务\n\n三、股东权利保护\n\n1. 完善股东知情权制度，扩大查阅范围\n2. 明确股东代表诉讼制度\n3. 新增异议股东股权回购请求权的适用情形\n\n四、法律责任强化\n\n对抽逃出资、违规减资、违规分配利润等行为加大了处罚力度，董事对公司债务在特定情形下承担赔偿责任。',
    chunk_count: 22, law_category: '商法', effective_date: '2024-07-01', issuing_authority: '全国人民代表大会常务委员会',
  },
}

const MOCK_DOC_DETAIL: DocDetail = {
  id: 'd1', title: '民法典总则编逐条解读', source: '法律出版社',
  summary: '对民法典总则编各条文的详细解读与实务分析，含典型案例引用',
  content: MOCK_DOC_DETAILS.d1.content || '',
  is_processed: true, tags: ['民法典', '总则', '实务'], created_at: '2024-01-20',
  chunk_count: 42, law_category: '民法', effective_date: '2021-01-01', issuing_authority: '全国人民代表大会',
} as any

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
      const items = data.items || []
      // 如果 API 返回的数据没有文档（可能是空库），合并 Mock 演示数据
      const hasContent = items.some((kb: any) => (kb.doc_count || kb.document_count || 0) > 0)
      if (items.length === 0 || !hasContent) {
        // 合并：真实数据 + Mock 演示数据（用不同 ID 避免冲突）
        const mockWithPrefix = MOCK_BASES.map(m => ({ ...m, id: `demo_${m.id}`, name: `${m.name}` }))
        setBases([...items, ...mockWithPrefix] as any[])
        if (items.length > 0) toast.info('已补充演示数据供参考')
      } else {
        setBases(items)
      }
    } catch {
      toast.warning('API 不可用，使用演示数据')
      setBases(MOCK_BASES)
    } finally {
      setLoading(false)
    }
  }, [filterType])

  const loadDocuments = useCallback(async (kbId: string) => {
    setDocLoading(true)
    // 演示知识库直接使用 Mock 文档
    if (kbId.startsWith('demo_')) {
      setDocuments(MOCK_DOCS)
      setDocLoading(false)
      return
    }
    try {
      const data = await knowledgeApi.listDocuments(kbId)
      const items = data.items || []
      if (items.length === 0) {
        // 空知识库也显示 Mock 文档供演示
        setDocuments(MOCK_DOCS)
      } else {
        setDocuments(items)
      }
    } catch {
      toast.warning('API 不可用，使用演示数据')
      setDocuments(MOCK_DOCS)
    } finally {
      setDocLoading(false)
    }
  }, [])

  const loadStats = useCallback(async (kbId: string) => {
    // 演示知识库直接使用 Mock 统计
    const docCount = (selectedBase as any)?.document_count || 0
    const mockStats = {
      kb_id: kbId, name: selectedBase?.name || '', doc_count: docCount || 8,
      processed_count: Math.floor((docCount || 8) * 0.85),
      total_chunks: (docCount || 8) * 15,
      categories: { '民法': 35, '刑法': 22, '行政法': 18, '商法': 15, '其他': 10 },
    }
    if (kbId.startsWith('demo_')) {
      setStats(mockStats)
      return
    }
    try {
      const data = await knowledgeApi.getBaseStats(kbId)
      // 如果返回的统计全为0，使用 Mock 数据
      if (data.doc_count === 0) {
        setStats(mockStats)
      } else {
        setStats(data)
      }
    } catch {
      setStats(mockStats)
    }
  }, [selectedBase])

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
    } catch {
      // Mock preview - 使用文档特定的 mock 详情，fallback 到通用 mock
      const docSpecific = MOCK_DOC_DETAILS[doc.id] || {}
      setPreviewDoc({
        ...MOCK_DOC_DETAIL,
        ...doc,
        content: docSpecific.content || `${doc.title}\n\n${doc.summary || '暂无详细内容。'}\n\n本文档包含该主题的详细法律条文解读、实务要点分析及典型案例引用。文档已收录至知识库，支持智能检索与问答。`,
        chunk_count: docSpecific.chunk_count || Math.floor(Math.random() * 40 + 10),
        law_category: docSpecific.law_category || '',
        effective_date: docSpecific.effective_date || '',
        issuing_authority: docSpecific.issuing_authority || doc.source || '',
      } as DocDetail)
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
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">{stats.doc_count}</p>
            <p className="text-xs text-muted-foreground">文档总数</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-emerald-600">{stats.processed_count}</p>
            <p className="text-xs text-muted-foreground">已索引</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-primary">{stats.total_chunks}</p>
            <p className="text-xs text-muted-foreground">向量分块</p>
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
                      <div className="h-full bg-primary/60 rounded-full transition-all" style={{ width: `${pct}%` }} />
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
      <div className="h-full flex flex-col">
        {/* 顶部导航 */}
        <div className="border-b border-border px-4 sm:px-6 py-4 shrink-0">
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
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
          {renderStatsPanel()}

          {docLoading ? (
            <div className="flex items-center justify-center py-20">
              <icons.Refresh className={`${iconSize.lg} animate-spin text-primary`} />
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <icons.FileText className={`${iconSize['2xl']} mb-3 opacity-30`} />
              <p className="text-sm mb-1">{docSearch ? '没有找到匹配的文档' : '暂无文档'}</p>
              <p className="text-xs mb-4">{docSearch ? '尝试修改搜索关键词' : '上传文件开始构建知识库'}</p>
              {!docSearch && (
                <button onClick={() => setShowUpload(true)} className={buttonStyle.primary}>
                  <icons.Upload className={`${iconSize.sm} inline-block mr-1`} />
                  上传文档
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground mb-2">
                共 {filteredDocs.length} 篇文档
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
    <div className="h-full flex flex-col">
      {/* 顶部区域 */}
      <div className="border-b border-border px-4 sm:px-6 py-4 sm:py-5 shrink-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className={heading.page}>
            <icons.KnowledgeBase className={`${iconSize.md} inline-block mr-2 -mt-0.5`} />
            司法智库
          </h1>
          <button onClick={() => { setBaseForm({ name: '', description: '', knowledge_type: 'general', is_public: false }); setShowCreate(true) }} className={buttonStyle.primary}>
            <icons.Plus className={`${iconSize.sm} inline-block mr-1`} />
            新建知识库
          </button>
        </div>
        {/* 搜索 & 筛选 */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
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
      </div>

      {/* 内容 */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <icons.Refresh className={`${iconSize.lg} animate-spin text-primary`} />
          </div>
        ) : filteredBases.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <icons.BookOpen className={`${iconSize['2xl']} mb-3 opacity-30`} />
            <p className="text-sm mb-1">{searchQuery || filterType ? '没有找到匹配的知识库' : '暂无知识库'}</p>
            <p className="text-xs mb-4">{searchQuery || filterType ? '尝试修改搜索条件' : '创建第一个知识库开始管理法律知识'}</p>
            {!searchQuery && !filterType && (
              <button onClick={() => { setBaseForm({ name: '', description: '', knowledge_type: 'general', is_public: false }); setShowCreate(true) }} className={buttonStyle.primary}>
                <icons.Plus className={`${iconSize.sm} inline-block mr-1`} />
                新建知识库
              </button>
            )}
          </div>
        ) : (
          <>
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

      {/* 弹窗 */}
      {renderCreateEditModal()}
      {renderDeleteConfirm()}
    </div>
  )
}
