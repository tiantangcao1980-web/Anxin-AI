/**
 * ConversationList - IM 对话列表
 *
 * 左侧面板：搜索框 + 对话列表 + 新建对话按钮。
 */

import { useState, useEffect, useCallback } from'react'
import { Avatar, AvatarFallback } from'@/components/ui/avatar'
import { Badge } from'@/components/ui/badge'
import { Button } from'@/components/ui/button'
import { ScrollArea } from'@/components/ui/scroll-area'
import { Skeleton } from'@/components/ui/skeleton'
import { inputStyle, heading, listItem, iconSize, onlineIndicator } from'@/lib/design-tokens'
import { icons } from'@/lib/icons'
import { imApi } from'@/lib/api'
import { useIMStore, useAuthStore, type IMConversation } from'@/lib/store'

interface ConversationListProps {
 onSelect?: (id: string) => void
 onNewConversation?: () => void
}

export function ConversationList({ onSelect, onNewConversation }: ConversationListProps) {
 const [search, setSearch] = useState('')
 const [loading, setLoading] = useState(false)
 const [error, setError] = useState<string | null>(null)

 const conversations = useIMStore((s) => s.conversations)
 const activeId = useIMStore((s) => s.activeConversationId)
 const setConversations = useIMStore((s) => s.setConversations)
 const setActiveConversation = useIMStore((s) => s.setActiveConversation)
 const currentUser = useAuthStore((s) => s.user)

 // 加载对话列表
 const loadConversations = useCallback(async () => {
 setLoading(true)
 setError(null)
 try {
 const res = await imApi.getConversations()
 if (res?.data) {
 setConversations(res.data)
 }
 } catch (err) {
 console.error('[IM] 加载对话列表失败:', err)
 setError('加载对话列表失败')
 } finally {
 setLoading(false)
 }
 }, [setConversations])

 useEffect(() => {
 loadConversations()
 }, [loadConversations])

 // 搜索过滤
 const filtered = search.trim()
 ? conversations.filter((c) => {
 const title = getConversationTitle(c, currentUser?.id)
 return title.toLowerCase().includes(search.toLowerCase())
 })
 : conversations

 const handleSelect = (id: string) => {
 setActiveConversation(id)
 onSelect?.(id)
 }

 return (
 <div className="h-full flex flex-col">
 {/* 顶部标题 + 新建按钮 */}
 <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
 <h2 className={heading.section}>消息</h2>
 <Button
 variant="ghost"
 size="icon"
 className="h-8 w-8"
 onClick={onNewConversation}
 >
 <icons.Edit className={iconSize.md} />
 </Button>
 </div>

 {/* 搜索框 */}
 <div className="px-3 py-2 shrink-0">
 <div className="relative">
 <icons.Search className={`absolute left-2.5 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
 <input
 className={`${inputStyle.search} pl-8`}
 placeholder="搜索对话..."
 value={search}
 onChange={(e) => setSearch(e.target.value)}
 />
 </div>
 </div>

 {/* 对话列表 */}
 <ScrollArea className="flex-1">
 {loading && conversations.length === 0 ? (
 <div className="px-3 py-2 space-y-2">
 {Array.from({ length: 5 }).map((_, i) => (
 <div key={i} className="flex items-center gap-3 px-3 py-2.5">
 <Skeleton className="w-10 h-10 rounded-full shrink-0" />
 <div className="flex-1 space-y-2">
 <Skeleton className="h-4 w-2/3" />
 <Skeleton className="h-3 w-1/2" />
 </div>
 </div>
 ))}
 </div>
 ) : error ? (
 <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
 <icons.AlertTriangle className={`${iconSize.xl} mb-2 text-destructive/60`} />
 <p className="text-sm mb-3">{error}</p>
 <Button variant="outline" size="sm" onClick={loadConversations}>
 <icons.RefreshCw className={`${iconSize.sm} mr-1.5`} />
 重试
 </Button>
 </div>
 ) : filtered.length === 0 ? (
 <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
 <div className="w-14 h-14 rounded-2xl bg-primary/5 flex items-center justify-center mb-3">
 <icons.MessageSquare className={`${iconSize.xl} text-primary/30`} />
 </div>
 <p className="text-sm font-medium">{search ?'未找到匹配对话' :'暂无消息'}</p>
 <p className="text-xs mt-1 text-muted-foreground/60 text-center max-w-[200px]">
 {search ?'请尝试其他关键词' :'点击右上角新建按钮，开始一段对话'}
 </p>
 {!search && (
 <button
 onClick={onNewConversation}
 className="mt-4 flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
 >
 <icons.Add className={iconSize.sm} />
 新建对话
 </button>
 )}
 </div>
 ) : (
 <div className="px-2 py-1 space-y-0.5">
 {filtered.map((conv) => (
 <ConversationItem
 key={conv.id}
 conversation={conv}
 isActive={conv.id === activeId}
 currentUserId={currentUser?.id}
 onClick={() => handleSelect(conv.id)}
 />
 ))}
 </div>
 )}
 </ScrollArea>
 </div>
 )
}

// ===== 单个对话项 =====

function ConversationItem({
 conversation,
 isActive,
 currentUserId,
 onClick,
}: {
 conversation: IMConversation
 isActive: boolean
 currentUserId?: string
 onClick: () => void
}) {
 const title = getConversationTitle(conversation, currentUserId)
 const initial = title.charAt(0)
 const time = conversation.last_message_at
 ? formatRelativeTime(conversation.last_message_at)
 :''

 // 对话类型图标
 const TypeIcon = getConversationTypeIcon(conversation.type)

 return (
 <div
 className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all ${
 isActive ? listItem.active : listItem.base
 }`}
 onClick={onClick}
 >
 {/* 头像 */}
 <div className="relative shrink-0">
 <Avatar className="w-10 h-10">
 <AvatarFallback
 className={`text-sm ${
 conversation.type ==='group'
 ?'bg-warning/10 text-warning'
 : conversation.type ==='case'
 ?'bg-primary/10 text-primary'
 : conversation.type ==='contract'
 ?'bg-success/10 text-success'
 :'bg-primary/10 text-primary'
 }`}
 >
 {TypeIcon ? <TypeIcon className="h-4 w-4" /> : initial}
 </AvatarFallback>
 </Avatar>
 {conversation.type ==='group' && (
 <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-background rounded-full flex items-center justify-center">
 <icons.Users className="w-2.5 h-2.5 text-muted-foreground" />
 </div>
 )}
 </div>

 {/* 中间信息 */}
 <div className="flex-1 min-w-0">
 <div className="flex items-center justify-between">
 <span className={`text-sm truncate ${conversation.unread_count > 0 ?'font-semibold text-foreground' :'font-medium text-foreground'}`}>
 {title}
 </span>
 <span className="text-[10px] text-muted-foreground shrink-0 ml-2">{time}</span>
 </div>
 <p className={`text-xs truncate mt-0.5 ${conversation.unread_count > 0 ?'text-foreground/70' :'text-muted-foreground'}`}>
 {conversation.last_message_preview ||'暂无消息'}
 </p>
 </div>

 {/* 未读数 */}
 {conversation.unread_count > 0 && (
 <Badge
 variant="destructive"
 className="h-5 min-w-5 flex items-center justify-center text-[10px] px-1.5 rounded-full shrink-0"
 >
 {conversation.unread_count > 99 ?'99+' : conversation.unread_count}
 </Badge>
 )}
 </div>
 )
}

function getConversationTypeIcon(type: string): React.ComponentType<React.SVGProps<SVGSVGElement>> | null {
 switch (type) {
 case'case': return icons.Scale
 case'contract': return icons.FileText
 case'group': return null
 default: return null
 }
}

// ===== 工具函数 =====

/**
 * 获取对话显示标题
 * - private 类型：显示对方名称
 * - 其他类型：显示 title 或参与者列表
 */
function getConversationTitle(conv: IMConversation, currentUserId?: string): string {
 if (conv.title) return conv.title

 if (conv.type ==='private' && currentUserId) {
 const other = conv.participants?.find((p) => p.user_id !== currentUserId)
 return other?.nickname || other?.user_id?.slice(0, 8) ||'私聊'
 }

 if (conv.type ==='case') return'案件讨论'
 if (conv.type ==='contract') return'合同讨论'
 return'群聊'
}

/**
 * 格式化相对时间
 */
function formatRelativeTime(isoStr: string): string {
 const date = new Date(isoStr)
 const now = new Date()
 const diffMs = now.getTime() - date.getTime()
 const diffMin = Math.floor(diffMs / 60000)
 const diffHour = Math.floor(diffMs / 3600000)
 const diffDay = Math.floor(diffMs / 86400000)

 if (diffMin < 1) return'刚刚'
 if (diffMin < 60) return `${diffMin}分钟前`
 if (diffHour < 24) return `${diffHour}小时前`
 if (diffDay < 7) return `${diffDay}天前`

 return date.toLocaleDateString('zh-CN', { month:'2-digit', day:'2-digit' })
}
