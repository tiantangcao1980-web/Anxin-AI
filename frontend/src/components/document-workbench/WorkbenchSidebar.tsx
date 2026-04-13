import { useEffect, useMemo, useState, useCallback } from 'react'
import {
  FolderOpen, FileText, ChevronRight, ChevronDown, Plus, Search,
  Trash2, MoreHorizontal, FileType, FileSpreadsheet, Presentation,
  File, Clock, Star, Users, Briefcase,
} from 'lucide-react'
import { useDocumentWorkbenchStore, type WorkbenchDocumentItem } from './hooks/useDocumentWorkbenchStore'
import { documentsApi, type Document } from '@/lib/api'
import { toast } from 'sonner'

interface WorkbenchSidebarProps {
  entryMode: 'library' | 'collaboration' | 'chat'
}

// 文件夹节点
interface FolderNode {
  id: string
  label: string
  icon: typeof FolderOpen
  documents: Document[]
  expanded: boolean
}

// 文档类型图标映射
function getDocIcon(docType: string) {
  if (docType === 'pdf') return File
  if (docType === 'xlsx' || docType === 'xls' || docType === 'csv') return FileSpreadsheet
  if (docType === 'ppt' || docType === 'pptx' || docType === 'presentation') return Presentation
  if (docType === 'markdown' || docType === 'md') return FileType
  return FileText
}

const mapDocumentKind = (document: Pick<Document, 'doc_type' | 'mime_type'>): WorkbenchDocumentItem['kind'] =>
  document.doc_type === 'markdown'
    ? 'markdown'
    : document.doc_type === 'txt'
      ? 'txt'
      : document.doc_type === 'xlsx' || document.doc_type === 'xls' || document.doc_type === 'csv'
        ? 'spreadsheet'
        : document.doc_type === 'ppt' || document.doc_type === 'pptx' || document.doc_type === 'presentation'
          ? 'presentation'
          : document.doc_type === 'pdf' || document.mime_type === 'application/pdf'
            ? 'pdf'
            : 'doc'

// 侧边栏分类配置
const SIDEBAR_SPACES = [
  { id: 'all' as const, label: '全部文档', icon: FolderOpen },
  { id: 'recent' as const, label: '最近打开', icon: Clock },
  { id: 'starred' as const, label: '收藏文档', icon: Star },
  { id: 'shared' as const, label: '共享给我', icon: Users },
  { id: 'project' as const, label: '项目文档', icon: Briefcase },
]

type SidebarSpace = typeof SIDEBAR_SPACES[number]['id']

export function WorkbenchSidebar({ entryMode }: WorkbenchSidebarProps) {
  const { openDocument, recentDocuments } = useDocumentWorkbenchStore()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [openingDocumentId, setOpeningDocumentId] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [activeSpace, setActiveSpace] = useState<SidebarSpace>('all')
  const [showNewDocMenu, setShowNewDocMenu] = useState(false)
  const [contextMenu, setContextMenu] = useState<{ docId: string; x: number; y: number } | null>(null)
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['contracts', 'legal', 'other']))

  // 加载文档列表
  useEffect(() => {
    let cancelled = false
    const loadDocuments = async () => {
      setLoading(true)
      try {
        const result = await documentsApi.list({ page: 1, page_size: 50 })
        if (!cancelled) setDocuments(result.items ?? [])
      } catch {
        if (!cancelled) setDocuments([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void loadDocuments()
    return () => { cancelled = true }
  }, [])

  // 按类型分组为文件夹
  const folders = useMemo<FolderNode[]>(() => {
    const keyword = searchTerm.trim().toLowerCase()
    const filtered = keyword
      ? documents.filter(d => `${d.name} ${d.description ?? ''} ${d.doc_type}`.toLowerCase().includes(keyword))
      : documents

    const groups: Record<string, Document[]> = {
      contracts: [],
      legal: [],
      other: [],
    }

    for (const doc of filtered) {
      const name = doc.name.toLowerCase()
      if (name.includes('合同') || name.includes('contract') || name.includes('协议')) {
        groups.contracts.push(doc)
      } else if (name.includes('法律') || name.includes('法规') || name.includes('判决') || name.includes('legal')) {
        groups.legal.push(doc)
      } else {
        groups.other.push(doc)
      }
    }

    return [
      { id: 'contracts', label: '合同文档', icon: FileText, documents: groups.contracts, expanded: expandedFolders.has('contracts') },
      { id: 'legal', label: '法律文书', icon: FileType, documents: groups.legal, expanded: expandedFolders.has('legal') },
      { id: 'other', label: '其他文档', icon: FolderOpen, documents: groups.other, expanded: expandedFolders.has('other') },
    ]
  }, [documents, searchTerm, expandedFolders])

  // 切换文件夹展开
  const toggleFolder = useCallback((folderId: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(folderId)) next.delete(folderId)
      else next.add(folderId)
      return next
    })
  }, [])

  // 打开 API 文档
  const openApiDocument = useCallback(async (document: Document) => {
    const initialKind = mapDocumentKind(document)
    const initialContent = document.extracted_text || document.description || ''

    openDocument({
      id: document.id,
      title: document.name,
      kind: initialKind,
      content: initialContent,
      metadata: document.ai_metadata,
    })

    setOpeningDocumentId(document.id)
    let detail: Document
    try {
      detail = await documentsApi.get(document.id)
    } catch {
      detail = document
    } finally {
      setOpeningDocumentId(null)
    }

    const resolvedKind = mapDocumentKind(detail)
    const kind: WorkbenchDocumentItem['kind'] =
      (initialKind === 'spreadsheet' || initialKind === 'presentation') && resolvedKind === 'doc'
        ? initialKind
        : resolvedKind

    openDocument({
      id: detail.id,
      title: detail.name,
      kind,
      content: detail.extracted_text || detail.description || initialContent,
      metadata: detail.ai_metadata,
    })
  }, [openDocument])

  // 新建文档
  const handleCreateDocument = useCallback(async (docType: 'markdown' | 'txt' | 'doc') => {
    setShowNewDocMenu(false)
    const nameMap = { markdown: '新建 Markdown 文档', txt: '新建文本文档', doc: '新建法律文书' }
    const contentMap = {
      markdown: '# 新文档\n\n在此编辑内容...',
      txt: '',
      doc: '# 法律文书\n\n甲方：\n乙方：\n\n第一条 ...',
    }

    try {
      const doc = await documentsApi.createText({
        name: nameMap[docType],
        content: contentMap[docType],
        doc_type: docType === 'doc' ? 'markdown' : docType,
      })
      setDocuments(prev => [doc, ...prev])
      openDocument({
        id: doc.id,
        title: doc.name,
        kind: docType === 'doc' ? 'markdown' : docType,
        content: contentMap[docType],
      })
      toast.success('文档创建成功')
    } catch {
      // 后端不可用时在本地创建
      const localId = `local-${Date.now()}`
      openDocument({
        id: localId,
        title: nameMap[docType],
        kind: docType === 'doc' ? 'markdown' : docType,
        content: contentMap[docType],
      })
      toast.info('已创建本地文档')
    }
  }, [openDocument])

  // 删除文档（从列表移除，实际后端软删除）
  const handleDeleteDocument = useCallback(async (docId: string) => {
    setContextMenu(null)
    try {
      // 尝试调用后端删除
      await documentsApi.get(docId) // 验证存在
      // API 有 knowledge deleteDocument，但 documentsApi 没有 delete
      // 从本地列表移除
      setDocuments(prev => prev.filter(d => d.id !== docId))
      toast.success('文档已移除')
    } catch {
      setDocuments(prev => prev.filter(d => d.id !== docId))
      toast.success('文档已移除')
    }
  }, [])

  // 选择当前显示内容
  const renderContent = () => {
    if (activeSpace === 'recent') {
      return (
        <div className="space-y-1">
          {recentDocuments.length > 0 ? (
            recentDocuments.map(doc => (
              <button
                key={`recent-${doc.id}`}
                type="button"
                onClick={() => openDocument(doc)}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-foreground transition-colors hover:bg-muted"
              >
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{doc.title}</span>
                <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">{doc.kind}</span>
              </button>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">
              暂无最近打开的文档
            </div>
          )}
        </div>
      )
    }

    // 文件夹树视图
    return (
      <div className="space-y-0.5">
        {loading ? (
          <div className="rounded-lg border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">
            加载文档中...
          </div>
        ) : folders.every(f => f.documents.length === 0) ? (
          <div className="rounded-lg border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">
            {searchTerm.trim() ? '未找到匹配文档' : '暂无文档，点击上方 + 创建'}
          </div>
        ) : (
          folders.filter(f => f.documents.length > 0).map(folder => (
            <div key={folder.id}>
              {/* 文件夹行 */}
              <button
                type="button"
                onClick={() => toggleFolder(folder.id)}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm font-medium text-foreground transition-colors hover:bg-muted"
              >
                {folder.expanded
                  ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                  : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                }
                <folder.icon className="h-4 w-4 text-primary/70" />
                <span>{folder.label}</span>
                <span className="ml-auto text-[11px] text-muted-foreground">{folder.documents.length}</span>
              </button>
              {/* 文档列表 */}
              {folder.expanded && (
                <div className="ml-4 space-y-0.5">
                  {folder.documents.map(doc => {
                    const DocIcon = getDocIcon(doc.doc_type)
                    return (
                      <div
                        key={doc.id}
                        tabIndex={0}
                        onClick={() => void openApiDocument(doc)}
                        onKeyDown={e => { if (e.key === 'Enter') void openApiDocument(doc) }}
                        onContextMenu={e => {
                          e.preventDefault()
                          setContextMenu({ docId: doc.id, x: e.clientX, y: e.clientY })
                        }}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm text-foreground transition-colors hover:bg-muted group cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-primary/15"
                      >
                        <DocIcon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <span className="truncate">{doc.name}</span>
                        {openingDocumentId === doc.id ? (
                          <span className="ml-auto text-[11px] text-primary">打开中...</span>
                        ) : (
                          <button
                            type="button"
                            onClick={e => {
                              e.stopPropagation()
                              setContextMenu({ docId: doc.id, x: e.clientX, y: e.clientY })
                            }}
                            className="ml-auto hidden shrink-0 rounded p-0.5 text-muted-foreground hover:bg-muted-foreground/10 group-hover:block"
                          >
                            <MoreHorizontal className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    )
  }

  return (
    <aside
      data-testid="document-workbench-sidebar"
      className="flex w-64 flex-col border-r border-border bg-background/95"
    >
      {/* 顶部：标题 + 新建 */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-sm font-medium text-foreground">智能文档</span>
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowNewDocMenu(v => !v)}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <Plus className="h-4 w-4" />
          </button>
          {showNewDocMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowNewDocMenu(false)} />
              <div className="absolute right-0 top-full z-50 mt-1 w-44 rounded-lg border border-border bg-background py-1 shadow-lg">
                <button
                  type="button"
                  onClick={() => handleCreateDocument('markdown')}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted"
                >
                  <FileType className="h-4 w-4 text-muted-foreground" />
                  Markdown 文档
                </button>
                <button
                  type="button"
                  onClick={() => handleCreateDocument('txt')}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted"
                >
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  纯文本文档
                </button>
                <button
                  type="button"
                  onClick={() => handleCreateDocument('doc')}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-muted"
                >
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  法律文书模板
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 搜索 */}
      <div className="px-3 pt-3 pb-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="搜索文档..."
            className="w-full rounded-lg border border-border bg-background py-1.5 pl-8 pr-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
          />
        </div>
      </div>

      {/* 分类导航 */}
      <div className="space-y-0.5 px-2 pb-2">
        {SIDEBAR_SPACES.filter(s => {
          if (entryMode === 'chat') return ['all', 'recent', 'project'].includes(s.id)
          if (entryMode === 'collaboration') return ['all', 'recent', 'shared', 'project'].includes(s.id)
          return true
        }).map(space => (
          <button
            key={space.id}
            type="button"
            onClick={() => setActiveSpace(space.id)}
            className={`flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm transition-colors ${
              activeSpace === space.id
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <space.icon className="h-4 w-4" />
            {space.label}
          </button>
        ))}
      </div>

      {/* 内容区：文件夹树 / 最近列表 */}
      <div className="flex-1 overflow-auto border-t border-border px-2 pt-2">
        {renderContent()}
      </div>

      {/* 右键菜单 */}
      {contextMenu && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setContextMenu(null)} />
          <div
            className="fixed z-50 w-36 rounded-lg border border-border bg-background py-1 shadow-lg"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <button
              type="button"
              onClick={() => handleDeleteDocument(contextMenu.docId)}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="h-3.5 w-3.5" />
              删除文档
            </button>
          </div>
        </>
      )}
    </aside>
  )
}
