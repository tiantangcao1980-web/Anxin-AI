/**
 * ChatWindow - IM 聊天窗口
 *
 * 右侧面板：顶部标题栏 + 消息列表 + 底部输入框。
 * 支持回复引用、正在输入状态、滚动加载历史消息。
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { inputStyle, heading, iconSize } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import { imApi } from '@/lib/api'
import { toast } from 'sonner'
import { useIMStore, useAuthStore, type IMMessage } from '@/lib/store'
import { useIMWebSocket } from '@/hooks/useIMWebSocket'
import { MessageItem } from './MessageItem'

interface ChatWindowProps {
  conversationId: string
  onBack?: () => void
}

export function ChatWindow({ conversationId, onBack }: ChatWindowProps) {
  const [inputText, setInputText] = useState('')
  const [replyTo, setReplyTo] = useState<IMMessage | null>(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [sending, setSending] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const messages = useIMStore((s) => s.messagesMap[conversationId] || [])
  const prependMessages = useIMStore((s) => s.prependMessages)
  const typingUsers = useIMStore((s) => s.typingUsers[conversationId] || [])
  const conversations = useIMStore((s) => s.conversations)
  const markAsRead = useIMStore((s) => s.markAsRead)
  const currentUser = useAuthStore((s) => s.user)
  const { send } = useIMWebSocket()

  const conversation = conversations.find((c) => c.id === conversationId)

  // 加载消息历史
  const loadMessages = useCallback(
    async (beforeId?: string) => {
      setLoadingHistory(true)
      try {
        const res = await imApi.getMessages(conversationId, {
          before_id: beforeId,
          limit: 50,
        })
        if (res?.data) {
          const msgs = res.data as IMMessage[]
          if (msgs.length < 50) setHasMore(false)

          if (beforeId) {
            prependMessages(conversationId, msgs)
          } else {
            prependMessages(conversationId, msgs)
          }
        }
      } catch (err) {
        console.error('[IM] 加载消息失败:', err)
      } finally {
        setLoadingHistory(false)
      }
    },
    [conversationId, prependMessages]
  )

  // 首次加载
  useEffect(() => {
    if (conversationId) {
      loadMessages()
      // 标记已读
      markAsRead(conversationId)
      send({ type: 'read_receipt', conversation_id: conversationId })
    }
  }, [conversationId])

  // 新消息自动滚动
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  // 加载更多
  const handleLoadMore = () => {
    if (loadingHistory || !hasMore || messages.length === 0) return
    const oldest = messages[0]
    loadMessages(oldest.id)
  }

  // 发送消息
  const handleSend = async () => {
    const text = inputText.trim()
    if (!text || sending) return

    setSending(true)
    try {
      send({
        type: 'message',
        conversation_id: conversationId,
        content: text,
        message_type: 'text',
        reply_to_id: replyTo?.id || undefined,
      })

      setInputText('')
      setReplyTo(null)
      inputRef.current?.focus()
    } catch {
      toast.error('消息发送失败，请重试')
    } finally {
      setSending(false)
    }
  }

  // 键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 输入状态
  const handleInputChange = (value: string) => {
    setInputText(value)

    // 节流发送 typing 状态
    if (typingTimerRef.current) clearTimeout(typingTimerRef.current)
    typingTimerRef.current = setTimeout(() => {
      send({ type: 'typing', conversation_id: conversationId })
    }, 300)
  }

  // 撤回消息
  const handleRecall = (messageId: string) => {
    send({ type: 'recall', message_id: messageId })
  }

  // 获取对话标题
  const title = conversation?.title || getTitle(conversation, currentUser?.id)

  // 查找回复引用的消息
  const findReplyMessage = (replyToId?: string): IMMessage | null => {
    if (!replyToId) return null
    return messages.find((m) => m.id === replyToId) || null
  }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部标题栏 */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
        {onBack && (
          <Button variant="ghost" size="icon" className="h-8 w-8 lg:hidden" onClick={onBack}>
            <icons.ChevronLeft className={iconSize.md} />
          </Button>
        )}
        <div className="flex-1 min-w-0">
          <h3 className={`${heading.card} truncate`}>{title}</h3>
          {conversation && (
            <p className={heading.micro}>
              {conversation.participants?.length || 0} 位成员
            </p>
          )}
        </div>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <icons.MoreHorizontal className={iconSize.md} />
        </Button>
      </div>

      {/* 消息列表 */}
      <ScrollArea className="flex-1 px-4" ref={scrollRef}>
        <div className="py-3 space-y-3">
          {/* 加载更多 */}
          {hasMore && (
            <div className="flex justify-center">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-muted-foreground"
                onClick={handleLoadMore}
                disabled={loadingHistory}
              >
                {loadingHistory ? (
                  <icons.Loader2 className={`${iconSize.sm} animate-spin mr-1`} />
                ) : null}
                {loadingHistory ? '加载中...' : '加载更多'}
              </Button>
            </div>
          )}

          {/* 空消息欢迎文案 */}
          {!loadingHistory && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <div className="w-12 h-12 rounded-xl bg-primary/5 flex items-center justify-center mb-3">
                <icons.MessageSquare className={`${iconSize.lg} text-primary/40`} />
              </div>
              <p className="text-sm font-medium">开始对话吧</p>
              <p className="text-xs mt-1">发送第一条消息开始交流</p>
            </div>
          )}

          {/* 消息列表（含时间分割线） */}
          {messages.map((msg, idx) => {
            const prev = idx > 0 ? messages[idx - 1] : null
            const showTimeDivider = shouldShowTimeDivider(prev?.created_at, msg.created_at)

            return (
              <div key={msg.id}>
                {showTimeDivider && (
                  <div className="flex items-center justify-center py-2">
                    <span className="text-[10px] text-muted-foreground/50 bg-muted/50 px-3 py-0.5 rounded-full">
                      {formatTimeDivider(msg.created_at)}
                    </span>
                  </div>
                )}
                <MessageItem
                  message={msg}
                  senderName={getSenderName(msg.sender_id, conversation)}
                  replyToMessage={findReplyMessage(msg.reply_to_id)}
                  onReply={(m) => setReplyTo(m)}
                  onRecall={handleRecall}
                />
              </div>
            )
          })}

          {/* 正在输入 */}
          {typingUsers.length > 0 && (
            <div className="flex items-center gap-1.5 px-2">
              <span className="text-xs text-muted-foreground animate-pulse">
                {typingUsers.length === 1
                  ? `${getSenderName(typingUsers[0], conversation)} 正在输入...`
                  : `${typingUsers.length} 人正在输入...`}
              </span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* 回复引用条 */}
      {replyTo && (
        <div className="flex items-center gap-2 px-4 py-2 bg-muted/50 border-t border-border shrink-0">
          <div className="flex-1 min-w-0">
            <span className="text-xs text-muted-foreground">
              回复 {getSenderName(replyTo.sender_id, conversation)}
            </span>
            <p className="text-xs text-foreground truncate">{replyTo.content}</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 shrink-0"
            onClick={() => setReplyTo(null)}
          >
            <icons.X className={iconSize.sm} />
          </Button>
        </div>
      )}

      {/* 输入框 */}
      <div className="px-4 py-3 border-t border-border shrink-0">
        <div className={inputStyle.chatContainer}>
          <textarea
            ref={inputRef}
            className={`${inputStyle.chatTextarea} px-4 max-h-32`}
            placeholder="输入消息..."
            rows={1}
            value={inputText}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 shrink-0 mr-1"
            disabled={!inputText.trim() || sending}
            onClick={handleSend}
          >
            {sending ? (
              <icons.Loader2 className={`${iconSize.md} text-muted-foreground animate-spin`} />
            ) : (
              <icons.Send
                className={`${iconSize.md} ${
                  inputText.trim() ? 'text-primary' : 'text-muted-foreground'
                }`}
              />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ===== 工具函数 =====

function getTitle(
  conversation: ReturnType<typeof useIMStore.getState>['conversations'][number] | undefined,
  currentUserId?: string
): string {
  if (!conversation) return '对话'
  if (conversation.title) return conversation.title
  if (conversation.type === 'private' && currentUserId) {
    const other = conversation.participants?.find((p) => p.user_id !== currentUserId)
    return other?.nickname || other?.user_id?.slice(0, 8) || '私聊'
  }
  if (conversation.type === 'case') return '案件讨论'
  if (conversation.type === 'contract') return '合同讨论'
  return '群聊'
}

function getSenderName(
  senderId: string,
  conversation?: ReturnType<typeof useIMStore.getState>['conversations'][number]
): string {
  if (!conversation) return senderId.slice(0, 8)
  const participant = conversation.participants?.find((p) => p.user_id === senderId)
  return participant?.nickname || senderId.slice(0, 8)
}

/**
 * 判断是否需要显示时间分割线
 * 两条消息间隔超过 5 分钟则显示
 */
function shouldShowTimeDivider(prevTime?: string, currTime?: string): boolean {
  if (!prevTime || !currTime) return !!currTime
  const diff = new Date(currTime).getTime() - new Date(prevTime).getTime()
  return diff > 5 * 60 * 1000
}

function formatTimeDivider(isoStr: string): string {
  const date = new Date(isoStr)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const msgDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())

  const time = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

  if (msgDay.getTime() === today.getTime()) return time
  if (msgDay.getTime() === today.getTime() - 86400000) return `昨天 ${time}`

  const isThisYear = date.getFullYear() === now.getFullYear()
  if (isThisYear) {
    return `${date.getMonth() + 1}月${date.getDate()}日 ${time}`
  }
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()} ${time}`
}
