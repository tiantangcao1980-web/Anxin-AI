import type { NotificationItem } from '@/types/api'

export function normalizeBadgeCount(count: number): number | string | undefined {
  if (!count || count <= 0) {
    return undefined
  }

  if (count > 99) {
    return '99+'
  }

  return count
}

export function getNotificationTargetRoute(notification: Pick<NotificationItem, 'event_type'>): string {
  switch (notification.event_type) {
    case 'approval':
      return '/approvals'
    case 'chat':
      return '/messages'
    case 'contract':
      return '/contracts'
    default:
      return '/notifications'
  }
}
