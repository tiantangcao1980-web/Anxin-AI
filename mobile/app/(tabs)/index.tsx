import { useEffect, useMemo, useState } from 'react'
import type { ComponentProps } from 'react'
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  SafeAreaView,
} from 'react-native'
import { router } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { api } from '@/services/api'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { getNotificationTargetRoute } from '@/features/inbox/engagement-model'
import { buildInboxOverviewCards, inboxQuickActions } from '@/features/inbox/model'
import type { ApprovalItem, NotificationItem, TaskItem } from '@/types/api'

type ConversationItem = {
  id: string
  unread_count?: number
}

type IoniconsName = ComponentProps<typeof Ionicons>['name']

function EmptySection({
  icon,
  title,
  description,
}: {
  icon: IoniconsName
  title: string
  description: string
}) {
  return (
    <View style={styles.emptyCard}>
      <Ionicons name={icon} size={24} color={Colors.textMuted} />
      <View style={styles.emptyTextGroup}>
        <Text style={styles.emptyTitle}>{title}</Text>
        <Text style={styles.emptyDescription}>{description}</Text>
      </View>
    </View>
  )
}

export default function HomeScreen() {
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [approvals, setApprovals] = useState<ApprovalItem[]>([])
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [counts, setCounts] = useState({
    tasks: 0,
    approvals: 0,
    messages: 0,
    notifications: 0,
  })
  const [loadError, setLoadError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    loadInbox()
  }, [])

  const loadInbox = async () => {
    try {
      const [taskResult, approvalResult, notificationResult, unreadCountResult, conversationResult] = await Promise.allSettled([
        api.get<{ items: TaskItem[]; total: number }>('/tasks/?status=todo&page_size=3'),
        api.get<{ items: ApprovalItem[]; total: number }>('/approvals?status=pending&page_size=3'),
        api.get<{ data: NotificationItem[]; total: number }>('/notifications/?limit=3&unread_only=true'),
        api.get<{ count: number }>('/notifications/unread-count'),
        api.get<ConversationItem[]>('/im/conversations'),
      ])

      const nextTasks = taskResult.status === 'fulfilled'
        ? taskResult.value.items ?? []
        : []
      const nextApprovals = approvalResult.status === 'fulfilled'
        ? approvalResult.value.items ?? []
        : []
      const nextNotifications = notificationResult.status === 'fulfilled'
        ? notificationResult.value.data ?? []
        : []
      const unreadMessages = conversationResult.status === 'fulfilled'
        ? conversationResult.value.reduce((sum, item) => sum + (item.unread_count ?? 0), 0)
        : 0
      const unreadNotifications = unreadCountResult.status === 'fulfilled'
        ? unreadCountResult.value.count
        : nextNotifications.filter((notification) => !notification.is_read).length
      const hasPartialFailure = [
        taskResult,
        approvalResult,
        notificationResult,
        unreadCountResult,
        conversationResult,
      ].some((result) => result.status === 'rejected')

      setTasks(nextTasks)
      setApprovals(nextApprovals)
      setNotifications(nextNotifications)
      setCounts({
        tasks: taskResult.status === 'fulfilled' ? taskResult.value.total ?? nextTasks.length : 0,
        approvals: approvalResult.status === 'fulfilled' ? approvalResult.value.total ?? nextApprovals.length : 0,
        messages: unreadMessages,
        notifications: unreadNotifications,
      })
      setLoadError(hasPartialFailure ? '部分数据加载失败，下拉可重试。' : null)
    } finally {
      setRefreshing(false)
    }
  }

  const overviewCards = useMemo(() => buildInboxOverviewCards(counts), [counts])

  const handleRefresh = () => {
    setRefreshing(true)
    loadInbox()
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor={Colors.primary}
            />
          }
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.heroCard}>
            <Text style={styles.heroEyebrow}>移动工作台</Text>
            <Text style={styles.heroTitle}>收件箱</Text>
            <Text style={styles.heroDescription}>集中处理任务、审批、消息和通知，优先完成今天最重要的待办。</Text>
          </View>

          <View style={styles.overviewGrid}>
            {overviewCards.map((card) => (
              <TouchableOpacity
                key={card.key}
                style={styles.overviewCard}
                onPress={() => router.push(card.route as any)}
                activeOpacity={0.8}
              >
                <View style={[styles.overviewIcon, { backgroundColor: `${card.tone}15` }]}>
                  <Ionicons name={card.icon as any} size={20} color={card.tone} />
                </View>
                <Text style={styles.overviewValue}>{card.value}</Text>
                <Text style={styles.overviewLabel}>{card.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.sectionTitle}>快捷入口</Text>
          <View style={styles.quickGrid}>
            {inboxQuickActions.map((action) => (
              <TouchableOpacity
                key={action.key}
                style={styles.quickItem}
                onPress={() => router.push(action.route as any)}
                activeOpacity={0.8}
              >
                <View style={[styles.quickIcon, { backgroundColor: `${action.tone}15` }]}>
                  <Ionicons name={action.icon as any} size={24} color={action.tone} />
                </View>
                <Text style={styles.quickLabel}>{action.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.sectionTitle}>待办任务</Text>
          {tasks.length === 0 ? (
            <EmptySection
              icon="checkbox-outline"
              title="暂无待办任务"
              description={loadError ?? '下拉可刷新。'}
            />
          ) : (
            tasks.map((task) => {
              const tags = task.tags ?? []
              return (
                <TouchableOpacity
                  key={task.id}
                  style={styles.listCard}
                  onPress={() =>
                    router.push({
                      pathname: '/tasks/[id]',
                      params: {
                        id: task.id,
                        title: task.title,
                        description: task.description,
                        status: task.status,
                        priority: task.priority,
                        dueDate: task.dueDate,
                        tags: tags.join('|'),
                      },
                    })
                  }
                  activeOpacity={0.8}
                >
                  <View style={styles.listHeader}>
                    <Text style={styles.listTitle} numberOfLines={1}>{task.title}</Text>
                    <View style={[styles.badge, task.priority === 'high' ? styles.badgeHigh : task.priority === 'medium' ? styles.badgeMedium : styles.badgeLow]}>
                      <Text style={styles.badgeText}>
                        {task.priority === 'high' ? '高优先级' : task.priority === 'medium' ? '中优先级' : '低优先级'}
                      </Text>
                    </View>
                  </View>
                  <Text style={styles.listMeta}>
                    {tags.join(' · ') || '待处理任务'}{task.dueDate ? ` · 截止 ${task.dueDate}` : ''}
                  </Text>
                </TouchableOpacity>
              )
            })
          )}

          <Text style={styles.sectionTitle}>待审批</Text>
          {approvals.length === 0 ? (
            <EmptySection
              icon="git-compare-outline"
              title="暂无待审批"
              description={loadError ?? '下拉可刷新。'}
            />
          ) : (
            approvals.map((approval) => (
              <TouchableOpacity
                key={approval.id}
                style={styles.listCard}
                onPress={() =>
                  router.push({
                    pathname: '/approvals/[id]',
                    params: {
                      id: approval.id,
                      title: approval.title,
                      type: approval.type,
                      status: approval.status,
                      description: approval.description,
                    },
                  })
                }
                activeOpacity={0.8}
              >
                <View style={styles.listHeader}>
                  <Text style={styles.listTitle} numberOfLines={1}>{approval.title}</Text>
                  <View style={styles.badgeNeutral}>
                    <Text style={styles.badgeNeutralText}>{approval.type}</Text>
                  </View>
                </View>
                <Text style={styles.listMeta}>
                  {approval.status === 'pending' ? '等待你处理' : approval.status}
                  {approval.created_at ? ` · ${approval.created_at}` : ''}
                </Text>
              </TouchableOpacity>
            ))
          )}

          <Text style={styles.sectionTitle}>最新通知</Text>
          {notifications.length === 0 ? (
            <EmptySection
              icon="notifications-outline"
              title="暂无新通知"
              description={loadError ?? '下拉可刷新。'}
            />
          ) : (
            notifications.map((notification) => (
              <TouchableOpacity
                key={notification.id}
                style={styles.notificationCard}
                onPress={() =>
                  router.push({
                    pathname: '/notifications/[id]',
                    params: {
                      id: notification.id,
                      title: notification.title,
                      message: notification.message,
                      event_type: notification.event_type,
                      created_at: notification.created_at,
                      is_read: notification.is_read ? '1' : '0',
                      target: getNotificationTargetRoute(notification),
                    },
                  })
                }
                activeOpacity={0.8}
              >
                <Text style={styles.notificationTitle}>{notification.title}</Text>
                <Text style={styles.notificationMessage} numberOfLines={2}>{notification.message}</Text>
                <Text style={styles.notificationTime}>{notification.created_at}</Text>
              </TouchableOpacity>
            ))
          )}
        </ScrollView>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scrollContent: {
    paddingHorizontal: Layout.spacing.md,
    paddingBottom: Layout.spacing.xl,
  },
  heroCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.lg,
    padding: Layout.spacing.lg,
    marginTop: Layout.spacing.md,
  },
  heroEyebrow: {
    fontSize: Layout.fontSize.xs,
    color: Colors.primary,
    fontWeight: '600',
    marginBottom: Layout.spacing.xs,
  },
  heroTitle: {
    fontSize: Layout.fontSize.xxl,
    color: Colors.text,
    fontWeight: '700',
  },
  heroDescription: {
    marginTop: Layout.spacing.sm,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    lineHeight: 20,
  },
  overviewGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginTop: Layout.spacing.md,
  },
  overviewCard: {
    width: '48%',
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  overviewIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  overviewValue: {
    fontSize: Layout.fontSize.xl,
    color: Colors.text,
    fontWeight: '700',
    marginTop: Layout.spacing.md,
  },
  overviewLabel: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    marginTop: Layout.spacing.xs,
  },
  sectionTitle: {
    fontSize: Layout.fontSize.lg,
    fontWeight: '700',
    color: Colors.text,
    marginTop: Layout.spacing.lg,
    marginBottom: Layout.spacing.md,
  },
  quickGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  quickItem: {
    width: '23%',
    alignItems: 'center',
    paddingVertical: Layout.spacing.sm,
  },
  quickIcon: {
    width: 56,
    height: 56,
    borderRadius: Layout.borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickLabel: {
    fontSize: Layout.fontSize.xs,
    color: Colors.text,
    textAlign: 'center',
    marginTop: Layout.spacing.sm,
  },
  listCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  emptyCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  emptyTextGroup: {
    flex: 1,
  },
  emptyTitle: {
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    fontWeight: '600',
  },
  emptyDescription: {
    marginTop: 2,
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
  },
  listHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: Layout.spacing.sm,
  },
  listTitle: {
    flex: 1,
    fontSize: Layout.fontSize.md,
    fontWeight: '600',
    color: Colors.text,
  },
  listMeta: {
    marginTop: Layout.spacing.xs,
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
  },
  badge: {
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 4,
    borderRadius: Layout.borderRadius.sm,
  },
  badgeHigh: {
    backgroundColor: '#FEE2E2',
  },
  badgeMedium: {
    backgroundColor: '#FEF3C7',
  },
  badgeLow: {
    backgroundColor: '#DCFCE7',
  },
  badgeText: {
    fontSize: Layout.fontSize.xs,
    color: Colors.text,
    fontWeight: '600',
  },
  badgeNeutral: {
    backgroundColor: Colors.primary + '15',
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 4,
    borderRadius: Layout.borderRadius.sm,
  },
  badgeNeutralText: {
    color: Colors.primary,
    fontSize: Layout.fontSize.xs,
    fontWeight: '600',
  },
  notificationCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  notificationTitle: {
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    fontWeight: '600',
  },
  notificationMessage: {
    marginTop: Layout.spacing.xs,
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    lineHeight: 20,
  },
  notificationTime: {
    marginTop: Layout.spacing.sm,
    fontSize: Layout.fontSize.xs,
    color: Colors.textMuted,
  },
})
