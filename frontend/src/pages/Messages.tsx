/**
 * Messages - IM 即时通讯页面
 *
 * 左右分栏布局：
 * - lg 以上：左侧对话列表 + 右侧聊天窗口
 * - lg 以下：全屏列表 / 全屏聊天窗口切换
 *
 * 使用 PageContainer scrollable={false} fullHeight 确保撑满容器。
 */

import { useState, useEffect } from 'react'
import { PageContainer } from '@/components/ui/PageContainer'
import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { useIMStore } from '@/lib/store'
import { useIMWebSocket } from '@/hooks/useIMWebSocket'
import { ConversationList } from '@/components/im/ConversationList'
import { ChatWindow } from '@/components/im/ChatWindow'

export default function Messages() {
  // 移动端模式下，用于切换列表/聊天视图
  const [mobileView, setMobileView] = useState<'list' | 'chat'>('list')

  const activeId = useIMStore((s) => s.activeConversationId)
  const setActiveConversation = useIMStore((s) => s.setActiveConversation)

  // 确保 IM WebSocket 已连接
  const { isConnected, connect } = useIMWebSocket()
  useEffect(() => {
    if (!isConnected) {
      connect()
    }
  }, [isConnected, connect])

  // 选择对话
  const handleSelectConversation = (id: string) => {
    setActiveConversation(id)
    setMobileView('chat')
  }

  // 返回列表（移动端）
  const handleBack = () => {
    setMobileView('list')
  }

  // 新建对话（占位）
  const handleNewConversation = () => {
    // TODO: 弹出创建对话 Dialog
    console.info('[IM] 新建对话')
  }

  return (
    <PageContainer scrollable={false} fullHeight showHeader={false}>
      {/* WebSocket 连接状态 */}
      {!isConnected && (
        <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 text-sm shrink-0 -m-4 sm:-m-5 lg:-m-6 mb-0">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          连接已断开，正在尝试重连...
        </div>
      )}
      <div className="flex-1 flex min-h-0 -m-4 sm:-m-5 lg:-m-6">
        {/* 左侧对话列表 */}
        <div
          className={`w-full lg:w-80 xl:w-96 border-r border-border shrink-0 ${
            mobileView === 'list' ? 'block' : 'hidden lg:block'
          }`}
        >
          <ConversationList
            onSelect={handleSelectConversation}
            onNewConversation={handleNewConversation}
          />
        </div>

        {/* 右侧聊天窗口 */}
        <div
          className={`flex-1 min-w-0 ${
            mobileView === 'chat' ? 'block' : 'hidden lg:block'
          }`}
        >
          {activeId ? (
            <ChatWindow
              conversationId={activeId}
              onBack={handleBack}
            />
          ) : (
            <EmptyState />
          )}
        </div>
      </div>
    </PageContainer>
  )
}

// ===== 空状态 =====

function EmptyState() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
      <div className="w-16 h-16 rounded-2xl bg-primary/5 flex items-center justify-center mb-4">
        <icons.MessageSquare className={`${iconSize['2xl']} text-primary/40`} />
      </div>
      <p className={heading.section}>选择对话开始聊天</p>
      <p className="text-sm mt-1 max-w-xs text-center">
        从左侧列表选择一个对话，或点击新建按钮开始新对话
      </p>
    </div>
  )
}
