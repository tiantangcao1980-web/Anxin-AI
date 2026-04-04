/**
 * Canvas 操作 Hook
 *
 * 从 Chat.tsx 提取的 Canvas 编辑/保存/AI润色逻辑
 * 包含：防抖保存、文档导出、AI优化、建议处理、文档快捷操作
 */

import { useCallback, useRef, useState } from 'react'
import { toast } from 'sonner'
import { chatApi } from '@/lib/api'
import { useChatStore } from '@/lib/store'

export function useCanvasOperations(
  wsRef: React.MutableRefObject<WebSocket | null>,
  conversationId: string | null,
  setIsProcessing: (v: boolean) => void,
  handleSendMessage: (content: string) => void,
) {
  const store = useChatStore()
  const canvasSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [canvasSaved, setCanvasSaved] = useState(true)

  // Canvas 内容变更 → 防抖发送到后端
  const handleCanvasContentChange = useCallback((content: string) => {
    store.updateCanvasText(content)
    setCanvasSaved(false)

    if (canvasSaveTimerRef.current) clearTimeout(canvasSaveTimerRef.current)
    canvasSaveTimerRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'canvas_edit',
          content,
          title: store.canvasContent?.title || '文档',
          canvas_type: store.canvasContent?.type || 'document',
        }))
        setCanvasSaved(true)
      }
    }, 1500)
  }, [store, wsRef])

  // 手动保存到文档库
  const handleCanvasSaveAsDocument = useCallback(async () => {
    if (!store.canvasContent?.content) return
    try {
      await chatApi.sendMessage({
        content: `[系统] 保存文档: ${store.canvasContent.title}`,
        conversation_id: conversationId || undefined,
      })
      const { documentsApi } = await import('@/lib/api')
      await documentsApi.createText({
        name: store.canvasContent.title || '未命名文档',
        content: store.canvasContent.content,
        doc_type: store.canvasContent.type === 'contract' ? 'contract' : 'document',
        description: '通过 Canvas 编辑器创建',
      })
      toast.success('文档已保存到文档库')
      setCanvasSaved(true)
    } catch (e) {
      toast.error('保存失败，请稍后重试')
    }
  }, [store.canvasContent, conversationId])

  // AI 润色
  const handleCanvasAIOptimize = useCallback(() => {
    if (!store.canvasContent) {
      toast.error('没有文档内容可以润色')
      return
    }
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error('连接已断开，请刷新后重试')
      return
    }
    wsRef.current.send(JSON.stringify({
      type: 'canvas_request',
      canvas_content: store.canvasContent.content,
      canvas_type: store.canvasContent.type,
    }))
    setIsProcessing(true)
  }, [store.canvasContent, wsRef, setIsProcessing])

  // 建议接受/拒绝
  const handleCanvasSuggestionAction = useCallback((id: string, action: 'accept' | 'reject') => {
    if (!store.canvasContent) return
    const updated = (store.canvasContent.suggestions || []).map(s =>
      s.id === id ? { ...s, status: action === 'accept' ? 'accepted' as const : 'rejected' as const } : s
    )
    store.setCanvasContent({ ...store.canvasContent, suggestions: updated })
  }, [store])

  // 文档快捷操作（翻译/摘要/润色/风险检查）
  const handleDocumentAction = useCallback((action: string, _payload?: any) => {
    if (!store.canvasContent) {
      toast.error('没有文档内容')
      return
    }
    const content = store.canvasContent.content

    const actionMessages: Record<string, string> = {
      summarize: `请为以下文档生成结构化摘要，包含主要内容、关键条款和核心结论：\n\n---\n${content.slice(0, 10000)}`,
      translate: `请将以下文档翻译为英文（保留原格式）：\n\n---\n${content.slice(0, 10000)}`,
      optimize: `请对以下法律文档进行措辞润色和结构优化：\n\n---\n${content.slice(0, 10000)}`,
      risk_check: `请检查以下文档中的法律风险点，标出有风险的条款并给出修改建议：\n\n---\n${content.slice(0, 10000)}`,
    }

    const message = actionMessages[action]
    if (message) {
      handleSendMessage(message)
    }
  }, [store.canvasContent, handleSendMessage])

  return {
    canvasSaved,
    setCanvasSaved,
    handleCanvasContentChange,
    handleCanvasSaveAsDocument,
    handleCanvasAIOptimize,
    handleCanvasSuggestionAction,
    handleDocumentAction,
  }
}
