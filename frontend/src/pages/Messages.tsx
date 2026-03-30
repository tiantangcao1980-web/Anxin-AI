/**
 * Messages - 消息中心页面
 *
 * 融合 IM 即时通讯和系统通知的统一入口。
 * 左右分栏布局：
 * - 左侧：消息/通知 Tab 切换 + 对应列表
 * - 右侧：聊天窗口 / 通知详情
 * - lg 以下：全屏列表 / 全屏详情切换
 */

import { useState, useEffect, useCallback } from 'react'
import { PageContainer } from '@/components/ui/PageContainer'
import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { useIMStore, useNotificationStore, type NotificationItem } from '@/lib/store'
import { useIMWebSocket } from '@/hooks/useIMWebSocket'
import { notificationsApi } from '@/lib/api'
import { ConversationList } from '@/components/im/ConversationList'
import { ChatWindow } from '@/components/im/ChatWindow'
import { NotificationList } from '@/components/im/NotificationList'
import { NotificationDetail } from '@/components/im/NotificationDetail'
import { CreateConversationDialog } from '@/components/im/CreateConversationDialog'

export default function Messages() {
  const [mobileView, setMobileView] = useState<'list' | 'detail'>('list')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [selectedNotification, setSelectedNotification] = useState<NotificationItem | null>(null)

  const activeId = useIMStore((s) => s.activeConversationId)
  const setActiveConversation = useIMStore((s) => s.setActiveConversation)
  const imUnreadTotal = useIMStore((s) => s.unreadTotal)

  const activeTab = useNotificationStore((s) => s.activeTab)
  const setActiveTab = useNotificationStore((s) => s.setActiveTab)
  const notifUnreadCount = useNotificationStore((s) => s.unreadCount)
  const notifications = useNotificationStore((s) => s.notifications)
  const markNotificationRead = useNotificationStore((s) => s.markNotificationRead)

  const { isConnected, connect } = useIMWebSocket()
  useEffect(() => {
    if (!isConnected) connect()
  }, [isConnected, connect])

  // 选择对话
  const handleSelectConversation = (id: string) => {
    setActiveConversation(id)
    setSelectedNotification(null)
    setMobileView('detail')
  }

  // 选择通知
  const handleSelectNotification = useCallback(async (item: NotificationItem) => {
    setSelectedNotification(item)
    setActiveConversation(null)
    setMobileView('detail')

    if (!item.is_read) {
      try {
        await notificationsApi.markAsRead(item.id)
        markNotificationRead(item.id)
      } catch { /* 静默 */ }
    }
  }, [setActiveConversation, markNotificationRead])

  // 返回列表（移动端）
  const handleBack = () => {
    setMobileView('list')
    setSelectedNotification(null)
  }

  // 新建对话
  const handleNewConversation = () => {
    setShowCreateDialog(true)
  }

  // 切换 Tab 时清除右侧选中状态
  const handleTabChange = (tab: 'messages' | 'notifications') => {
    setActiveTab(tab)
    if (tab === 'notifications') {
      setActiveConversation(null)
    } else {
      setSelectedNotification(null)
    }
  }

  // 右侧面板内容
  const hasRightContent =
    activeTab === 'messages' ? !!activeId : !!selectedNotification

  return (
    <PageContainer scrollable={false} fullHeight showHeader={false}>
      {/* WebSocket 连接状态 */}
      {!isConnected && (
        <div className="flex items-center justify-between px-4 py-1.5 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 text-xs shrink-0 -m-4 sm:-m-5 lg:-m-6 mb-0">
          <div className="flex items-center gap-2">
            <icons.Loader2 className="w-3 h-3 animate-spin" />
            <span>消息服务连接中...</span>
          </div>
          <button
            onClick={() => connect()}
            className="text-xs font-medium text-amber-800 dark:text-amber-300 hover:underline"
          >
            手动重连
          </button>
        </div>
      )}

      <div className="flex-1 flex min-h-0 -m-4 sm:-m-5 lg:-m-6">
        {/* ===== 左侧面板 ===== */}
        <div
          className={`w-full lg:w-80 xl:w-96 border-r border-border shrink-0 flex flex-col ${
            mobileView === 'list' ? 'block' : 'hidden lg:flex'
          }`}
        >
          {/* Tab 切换器 */}
          <div className="flex items-center border-b border-border shrink-0">
            <TabButton
              active={activeTab === 'messages'}
              onClick={() => handleTabChange('messages')}
              badge={imUnreadTotal}
            >
              <icons.Chat className={iconSize.sm} />
              消息
            </TabButton>
            <TabButton
              active={activeTab === 'notifications'}
              onClick={() => handleTabChange('notifications')}
              badge={notifUnreadCount}
            >
              <icons.Notification className={iconSize.sm} />
              通知
            </TabButton>
          </div>

          {/* 列表内容 */}
          <div className="flex-1 min-h-0">
            {activeTab === 'messages' ? (
              <ConversationList
                onSelect={handleSelectConversation}
                onNewConversation={handleNewConversation}
              />
            ) : (
              <NotificationList onSelect={handleSelectNotification} selectedId={selectedNotification?.id} />
            )}
          </div>
        </div>

        {/* ===== 右侧面板 ===== */}
        <div
          className={`flex-1 min-w-0 ${
            mobileView === 'detail' ? 'block' : 'hidden lg:block'
          }`}
        >
          {activeTab === 'messages' && activeId ? (
            <ChatWindow conversationId={activeId} onBack={handleBack} />
          ) : activeTab === 'notifications' && selectedNotification ? (
            <NotificationDetail
              notification={selectedNotification}
              onBack={handleBack}
              onDeleted={() => {
                setSelectedNotification(null)
                setMobileView('list')
              }}
            />
          ) : (
            <EmptyState tab={activeTab} />
          )}
        </div>
      </div>

      {/* 新建对话弹窗 */}
      <CreateConversationDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onCreated={(id) => {
          handleSelectConversation(id)
        }}
      />
    </PageContainer>
  )
}

// ===== Tab 按钮 =====

function TabButton({
  active,
  onClick,
  badge,
  children,
}: {
  active: boolean
  onClick: () => void
  badge?: number
  children: React.ReactNode
}) {
  return (
    <button
      className={`relative flex-1 flex items-center justify-center gap-1.5 py-3 text-sm font-medium transition-colors border-b-2 ${
        active
          ? 'text-primary border-primary'
          : 'text-muted-foreground border-transparent hover:text-foreground hover:border-border'
      }`}
      onClick={onClick}
    >
      {children}
      {badge != null && badge > 0 && (
        <span className="min-w-[16px] h-[16px] bg-destructive text-white text-[10px] font-bold flex items-center justify-center rounded-full px-1">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
    </button>
  )
}

// ===== 空状态 =====

function EmptyState({ tab }: { tab: 'messages' | 'notifications' }) {
  const isMessages = tab === 'messages'

  return (
    <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
      <div className="w-16 h-16 rounded-2xl bg-primary/5 flex items-center justify-center mb-4">
        {isMessages ? (
          <icons.MessageSquare className={`${iconSize['2xl']} text-primary/40`} />
        ) : (
          <icons.Notification className={`${iconSize['2xl']} text-primary/40`} />
        )}
      </div>
      <p className={heading.section}>
        {isMessages ? '选择对话开始聊天' : '选择通知查看详情'}
      </p>
      <p className="text-sm mt-1 max-w-xs text-center">
        {isMessages
          ? '从左侧列表选择一个对话，或点击新建按钮开始新对话'
          : '从左侧列表选择一条通知查看详细内容'}
      </p>
    </div>
  )
}
