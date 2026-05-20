/**
 * LongMessage — 长消息与文档卡片展示（V2）
 *
 * 两种展示模式：
 * 1. DocumentCard：当内容被识别为法律文书（合同/律师函/通知等） → 用文件卡片展示
 *    - 显示文件图标 + 标题 + 摘要 + "在工作台打开"按钮
 *    - 不在聊天流中直接渲染全文，节省空间
 * 2. FoldableContent：普通长消息（>500字）→ 默认显示前 300 字 + "展开全文"
 */

import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { icons } from '@/lib/icons'
import { proseStyle } from '@/lib/design-tokens'
import { useChatStore } from '@/lib/store'
import { isDocumentGeneration, cleanCanvasContent } from './canvasUtils'
import { ApprovalLinkInline, extractApprovalIds } from './ApprovalLinkInline'

const FOLD_THRESHOLD = 500  // 超过此长度自动折叠
const PREVIEW_LENGTH = 300  // 折叠状态下显示的字数

interface LongMessageProps {
  content: string
  // 是否历史消息（历史消息更严格折叠）
  isHistorical?: boolean
  onOpenInWorkspace?: (title: string, content: string, type: 'contract' | 'document') => void
}

/**
 * 从 Markdown 提取文档标题
 */
function extractTitle(content: string): string {
  const h1Match = content.match(/^#\s+(.+)$/m)
  if (h1Match) return h1Match[1].trim()

  const firstLine = content.split('\n').find((l) => l.trim().length > 0)?.trim() || ''
  if (firstLine.length < 80) return firstLine.replace(/^[#*\-\s]+/, '')

  // 匹配文书类型关键词
  const docTypeMatch = content.match(/^(.+?(?:合同|协议|意见书|律师函|起诉状|答辩状|仲裁申请书|通知书|声明|备忘录|章程|决议))/m)
  if (docTypeMatch) return docTypeMatch[1].trim()

  return '法律文书'
}

/**
 * 根据内容推断文档类型
 */
function inferDocType(content: string): 'contract' | 'document' {
  return /合同|协议|contract|agreement|保密|NDA/i.test(content) ? 'contract' : 'document'
}

/**
 * 生成摘要（去掉 markdown 格式，取前 N 字）
 */
function makeSummary(content: string, maxChars = 120): string {
  const plain = content
    .replace(/^#+\s+/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`(.+?)`/g, '$1')
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return plain.length > maxChars ? plain.slice(0, maxChars) + '...' : plain
}

/**
 * 文档卡片 — 用于 AI 生成的长篇法律文书
 */
function DocumentCard({
  title,
  summary,
  charCount,
  docType,
  onOpen,
}: {
  title: string
  summary: string
  charCount: number
  docType: 'contract' | 'document'
  onOpen: () => void
}) {
  const iconColor = docType === 'contract' ? 'text-primary' : 'text-foreground'
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-border rounded-xl bg-card/50 hover:bg-card/80 transition-colors overflow-hidden max-w-sm"
    >
      <button
        onClick={onOpen}
        className="w-full p-3.5 flex items-start gap-3 text-left"
      >
        <div className={`w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 ${iconColor}`}>
          <icons.FileText className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-sm font-medium text-foreground truncate">{title}</span>
            <span className="text-[9px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded flex-shrink-0">
              {docType === 'contract' ? '合同' : '文书'}
            </span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
            {summary}
          </p>
          <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
            <span>{charCount} 字</span>
            <span className="flex items-center gap-1 text-primary">
              <icons.Edit className="w-3 h-3" /> 点击在工作台打开
            </span>
          </div>
        </div>
      </button>
    </motion.div>
  )
}

/**
 * 可折叠内容 — 用于超长但非典型文书的消息
 */
function FoldableContent({ content, defaultFolded }: { content: string; defaultFolded: boolean }) {
  const [expanded, setExpanded] = useState(!defaultFolded)
  const charCount = content.length

  const preview = useMemo(() => {
    const plain = content.replace(/\n+/g, '\n').trim()
    return plain.slice(0, PREVIEW_LENGTH) + (plain.length > PREVIEW_LENGTH ? '...' : '')
  }, [content])

  return (
    <div>
      <AnimatePresence mode="wait" initial={false}>
        {expanded ? (
          <motion.div
            key="full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={proseStyle.chat}
          >
            <ReactMarkdown>{content}</ReactMarkdown>
          </motion.div>
        ) : (
          <motion.div
            key="preview"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap line-clamp-6">
              {preview}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-2 text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1"
      >
        {expanded ? (
          <>
            <icons.ChevronUp className="w-3.5 h-3.5" />
            收起（{charCount} 字）
          </>
        ) : (
          <>
            <icons.ChevronDown className="w-3.5 h-3.5" />
            展开全文（{charCount} 字）
          </>
        )}
      </button>
    </div>
  )
}

/**
 * 主组件：根据内容特征自动选择展示方式
 */
export function LongMessage({ content, isHistorical, onOpenInWorkspace }: LongMessageProps) {
  const setCanvasContent = useChatStore((s) => s.setCanvasContent)
  const setRightPanelTab = useChatStore((s) => s.setRightPanelTab)

  const charCount = content.length
  const isDoc = isDocumentGeneration(content)

  // 文档类：显示文件卡片
  if (isDoc) {
    const cleanContent = cleanCanvasContent(content)
    const title = extractTitle(cleanContent)
    const docType = inferDocType(cleanContent)
    const summary = makeSummary(cleanContent, 120)

    const handleOpen = () => {
      if (onOpenInWorkspace) {
        onOpenInWorkspace(title, cleanContent, docType)
      } else {
        // 默认行为：写入 Canvas 并切换到文档 tab
        setCanvasContent({
          type: docType,
          title,
          content: cleanContent,
          suggestions: [],
        })
        setRightPanelTab?.('document')
      }
    }

    return (
      <DocumentCard
        title={title}
        summary={summary}
        charCount={cleanContent.length}
        docType={docType}
        onOpen={handleOpen}
      />
    )
  }

  // I3 (2026-05-14): 提取审批工单 id, 若有则渲染顶部 chip 链, 用户可一键跳转 admin 审批面板
  const approvalIds = extractApprovalIds(content)

  const renderApprovalBanner = () => {
    if (approvalIds.length === 0) return null
    return (
      <div className="flex flex-wrap items-center gap-1.5 mb-2 text-xs">
        <span className="text-muted-foreground">🔐 涉及审批工单:</span>
        {approvalIds.map(id => (
          <ApprovalLinkInline key={id} approvalId={id} />
        ))}
      </div>
    )
  }

  // 长文本：可折叠
  if (charCount > FOLD_THRESHOLD) {
    return (
      <>
        {renderApprovalBanner()}
        <FoldableContent content={content} defaultFolded={isHistorical || charCount > 1500} />
      </>
    )
  }

  // 短消息：直接渲染
  return (
    <div className={proseStyle.chat}>
      {renderApprovalBanner()}
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}
