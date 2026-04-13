import { useRef, useCallback } from 'react'
import { Upload, Share2, History, Download, PanelRightClose, PanelRightOpen } from 'lucide-react'
import { useActiveWorkbenchDocument } from './hooks/useActiveWorkbenchDocument'
import { useDocumentWorkbenchStore } from './hooks/useDocumentWorkbenchStore'
import { documentsApi } from '@/lib/api'
import { toast } from 'sonner'

interface WorkbenchTopbarProps {
  entryMode: 'library' | 'collaboration' | 'chat'
  showRightPanel: boolean
  onToggleRightPanel: () => void
}

const ENTRY_MODE_LABEL: Record<WorkbenchTopbarProps['entryMode'], string> = {
  library: '智能文档',
  collaboration: '协作文档',
  chat: '智能工作台',
}

export function WorkbenchTopbar({ entryMode, showRightPanel, onToggleRightPanel }: WorkbenchTopbarProps) {
  const { activeDocument, kindLabel } = useActiveWorkbenchDocument()
  const openDocument = useDocumentWorkbenchStore(s => s.openDocument)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const doc = await documentsApi.upload(file, {})
      openDocument({
        id: doc.id,
        title: doc.name,
        kind: doc.doc_type === 'pdf' ? 'pdf' : doc.doc_type === 'markdown' ? 'markdown' : 'doc',
        content: doc.extracted_text || doc.description || '',
      })
      toast.success('文档上传成功')
    } catch {
      toast.error('上传失败，请重试')
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [openDocument])

  const handleExport = useCallback(() => {
    if (!activeDocument?.content) {
      toast.info('当前文档无内容可导出')
      return
    }
    const blob = new Blob([activeDocument.content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${activeDocument.title || '文档'}.md`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('文档已导出')
  }, [activeDocument])

  const btnClass = "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"

  return (
    <header
      data-testid="document-workbench-topbar"
      className="flex h-14 items-center justify-between border-b border-border bg-background px-4"
    >
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-foreground">{ENTRY_MODE_LABEL[entryMode]}</div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span data-testid="workbench-active-title" className="truncate max-w-[200px]">
            {activeDocument?.title ?? '未打开文档'}
          </span>
          <span className="text-border">·</span>
          <span>{kindLabel}</span>
        </div>
      </div>
      <div className="flex items-center gap-1">
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".md,.txt,.pdf,.docx,.doc,.xlsx,.xls,.csv,.ppt,.pptx"
          onChange={handleUpload}
        />
        <button type="button" onClick={() => fileInputRef.current?.click()} className={btnClass}>
          <Upload className="h-3.5 w-3.5" />
          上传
        </button>
        <button type="button" onClick={handleExport} className={btnClass}>
          <Download className="h-3.5 w-3.5" />
          导出
        </button>
        <button type="button" onClick={() => toast.info('分享功能即将上线')} className={btnClass}>
          <Share2 className="h-3.5 w-3.5" />
          分享
        </button>
        <button
          type="button"
          onClick={onToggleRightPanel}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs transition-colors ${
            showRightPanel
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          }`}
        >
          {showRightPanel ? (
            <PanelRightClose className="h-3.5 w-3.5" />
          ) : (
            <PanelRightOpen className="h-3.5 w-3.5" />
          )}
          版本
        </button>
      </div>
    </header>
  )
}
