import { useEffect, useMemo, useState } from 'react'
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'
import type { NotificationItem } from '@/types/api'

const filters = [
  { key: 'all', label: '全部' },
  { key: 'unread', label: '未读' },
] as const

const fallbackNotifications: NotificationItem[] = [
  {
    id: 'n1',
    type: 'warning',
    title: '审批即将超时',
    message: '合同用印审批距离 SLA 还有 2 小时。',
    is_read: false,
    event_type: 'approval',
    created_at: '刚刚',
  },
  {
    id: 'n2',
    type: 'info',
    title: '有新的协作消息',
    message: '并购项目群有 2 条新消息等待处理。',
    is_read: false,
    event_type: 'chat',
    created_at: '10 分钟前',
  },
]

export default function NotificationsScreen() {
  const [filter, setFilter] = useState<(typeof filters)[number]['key']>('all')
  const [notifications, setNotifications] = useState<NotificationItem[]>(fallbackNotifications)

  useEffect(() => {
    const loadNotifications = async () => {
      try {
        const result = await api.get<{ data: NotificationItem[]; total: number }>('/notifications/?limit=30')
        if (result.data.length > 0) {
          setNotifications(result.data)
        }
      } catch {
        setNotifications(fallbackNotifications)
      }
    }

    loadNotifications()
  }, [])

  const visibleNotifications = useMemo(
    () => notifications.filter((item) => (filter === 'unread' ? !item.is_read : true)),
    [filter, notifications]
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '通知中心' }} />
      <View style={styles.filterRow}>
        {filters.map((item) => (
          <TouchableOpacity
            key={item.key}
            style={[styles.filterChip, filter === item.key && styles.filterChipActive]}
            onPress={() => setFilter(item.key)}
            activeOpacity={0.8}
          >
            <Text style={[styles.filterText, filter === item.key && styles.filterTextActive]}>
              {item.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={visibleNotifications}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            activeOpacity={0.8}
            onPress={() =>
              router.push({
                pathname: '/notifications/[id]',
                params: {
                  id: item.id,
                  title: item.title,
                  message: item.message,
                  event_type: item.event_type,
                  created_at: item.created_at,
                  is_read: item.is_read ? '1' : '0',
                },
              })
            }
          >
            <View style={[styles.iconWrap, !item.is_read && styles.iconWrapUnread]}>
              <Ionicons name="notifications-outline" size={18} color={item.is_read ? Colors.textMuted : Colors.primary} />
            </View>
            <View style={styles.cardBody}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle} numberOfLines={1}>{item.title}</Text>
                <Text style={styles.cardTime}>{item.created_at}</Text>
              </View>
              <Text style={styles.cardMessage} numberOfLines={2}>{item.message}</Text>
            </View>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="notifications-off-outline" size={48} color={Colors.textMuted} />
            <Text style={styles.emptyTitle}>暂无通知</Text>
            <Text style={styles.emptyText}>你处理过的通知会显示在这里。</Text>
          </View>
        }
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  filterRow: {
    flexDirection: 'row',
    gap: Layout.spacing.sm,
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.md,
  },
  filterChip: {
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
  },
  filterChipActive: {
    backgroundColor: Colors.primary,
  },
  filterText: {
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    fontWeight: '500',
  },
  filterTextActive: {
    color: Colors.white,
  },
  listContent: {
    padding: Layout.spacing.md,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
    flexDirection: 'row',
    gap: Layout.spacing.sm,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrapUnread: {
    backgroundColor: Colors.primary + '15',
  },
  cardBody: {
    flex: 1,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: Layout.spacing.sm,
  },
  cardTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: Layout.fontSize.md,
    fontWeight: '600',
  },
  cardTime: {
    color: Colors.textMuted,
    fontSize: Layout.fontSize.xs,
  },
  cardMessage: {
    marginTop: Layout.spacing.xs,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    lineHeight: 20,
  },
  emptyState: {
    alignItems: 'center',
    marginTop: Layout.spacing.xl,
  },
  emptyTitle: {
    marginTop: Layout.spacing.md,
    color: Colors.text,
    fontSize: Layout.fontSize.md,
    fontWeight: '600',
  },
  emptyText: {
    marginTop: Layout.spacing.xs,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    textAlign: 'center',
  },
})
