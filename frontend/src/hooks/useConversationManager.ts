/**
 * 会话管理 Hook
 *
 * 从 Chat.tsx 提取的会话 CRUD 操作
 * 包含：新建/切换/删除/重命名/批量操作
 */

import { useCallback, useRef, useState } from 'react'
import { toast } from 'sonner'
import { chatApi } from '@/lib/api'
import { useChatStore } from '@/lib/store'

export function useConversationManager(
  closeCurrentWs: () => void,
) {
  const store = useChatStore()

  // 编辑/重命名状态
  const [editingConvId, setEditingConvId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null)
  const editInputRef = useRef<HTMLInputElement>(null)

  // 批量操作状态
  const [batchMode, setBatchMode] = useState(false)
  const [selectedConvIds, setSelectedConvIds] = useState<Set<string>>(new Set())
  const [isBatchDeleting, setIsBatchDeleting] = useState(false)

  // 删除确认状态
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  // 加载会话列表
  const loadConversationsRef = useRef<() => Promise<void>>()
  const loadConversations = useCallback(async () => {
    try {
      const result = await chatApi.listConversations(50)
      if (Array.isArray(result?.conversations)) {
        store.setConversations(result.conversations)
      }
    } catch (e: any) {
      if (!e?.message?.includes('401')) {
        console.error('加载对话列表失败:', e)
      }
    }
  }, [store])
  loadConversationsRef.current = loadConversations

  // 新建会话
  const handleNewConversation = useCallback(() => {
    closeCurrentWs()
    store.setConversationId(null)
    store.setMessages([])
    store.setCanvasContent(null)
    store.clearAgentResults()
    store.clearThinkingSteps()
    store.clearWorkspaceActions()
    store.clearAgentTasks()
    store.setRequirementAnalysis(null)
    store.setRightPanelTab('smart')
  }, [store, closeCurrentWs])

  // 切换会话
  const handleSwitchConversation = useCallback((convId: string) => {
    if (convId === store.conversationId) return
    closeCurrentWs()
    store.setConversationId(convId)
    store.setMessages([])
    store.clearAgentResults()
    store.clearThinkingSteps()
    store.setCanvasContent(null)
    store.clearWorkspaceActions()
  }, [store, closeCurrentWs])

  // 删除会话
  const handleDeleteConversation = useCallback((convId: string) => {
    setDeleteConfirmId(convId)
  }, [])

  const confirmDeleteConversation = useCallback(async () => {
    if (!deleteConfirmId) return
    try {
      await chatApi.deleteConversation(deleteConfirmId)
      store.removeConversation(deleteConfirmId)
      if (store.conversationId === deleteConfirmId) {
        handleNewConversation()
      }
      toast.success('对话已删除')
    } catch (e) {
      toast.error('删除失败')
    }
    setDeleteConfirmId(null)
  }, [deleteConfirmId, store, handleNewConversation])

  // 重命名
  const handleStartRename = useCallback((convId: string, currentTitle: string) => {
    setEditingConvId(convId)
    setEditingTitle(currentTitle)
    setMenuOpenId(null)
    setTimeout(() => editInputRef.current?.focus(), 50)
  }, [])

  const handleFinishRename = useCallback(async () => {
    if (editingConvId && editingTitle.trim()) {
      try {
        await chatApi.updateConversationTitle(editingConvId, editingTitle.trim())
        store.updateConversationTitle(editingConvId, editingTitle.trim())
      } catch (e) {
        toast.error('重命名失败')
      }
    }
    setEditingConvId(null)
    setEditingTitle('')
  }, [editingConvId, editingTitle, store])

  // 批量操作
  const handleToggleBatchMode = useCallback(() => {
    setBatchMode(prev => {
      if (prev) setSelectedConvIds(new Set())
      return !prev
    })
  }, [])

  const handleToggleSelect = useCallback((convId: string) => {
    setSelectedConvIds(prev => {
      const next = new Set(prev)
      if (next.has(convId)) next.delete(convId)
      else next.add(convId)
      return next
    })
  }, [])

  const handleSelectAll = useCallback(() => {
    if (selectedConvIds.size === store.conversations.length) {
      setSelectedConvIds(new Set())
    } else {
      setSelectedConvIds(new Set(store.conversations.map(c => c.id)))
    }
  }, [selectedConvIds, store.conversations])

  const handleBatchDelete = useCallback(async () => {
    if (selectedConvIds.size === 0) return
    setIsBatchDeleting(true)
    try {
      for (const id of selectedConvIds) {
        await chatApi.deleteConversation(id)
        store.removeConversation(id)
      }
      if (store.conversationId && selectedConvIds.has(store.conversationId)) {
        handleNewConversation()
      }
      toast.success(`已删除 ${selectedConvIds.size} 个对话`)
      setSelectedConvIds(new Set())
      setBatchMode(false)
    } catch (e) {
      toast.error('批量删除失败')
    } finally {
      setIsBatchDeleting(false)
    }
  }, [selectedConvIds, store, handleNewConversation])

  return {
    // 状态
    editingConvId,
    editingTitle,
    setEditingTitle,
    menuOpenId,
    setMenuOpenId,
    editInputRef,
    deleteConfirmId,
    setDeleteConfirmId,
    batchMode,
    selectedConvIds,
    isBatchDeleting,
    // 方法
    loadConversations,
    loadConversationsRef,
    handleNewConversation,
    handleSwitchConversation,
    handleDeleteConversation,
    confirmDeleteConversation,
    handleStartRename,
    handleFinishRename,
    handleToggleBatchMode,
    handleToggleSelect,
    handleSelectAll,
    handleBatchDelete,
  }
}
