export type InboxOverviewCounts = {
  tasks: number
  approvals: number
  messages: number
  notifications: number
}

export type InboxOverviewCard = {
  key: keyof InboxOverviewCounts
  label: string
  value: number
  route: string
  tone: string
  icon: string
}

export type InboxQuickAction = {
  key: string
  label: string
  route: string
  icon: string
  tone: string
}

export const inboxQuickActions: InboxQuickAction[] = [
  {
    key: 'tasks',
    label: '任务中心',
    route: '/tasks',
    icon: 'checkbox-outline',
    tone: '#D97706',
  },
  {
    key: 'approvals',
    label: '审批处理',
    route: '/approvals',
    icon: 'git-compare-outline',
    tone: '#7C3AED',
  },
  {
    key: 'chat',
    label: '消息跟进',
    route: '/messages',
    icon: 'chatbubble-ellipses-outline',
    tone: '#2563EB',
  },
  {
    key: 'contracts',
    label: '合同查看',
    route: '/contracts',
    icon: 'document-text-outline',
    tone: '#059669',
  },
]

export function buildInboxOverviewCards(counts: InboxOverviewCounts): InboxOverviewCard[] {
  return [
    {
      key: 'tasks',
      label: '待办任务',
      value: counts.tasks,
      route: '/tasks',
      tone: '#F59E0B',
      icon: 'checkbox-outline',
    },
    {
      key: 'approvals',
      label: '待审批',
      value: counts.approvals,
      route: '/approvals',
      tone: '#8B5CF6',
      icon: 'document-attach-outline',
    },
    {
      key: 'messages',
      label: '未读消息',
      value: counts.messages,
      route: '/messages',
      tone: '#2563EB',
      icon: 'chatbubble-outline',
    },
    {
      key: 'notifications',
      label: '通知提醒',
      value: counts.notifications,
      route: '/notifications',
      tone: '#10B981',
      icon: 'notifications-outline',
    },
  ]
}
