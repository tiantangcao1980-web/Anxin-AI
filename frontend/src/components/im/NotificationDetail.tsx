/**
 * NotificationDetail - 通知详情面板
 *
 * 显示在右侧面板，展示选中通知的详细内容，
 * 包括操作按钮、跳转链接、时间信息等。
 */

import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { heading, iconSize, statusBadge, cardStyle } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import { notificationsApi } from '@/lib/api'
import { useNotificationStore, type NotificationItem } from '@/lib/store'
import { toast } from 'sonner'

interface NotificationDetailProps {
  notification: NotificationItem
  onBack?: () => void
  onDeleted?: () => void
}

export function NotificationDetail({ notification, onBack, onDeleted }: NotificationDetailProps) {
  const navigate = useNavigate()
  const removeNotification = useNotificationStore((s) => s.removeNotification)
  const markNotificationRead = useNotificationStore((s) => s.markNotificationRead)

  const meta = getNotificationMeta(notification)
  const Icon = meta.Icon
  const timeStr = formatDetailTime(notification.created_at)

  const handleDelete = async () => {
    try {
      await notificationsApi.delete(notification.id)
      removeNotification(notification.id)
      onDeleted?.()
      toast.success('通知已删除')
    } catch {
      toast.error('删除失败')
    }
  }

  const handleMarkRead = async () => {
    if (notification.is_read) return
    try {
      await notificationsApi.markAsRead(notification.id)
      markNotificationRead(notification.id)
    } catch {
      /* 静默 */
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部 */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
        {onBack && (
          <Button variant="ghost" size="icon" className="h-8 w-8 lg:hidden" onClick={onBack}>
            <icons.ChevronLeft className={iconSize.md} />
          </Button>
        )}
        <div className="flex-1 min-w-0">
          <h3 className={`${heading.card} truncate`}>通知详情</h3>
        </div>
        <div className="flex items-center gap-1">
          {!notification.is_read && (
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleMarkRead}>
              <icons.Check className={`${iconSize.sm} mr-1`} />
              标为已读
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={handleDelete}
            title="删除"
          >
            <icons.Delete className={iconSize.sm} />
          </Button>
        </div>
      </div>

      {/* 内容 */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-lg mx-auto space-y-6">
          {/* 图标和标题 */}
          <div className="flex items-start gap-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${meta.iconColor}`}>
              <Icon className={iconSize.lg} />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-base font-semibold text-foreground">{notification.title}</h2>
              <div className="flex items-center gap-2 mt-1.5">
                <span className={`text-[10px] px-1.5 py-0.5 rounded-md ${meta.badge.style}`}>
                  {meta.badge.label}
                </span>
                <TypeBadge type={notification.type} />
                <span className="text-xs text-muted-foreground">{timeStr}</span>
              </div>
            </div>
          </div>

          {/* 消息正文 */}
          <div className={cardStyle.base}>
            <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
              {notification.message}
            </p>
          </div>

          {/* 操作区域 */}
          <div className="space-y-2">
            {notification.related_link && (
              <Button
                className="w-full"
                onClick={() => navigate(notification.related_link!)}
              >
                <icons.ExternalLink className={`${iconSize.sm} mr-2`} />
                查看关联内容
              </Button>
            )}

            {/* 审批类型通知显示快捷操作 */}
            {notification.event_type === 'approval' && notification.related_link && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => navigate(notification.related_link!)}
                >
                  <icons.Eye className={`${iconSize.sm} mr-1.5`} />
                  查看审批
                </Button>
              </div>
            )}
          </div>

          {/* 时间详情 */}
          <div className="pt-4 border-t border-border space-y-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <icons.Clock className="w-3.5 h-3.5 shrink-0" />
              <span>通知时间：{new Date(notification.created_at).toLocaleString('zh-CN')}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <icons.Tag className="w-3.5 h-3.5 shrink-0" />
              <span>事件类型：{getEventTypeLabel(notification.event_type)}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {notification.is_read ? (
                <>
                  <icons.CheckCircle className="w-3.5 h-3.5 shrink-0 text-emerald-500" />
                  <span>已读</span>
                </>
              ) : (
                <>
                  <icons.AlertCircle className="w-3.5 h-3.5 shrink-0 text-primary" />
                  <span>未读</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ===== 紧急程度标签 =====

function TypeBadge({ type }: { type: string }) {
  const map: Record<string, { label: string; className: string }> = {
    urgent: { label: '紧急', className: 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400' },
    warning: { label: '警告', className: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400' },
    success: { label: '成功', className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400' },
    info: { label: '信息', className: 'bg-primary/10 text-primary' },
  }
  const config = map[type] || map.info
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-md font-medium ${config.className}`}>
      {config.label}
    </span>
  )
}

// ===== 事件类型标签 =====

function getEventTypeLabel(eventType?: string): string {
  const map: Record<string, string> = {
    approval: '审批流程',
    case: '案件动态',
    contract: '合同管理',
    chat: '即时通讯',
    lawyer: '律师服务',
    system: '系统通知',
  }
  return eventType ? map[eventType] || eventType : '未分类'
}

// ===== 通知类型元数据 =====

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

function formatDetailTime(isoStr: string): string {
  const date = new Date(isoStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMs / 3600000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  if (diffHour < 24) return `${diffHour}小时前`

  return date.toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
