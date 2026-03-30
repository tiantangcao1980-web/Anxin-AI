/**
 * NotificationList - 通知列表组件
 *
 * 支持分类筛选（全部/未读/审批/案件/系统/合同），
 * 按日期分组显示，全部已读、删除、点击查看详情。
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { heading, iconSize, statusBadge, listItem } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import { notificationsApi } from '@/lib/api'
import { useNotificationStore, type NotificationItem } from '@/lib/store'
import { toast } from 'sonner'

const FILTER_TABS = [
  { key: 'all' as const, label: '全部' },
  { key: 'unread' as const, label: '未读' },
  { key: 'approval' as const, label: '审批' },
  { key: 'case' as const, label: '案件' },
  { key: 'contract' as const, label: '合同' },
  { key: 'system' as const, label: '系统' },
]

interface NotificationListProps {
  onSelect?: (item: NotificationItem) => void
  selectedId?: string | null
}

export function NotificationList({ onSelect, selectedId }: NotificationListProps = {}) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const notifications = useNotificationStore((s) => s.notifications)
  const filter = useNotificationStore((s) => s.notificationFilter)
  const unreadCount = useNotificationStore((s) => s.unreadCount)
  const setNotifications = useNotificationStore((s) => s.setNotifications)
  const setFilter = useNotificationStore((s) => s.setNotificationFilter)
  const markNotificationRead = useNotificationStore((s) => s.markNotificationRead)
  const markAllNotificationsRead = useNotificationStore((s) => s.markAllNotificationsRead)
  const removeNotification = useNotificationStore((s) => s.removeNotification)

  const loadNotifications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, any> = { limit: 100 }
      if (filter === 'unread') params.unread_only = true
      else if (filter !== 'all') params.event_type = filter

      const res = await notificationsApi.list(params)
      if (res?.data) {
        setNotifications(res.data as NotificationItem[])
      }
    } catch {
      setError('加载通知失败')
    } finally {
      setLoading(false)
    }
  }, [filter, setNotifications])

  useEffect(() => {
    loadNotifications()
  }, [loadNotifications])

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllAsRead()
      markAllNotificationsRead()
      toast.success('已全部标记为已读')
    } catch {
      toast.error('操作失败')
    }
  }

  const handleRead = async (item: NotificationItem) => {
    if (!item.is_read) {
      try {
        await notificationsApi.markAsRead(item.id)
        markNotificationRead(item.id)
      } catch {
        /* 静默处理 */
      }
    }
    if (onSelect) {
      onSelect(item)
    } else if (item.related_link) {
      navigate(item.related_link)
    }
  }

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    try {
      await notificationsApi.delete(id)
      removeNotification(id)
    } catch {
      toast.error('删除失败')
    }
  }

  // 按日期分组
  const grouped = groupByDate(notifications)

  return (
    <div className="h-full flex flex-col">
      {/* 顶部标题 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <h2 className={heading.section}>通知</h2>
          {unreadCount > 0 && (
            <Badge variant="destructive" className="h-5 min-w-5 px-1.5 text-[10px] rounded-full">
              {unreadCount}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" className="text-xs h-7" onClick={handleMarkAllRead}>
              <icons.CheckCheck className={`${iconSize.sm} mr-1`} />
              全部已读
            </Button>
          )}
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={loadNotifications} title="刷新">
            <icons.RefreshCw className={`${iconSize.sm} ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* 筛选标签 */}
      <div className="flex items-center gap-1 px-3 py-2 border-b border-border shrink-0 overflow-x-auto no-scrollbar">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              filter === tab.key
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 通知列表 */}
      <ScrollArea className="flex-1">
        {loading && notifications.length === 0 ? (
          <div className="px-3 py-2 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3 px-3 py-3">
                <Skeleton className="w-9 h-9 rounded-lg shrink-0" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <icons.AlertTriangle className={`${iconSize.xl} mb-2 text-destructive/60`} />
            <p className="text-sm mb-3">{error}</p>
            <Button variant="outline" size="sm" onClick={loadNotifications}>
              <icons.RefreshCw className={`${iconSize.sm} mr-1.5`} />
              重试
            </Button>
          </div>
        ) : notifications.length === 0 ? (
          <EmptyNotification filter={filter} />
        ) : (
          <div className="py-1">
            {grouped.map(({ label, items }) => (
              <div key={label}>
                <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm px-4 py-1.5">
                  <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                    {label}
                  </span>
                </div>
                <div className="px-2 space-y-0.5">
                  {items.map((item) => (
                    <NotificationRow
                      key={item.id}
                      item={item}
                      isSelected={item.id === selectedId}
                      onClick={() => handleRead(item)}
                      onDelete={(e) => handleDelete(e, item.id)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}

// ===== 空状态 =====

function EmptyNotification({ filter }: { filter: string }) {
  const msgMap: Record<string, { icon: typeof icons.Notification; title: string; desc: string }> = {
    all: { icon: icons.Notification, title: '暂无通知', desc: '有新动态时，通知将显示在这里' },
    unread: { icon: icons.CheckCheck, title: '全部已读', desc: '您已处理所有未读通知' },
    approval: { icon: icons.ClipboardCheck, title: '暂无审批通知', desc: '待审批事项会出现在这里' },
    case: { icon: icons.Cases, title: '暂无案件通知', desc: '案件相关动态会出现在这里' },
    contract: { icon: icons.Contracts, title: '暂无合同通知', desc: '合同相关动态会出现在这里' },
    system: { icon: icons.Settings, title: '暂无系统通知', desc: '系统公告会出现在这里' },
  }

  const config = msgMap[filter] || msgMap.all
  const Icon = config.icon

  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
      <div className="w-14 h-14 rounded-2xl bg-primary/5 flex items-center justify-center mb-3">
        <Icon className={`${iconSize.xl} text-primary/30`} />
      </div>
      <p className="text-sm font-medium">{config.title}</p>
      <p className="text-xs mt-1 text-muted-foreground/60 text-center max-w-[200px]">{config.desc}</p>
    </div>
  )
}

// ===== 日期分组 =====

function groupByDate(items: NotificationItem[]) {
  const groups: { label: string; items: NotificationItem[] }[] = []
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const weekAgo = new Date(today.getTime() - 7 * 86400000)

  const buckets: Record<string, NotificationItem[]> = {}

  for (const item of items) {
    const date = new Date(item.created_at)
    let key: string

    if (date >= today) key = '今天'
    else if (date >= yesterday) key = '昨天'
    else if (date >= weekAgo) key = '本周'
    else key = '更早'

    if (!buckets[key]) buckets[key] = []
    buckets[key].push(item)
  }

  const order = ['今天', '昨天', '本周', '更早']
  for (const label of order) {
    if (buckets[label]?.length) {
      groups.push({ label, items: buckets[label] })
    }
  }
  return groups
}

// ===== 通知类型图标与颜色映射 =====

function getNotificationMeta(item: NotificationItem) {
  const eventType = item.event_type || 'system'
  const type = item.type

  const iconMap: Record<string, typeof icons.Notification> = {
    approval: icons.ClipboardCheck,
    case: icons.Cases,
    contract: icons.Contracts,
    chat: icons.Chat,
    lawyer: icons.Experts,
    system: icons.Notification,
  }

  const colorMap: Record<string, string> = {
    urgent: 'bg-red-100 text-red-600 dark:bg-red-950/40 dark:text-red-400',
    warning: 'bg-amber-100 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400',
    success: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400',
    info: 'bg-primary/10 text-primary',
  }

  const badgeMap: Record<string, { label: string; style: string }> = {
    approval: { label: '审批', style: statusBadge.warning },
    case: { label: '案件', style: statusBadge.info },
    contract: { label: '合同', style: statusBadge.info },
    chat: { label: '消息', style: statusBadge.neutral },
    lawyer: { label: '律师', style: statusBadge.success },
    system: { label: '系统', style: statusBadge.neutral },
  }

  return {
    Icon: iconMap[eventType] || icons.Notification,
    iconColor: colorMap[type] || colorMap.info,
    badge: badgeMap[eventType] || badgeMap.system,
  }
}

// ===== 单条通知 =====

function NotificationRow({
  item,
  isSelected,
  onClick,
  onDelete,
}: {
  item: NotificationItem
  isSelected?: boolean
  onClick: () => void
  onDelete: (e: React.MouseEvent) => void
}) {
  const { Icon, iconColor, badge } = getNotificationMeta(item)
  const timeStr = formatNotificationTime(item.created_at)

  return (
    <div
      className={`flex items-start gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all group ${
        isSelected
          ? listItem.active
          : item.is_read
            ? listItem.base
            : 'bg-primary/[0.03] hover:bg-primary/[0.06] border border-primary/5'
      }`}
      onClick={onClick}
    >
      {/* 未读指示点 */}
      <div className="flex flex-col items-center pt-1">
        {!item.is_read && (
          <div className="w-2 h-2 rounded-full bg-primary mb-1" />
        )}
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${iconColor}`}>
          <Icon className={iconSize.sm} />
        </div>
      </div>

      {/* 内容 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-sm truncate ${item.is_read ? 'text-foreground' : 'font-semibold text-foreground'}`}>
            {item.title}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-md whitespace-nowrap shrink-0 ${badge.style}`}>
            {badge.label}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{item.message}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[10px] text-muted-foreground/60">{timeStr}</span>
          {item.related_link && (
            <span className="text-[10px] text-primary/60 flex items-center gap-0.5">
              <icons.ExternalLink className="w-2.5 h-2.5" />
              详情
            </span>
          )}
        </div>
      </div>

      {/* 删除按钮 */}
      <button
        onClick={onDelete}
        className="p-1 rounded-md text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors opacity-0 group-hover:opacity-100 shrink-0 mt-0.5"
        title="删除"
      >
        <icons.Close className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

// ===== 时间格式化 =====

function formatNotificationTime(isoStr: string): string {
  const date = new Date(isoStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  if (diffHour < 24) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  if (diffDay < 7) return `${diffDay}天前`

  const isThisYear = date.getFullYear() === now.getFullYear()
  if (isThisYear) {
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
