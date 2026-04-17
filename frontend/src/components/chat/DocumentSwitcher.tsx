/**
 * DocumentSwitcher — 工作台文档切换器
 *
 * V2 新增：在 Canvas 编辑器顶部显示对话内的所有历史文档
 * - 用户可点击切换打开不同文档
 * - 支持删除
 * - 显示更新时间
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { chatApi } from '@/lib/api'
import { toast } from 'sonner'
import { useChatStore } from '@/lib/store'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

interface DocumentItem {
  id: string
  title: string
  type: string
  updatedAt: string | number
  preview?: string
}

interface DocumentSwitcherProps {
  currentTitle?: string
  documents: DocumentItem[]
  onSelect: (doc: { id: string; title: string; content: string; type: string }) => void
  onDelete?: (id: string) => void
  onRefresh?: () => void
}

function formatTime(v: string | number): string {
  try {
    const d = new Date(v)
    const now = Date.now()
    const diff = now - d.getTime()
    const min = Math.floor(diff / 60000)
    if (min < 1) return '刚刚'
    if (min < 60) return `${min} 分钟前`
    if (min < 1440) return `${Math.floor(min / 60)} 小时前`
    return `${Math.floor(min / 1440)} 天前`
  } catch {
    return ''
  }
}

function docTypeLabel(t: string): string {
  const map: Record<string, string> = {
    contract: '合同',
    agreement: '协议',
    legal_opinion: '法律意见',
    document: '文书',
    other: '其他',
  }
  return map[t] || t
}

export function DocumentSwitcher({
  currentTitle,
  documents,
  onSelect,
  onDelete,
  onRefresh,
}: DocumentSwitcherProps) {
  const [expanded, setExpanded] = useState(false)
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  if (documents.length === 0) return null

  const handleSelect = async (doc: DocumentItem) => {
    if (loadingId) return
    setLoadingId(doc.id)
    try {
      const full = await chatApi.getDocumentContent(doc.id)
      onSelect({
        id: full.id,
        title: full.title,
        content: full.content || '',
        type: full.type,
      })
      setExpanded(false)
      toast.success(`已打开「${doc.title}」`)
    } catch (e: any) {
      toast.error(e?.message || '加载文档失败')
    } finally {
      setLoadingId(null)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    try {
      await chatApi.deleteDocument(deleteTarget)
      toast.success('已删除')
      onDelete?.(deleteTarget)
      onRefresh?.()
    } catch (e: any) {
      toast.error(e?.message || '删除失败')
    } finally {
      setDeleteTarget(null)
    }
  }

  return (
    <div className="border-b border-border bg-muted/30">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/60 transition-colors"
      >
        <icons.FileText className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
        <span className="text-xs text-muted-foreground">本对话文档</span>
        <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-medium">
          {documents.length}
        </span>
        <div className="flex-1" />
        <icons.ChevronDown
          className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="max-h-60 overflow-y-auto">
              {documents.map((doc) => {
                const isCurrent = currentTitle && doc.title === currentTitle
                return (
                  <div
                    key={doc.id}
                    className={`group flex items-center gap-2 px-3 py-2 border-t border-border/50 hover:bg-muted/60 transition-colors ${
                      isCurrent ? 'bg-primary/5' : ''
                    }`}
                  >
                    <button
                      onClick={() => handleSelect(doc)}
                      disabled={loadingId === doc.id}
                      className="flex-1 flex items-center gap-2 text-left min-w-0"
                    >
                      {loadingId === doc.id ? (
                        <icons.Loader2 className="w-3.5 h-3.5 animate-spin text-primary flex-shrink-0" />
                      ) : isCurrent ? (
                        <icons.CheckCircle className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                      ) : (
                        <icons.FileText className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className={`text-xs font-medium truncate ${isCurrent ? 'text-primary' : 'text-foreground'}`}>
                            {doc.title}
                          </span>
                          <span className="text-[9px] text-muted-foreground bg-muted px-1 rounded flex-shrink-0">
                            {docTypeLabel(doc.type)}
                          </span>
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5">
                          {formatTime(doc.updatedAt)}
                        </div>
                      </div>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setDeleteTarget(doc.id)
                      }}
                      className="p-1 rounded hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                      title="删除文档"
                    >
                      <icons.Delete className="w-3 h-3 text-destructive" />
                    </button>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="确认删除文档"
        description="删除后无法恢复，确定要删除这份文档吗？"
        confirmText="确认删除"
        destructive
        onConfirm={handleDeleteConfirm}
      />
    </div>
  )
}
