import { useEffect, useMemo, useState } from 'react'
import { useDocumentWorkbenchStore, type WorkbenchDocumentItem } from './hooks/useDocumentWorkbenchStore'
import { documentsApi, type Document } from '@/lib/api'

interface WorkbenchSidebarProps {
  entryMode: 'library' | 'collaboration' | 'chat'
}

const ENTRY_ITEMS: Record<
  WorkbenchSidebarProps['entryMode'],
  { id: 'recent' | 'mine' | 'shared' | 'project' | 'starred'; label: string }[]
> = {
  library: [
    { id: 'recent', label: '最近打开' },
    { id: 'mine', label: '我的文档' },
    { id: 'shared', label: '共享给我' },
  ],
  collaboration: [
    { id: 'project', label: '协作文档' },
    { id: 'shared', label: '共享给我' },
    { id: 'recent', label: '历史版本' },
  ],
  chat: [
    { id: 'project', label: '当前任务文档' },
    { id: 'mine', label: 'AI 生成文档' },
    { id: 'recent', label: '最近打开' },
  ],
}

export function WorkbenchSidebar({ entryMode }: WorkbenchSidebarProps) {
  const { activeSpace, setActiveSpace, openDocument, recentDocuments } = useDocumentWorkbenchStore()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [openingDocumentId, setOpeningDocumentId] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  const exampleDocument = useMemo<WorkbenchDocumentItem>(
    () => ({
      id: 'example-doc',
      title: '示例合同草稿',
      kind: 'markdown',
      content: '# 示例合同草稿\n\n第一条 合同目的',
    }),
    [],
  )

  const markdownExample = useMemo<WorkbenchDocumentItem>(
    () => ({
      id: 'markdown-example',
      title: 'Markdown 示例',
      kind: 'markdown',
      content: '# Markdown 示例\n\n- 支持基础编辑\n- 支持多标签切换',
    }),
    [],
  )

  const pdfExample = useMemo<WorkbenchDocumentItem>(
    () => ({
      id: 'pdf-example',
      title: 'PDF 示例文件',
      kind: 'pdf',
    }),
    [],
  )

  const excelExample = useMemo<WorkbenchDocumentItem>(
    () => ({
      id: 'excel-example',
      title: 'Excel 示例文件',
      kind: 'spreadsheet',
    }),
    [],
  )

  const pptExample = useMemo<WorkbenchDocumentItem>(
    () => ({
      id: 'ppt-example',
      title: 'PPT 示例文件',
      kind: 'presentation',
    }),
    [],
  )

  useEffect(() => {
    let cancelled = false

    const loadDocuments = async () => {
      setLoading(true)
      try {
        const result = await documentsApi.list({ page: 1, page_size: 8 })
        if (!cancelled) {
          setDocuments(result.items ?? [])
        }
      } catch {
        if (!cancelled) {
          setDocuments([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadDocuments()

    return () => {
      cancelled = true
    }
  }, [])

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

  const openApiDocument = async (document: Document) => {
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
    let detail = document

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
  }

  const filteredDocuments = useMemo(() => {
    const keyword = searchTerm.trim().toLowerCase()
    if (!keyword) return documents

    return documents.filter((item) => {
      const source = `${item.name} ${item.description ?? ''} ${item.doc_type}`.toLowerCase()
      return source.includes(keyword)
    })
  }, [documents, searchTerm])

  return (
    <aside
      data-testid="document-workbench-sidebar"
      className="flex w-64 flex-col border-r border-border bg-background/95"
    >
      <div className="border-b border-border px-4 py-3">
        <div className="text-sm font-semibold text-foreground">文档导航</div>
      </div>
      <div className="space-y-1 p-2">
        {ENTRY_ITEMS[entryMode].map((item) => (
          <button
            key={item.label}
            type="button"
            onClick={() => setActiveSpace(item.id)}
            className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition-colors ${
              activeSpace === item.id
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      {activeSpace === 'recent' && (
      <div className="border-t border-border px-3 py-3">
        <div className="mb-2 text-xs font-medium text-muted-foreground">最近打开记录</div>
        <div data-testid="workbench-recent-list" className="space-y-1">
          {recentDocuments.length > 0 ? (
            recentDocuments.map((document) => (
              <button
                key={`recent-${document.id}`}
                type="button"
                onClick={() => openDocument(document)}
                className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-foreground transition-colors hover:bg-muted"
              >
                <span className="truncate">{document.title}</span>
                <span className="ml-3 shrink-0 text-[11px] text-muted-foreground">{document.kind}</span>
              </button>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
              暂无最近打开文档
            </div>
          )}
        </div>
      </div>
      )}
      <div className="border-t border-border px-3 py-3">
        <div className="mb-2 text-xs font-medium text-muted-foreground">真实文档</div>
        <input
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="搜索真实文档"
          className="mb-3 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
        />
        <div className="space-y-1">
          {loading ? (
            <div className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
              正在加载文档...
            </div>
          ) : filteredDocuments.length > 0 ? (
            filteredDocuments.map((document) => (
              <button
                key={document.id}
                type="button"
                onClick={() => void openApiDocument(document)}
                className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-foreground transition-colors hover:bg-muted"
              >
                <span className="truncate">{document.name}</span>
                <span className="ml-3 shrink-0 text-[11px] text-muted-foreground">
                  {openingDocumentId === document.id ? '打开中...' : document.doc_type}
                </span>
              </button>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
              {searchTerm.trim() ? '未找到匹配文档' : '暂无真实文档'}
            </div>
          )}
        </div>
      </div>
      <div className="mt-auto border-t border-border p-3">
        <button
          type="button"
          onClick={() => openDocument(exampleDocument)}
          className="w-full rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          打开示例文档
        </button>
        <button
          type="button"
          onClick={() => openDocument(markdownExample)}
          className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        >
          打开 Markdown 示例
        </button>
        <button
          type="button"
          onClick={() => openDocument(pdfExample)}
          className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        >
          打开 PDF 示例
        </button>
        <button
          type="button"
          onClick={() => openDocument(excelExample)}
          className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        >
          打开 Excel 示例
        </button>
        <button
          type="button"
          onClick={() => openDocument(pptExample)}
          className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        >
          打开 PPT 示例
        </button>
      </div>
    </aside>
  )
}
