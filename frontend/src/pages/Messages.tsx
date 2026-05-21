/**
 * Messages · 消息中心（Editorial Luxury 改造 · Phase 1.15）
 *
 * 旧版用 PageContainer + bg-primary/5 圆角空状态 + 药丸状 Tab。
 * 新版：满高 1px hairline 双栏布局 + Editorial 下划线 Tab + tracker 标识。
 *
 * 融合 IM 即时通讯和系统通知的统一入口：
 *   - 左侧：messages/notifications Tab + 列表
 *   - 右侧：聊天窗口 / 通知详情
 *   - lg 以下：mobileView 切换 list / detail
 */
import { useState, useEffect, useCallback } from 'react'
import { Loader2, MessageSquare, Bell } from 'lucide-react'

import { useIMStore, useNotificationStore, type NotificationItem } from '@/lib/store'
import { useIMWebSocket } from '@/hooks/useIMWebSocket'
import { notificationsApi } from '@/lib/api'
import { ConversationList } from '@/components/im/ConversationList'
import { ChatWindow } from '@/components/im/ChatWindow'
import { NotificationList } from '@/components/im/NotificationList'
import { NotificationDetail } from '@/components/im/NotificationDetail'
import { CreateConversationDialog } from '@/components/im/CreateConversationDialog'
import { cn } from '@/components/ui/utils'

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
  const markNotificationRead = useNotificationStore((s) => s.markNotificationRead)

  const { isConnected, connect } = useIMWebSocket()
  useEffect(() => { if (!isConnected) connect() }, [isConnected, connect])

  const handleSelectConversation = (id: string) => {
    setActiveConversation(id)
    setSelectedNotification(null)
    setMobileView('detail')
  }

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

  const handleBack = () => {
    setMobileView('list')
    setSelectedNotification(null)
  }

  const handleTabChange = (tab: 'messages' | 'notifications') => {
    setActiveTab(tab)
    if (tab === 'notifications') setActiveConversation(null)
    else setSelectedNotification(null)
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* WS 状态条 */}
      {!isConnected && (
        <div className="shrink-0 flex items-center justify-between px-6 py-2 border-b border-warning/20 bg-warning/5">
          <div className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-warning">
            <Loader2 className="w-3 h-3 stroke-[1.5] animate-spin" />
            <span>Connecting</span>
            <span className="text-warning/40" aria-hidden>·</span>
            <span className="normal-case tracking-normal">消息服务连接中…</span>
          </div>
          <button
            type="button"
            onClick={() => connect()}
            className="text-[12px] uppercase tracking-[0.12em] text-warning hover:text-warning/80 transition-colors"
          >
            手动重连 →
          </button>
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        {/* ===== 左侧 ===== */}
        <aside
          className={cn(
            'w-full lg:w-80 xl:w-96 border-r border-border shrink-0 flex flex-col bg-card',
            mobileView === 'list' ? 'block' : 'hidden lg:flex',
          )}
        >
          {/* Tracker */}
          <div className="px-5 pt-5 pb-3 shrink-0">
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Inbox
              <span className="text-foreground/30 mx-1.5" aria-hidden>·</span>
              <span className="text-foreground/70 normal-case tracking-normal">消息中心</span>
            </div>
          </div>

          {/* Tab 切换 */}
          <nav className="flex items-center border-b border-border shrink-0" role="tablist">
            <TabButton
              active={activeTab === 'messages'}
              onClick={() => handleTabChange('messages')}
              badge={imUnreadTotal}
              icon={<MessageSquare className="w-3.5 h-3.5 stroke-[1.5]" />}
              labelEn="Messages"
              label="消息"
            />
            <TabButton
              active={activeTab === 'notifications'}
              onClick={() => handleTabChange('notifications')}
              badge={notifUnreadCount}
              icon={<Bell className="w-3.5 h-3.5 stroke-[1.5]" />}
              labelEn="Notify"
              label="通知"
            />
          </nav>

          {/* 列表 */}
          <div className="flex-1 min-h-0">
            {activeTab === 'messages' ? (
              <ConversationList
                onSelect={handleSelectConversation}
                onNewConversation={() => setShowCreateDialog(true)}
              />
            ) : (
              <NotificationList
                onSelect={handleSelectNotification}
                selectedId={selectedNotification?.id}
              />
            )}
          </div>
        </aside>

        {/* ===== 右侧 ===== */}
        <section
          className={cn(
            'flex-1 min-w-0 bg-background',
            mobileView === 'detail' ? 'block' : 'hidden lg:block',
          )}
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
        </section>
      </div>

      <CreateConversationDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onCreated={(id) => handleSelectConversation(id)}
      />
    </div>
  )
}

function TabButton({
  active, onClick, badge, icon, labelEn, label,
}: {
  active: boolean
  onClick: () => void
  badge?: number
  icon: React.ReactNode
  labelEn: string
  label: string
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        'relative flex-1 flex items-center justify-center gap-2 py-3 text-[11px] font-medium uppercase tracking-[0.16em] transition-colors outline-none focus-visible:text-foreground',
        active
          ? 'text-foreground after:absolute after:left-3 after:right-3 after:bottom-0 after:h-px after:bg-primary'
          : 'text-muted-foreground hover:text-foreground',
      )}
    >
      {icon}
      <span>{labelEn}</span>
      <span className="text-foreground/30" aria-hidden>·</span>
      <span className="normal-case tracking-normal">{label}</span>
      {badge != null && badge > 0 && (
        <span className="ml-1 min-w-[18px] h-[16px] bg-destructive text-destructive-foreground text-[10px] font-medium flex items-center justify-center px-1 tabular-nums">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
    </button>
  )
}

function EmptyState({ tab }: { tab: 'messages' | 'notifications' }) {
  const isMessages = tab === 'messages'
  const Icon = isMessages ? MessageSquare : Bell
  return (
    <div className="h-full flex flex-col items-center justify-center px-8 text-center">
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
        {isMessages ? 'Messages · 空状态' : 'Notifications · 空状态'}
      </div>
      <Icon className="w-12 h-12 stroke-[1] text-foreground/20 mb-5" />
      <h2 className="font-serif text-[22px] text-foreground mb-2">
        {isMessages ? '选择对话开始聊天' : '选择通知查看详情'}
      </h2>
      <p className="text-[13px] text-muted-foreground max-w-xs leading-relaxed">
        {isMessages
          ? '从左侧列表选择一个对话，或点击新建按钮开始新对话。'
          : '从左侧列表选择一条通知查看详细内容。'}
      </p>
    </div>
  )
}
