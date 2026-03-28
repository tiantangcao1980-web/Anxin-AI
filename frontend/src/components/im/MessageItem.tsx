/**
 * MessageItem - 单条 IM 消息组件
 *
 * 支持多种消息类型 (text/image/file/system)，
 * 撤回状态显示，回复引用，右键菜单（回复/撤回）。
 */

import { useState, useCallback } from 'react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { chatBubble, heading } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import { useAuthStore, type IMMessage } from '@/lib/store'

interface MessageItemProps {
  message: IMMessage
  /** 发送者显示名称 */
  senderName?: string
  /** 回复引用的原始消息 */
  replyToMessage?: IMMessage | null
  /** 触发回复 */
  onReply?: (msg: IMMessage) => void
  /** 触发撤回 */
  onRecall?: (messageId: string) => void
}

export function MessageItem({
  message,
  senderName,
  replyToMessage,
  onReply,
  onRecall,
}: MessageItemProps) {
  const currentUser = useAuthStore((s) => s.user)
  const isMine = currentUser?.id === message.sender_id
  const isSystem = message.message_type === 'system'

  // 撤回消息
  if (message.is_recalled) {
    return (
      <div className="flex justify-center py-1">
        <span className={`${chatBubble.system} bg-muted text-muted-foreground`}>
          {isMine ? '你' : senderName || '对方'}撤回了一条消息
        </span>
      </div>
    )
  }

  // 系统消息
  if (isSystem) {
    return (
      <div className="flex justify-center py-1">
        <span className={`${chatBubble.system} bg-muted text-muted-foreground`}>
          {message.content}
        </span>
      </div>
    )
  }

  // 是否可以撤回（2 分钟内自己的消息）
  const canRecall =
    isMine &&
    Date.now() - new Date(message.created_at).getTime() < 2 * 60 * 1000

  const displayName = senderName || (isMine ? '我' : '对方')
  const initial = displayName.charAt(0)
  const time = new Date(message.created_at).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className={`flex gap-2 ${isMine ? 'flex-row-reverse' : 'flex-row'} group`}>
      {/* 头像 */}
      {!isMine && (
        <Avatar className="w-8 h-8 shrink-0">
          <AvatarFallback className="text-xs bg-primary/10 text-primary">
            {initial}
          </AvatarFallback>
        </Avatar>
      )}

      {/* 消息体 */}
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div className={`max-w-[70%] ${isMine ? 'items-end' : 'items-start'} flex flex-col`}>
            {/* 发送者名称 + 时间 */}
            {!isMine && (
              <div className="flex items-center gap-1.5 mb-0.5 px-1">
                <span className={heading.micro}>{displayName}</span>
                <span className="text-[10px] text-muted-foreground/60">{time}</span>
              </div>
            )}

            {/* 回复引用 */}
            {replyToMessage && (
              <div className="px-3 py-1 mb-0.5 rounded-lg bg-muted/50 border-l-2 border-primary/30 text-xs text-muted-foreground truncate max-w-full">
                {replyToMessage.is_recalled
                  ? '消息已撤回'
                  : replyToMessage.content.slice(0, 60)}
              </div>
            )}

            {/* 气泡 */}
            <div className={isMine ? chatBubble.user : chatBubble.ai}>
              <MessageContent message={message} />
            </div>

            {/* 自己的消息时间 */}
            {isMine && (
              <span className="text-[10px] text-muted-foreground/60 mt-0.5 px-1">
                {time}
              </span>
            )}
          </div>
        </ContextMenuTrigger>

        <ContextMenuContent>
          {onReply && (
            <ContextMenuItem onClick={() => onReply(message)}>
              <icons.MessageSquare className="w-4 h-4 mr-2" />
              回复
            </ContextMenuItem>
          )}
          {canRecall && onRecall && (
            <ContextMenuItem onClick={() => onRecall(message.id)}>
              <icons.RotateCcw className="w-4 h-4 mr-2" />
              撤回
            </ContextMenuItem>
          )}
          <ContextMenuItem
            onClick={() => navigator.clipboard.writeText(message.content)}
          >
            <icons.Copy className="w-4 h-4 mr-2" />
            复制
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>
    </div>
  )
}

// ===== 消息内容渲染 =====

function MessageContent({ message }: { message: IMMessage }) {
  switch (message.message_type) {
    case 'image':
      return (
        <img
          src={message.metadata_?.url || message.content}
          alt="图片消息"
          className="max-w-[240px] rounded-lg"
        />
      )
    case 'file':
      return (
        <div className="flex items-center gap-2">
          <icons.FileText className="w-5 h-5 shrink-0" />
          <span className="text-sm truncate">
            {message.metadata_?.filename || '文件'}
          </span>
        </div>
      )
    case 'card':
      return (
        <div className="text-sm">
          <div className="font-medium">{message.metadata_?.title || '卡片消息'}</div>
          <div className="text-muted-foreground mt-1">{message.content}</div>
        </div>
      )
    default:
      return <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
  }
}
