import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
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

export default function NotificationsScreen() {
  const [filter, setFilter] = useState<(typeof filters)[number]['key']>('all')
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadNotifications = useCallback(async () => {
    try {
      setError(null)
      const result = await api.get<{ data: NotificationItem[]; total: number }>(
        '/notifications/?limit=50',
      )
      setNotifications(result.data ?? [])
    } catch (err: any) {
      setNotifications([])
      setError(err?.message || '加载通知失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadNotifications()
  }, [loadNotifications])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadNotifications()
  }, [loadNotifications])

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

      {loading && notifications.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
      <FlatList
        data={visibleNotifications}
        keyExtractor={(item) => item.id}
        contentContainerStyle={
          visibleNotifications.length === 0 ? styles.emptyContainer : styles.listContent
        }
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={Colors.primary}
          />
        }
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
          error ? (
            <View style={styles.emptyState}>
              <Ionicons name="cloud-offline-outline" size={48} color="#DC2626" />
              <Text style={[styles.emptyTitle, { color: '#DC2626' }]}>{error}</Text>
              <TouchableOpacity style={styles.retryBtn} onPress={loadNotifications}>
                <Text style={styles.retryBtnText}>点击重试</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.emptyState}>
              <Ionicons name="notifications-off-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyTitle}>暂无通知</Text>
              <Text style={styles.emptyText}>下拉可刷新。</Text>
            </View>
          )
        }
      />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  emptyContainer: { flex: 1 },
  retryBtn: {
    marginTop: Layout.spacing.md,
    paddingHorizontal: Layout.spacing.lg,
    paddingVertical: Layout.spacing.sm,
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.md,
  },
  retryBtnText: {
    fontSize: Layout.fontSize.sm,
    color: Colors.white,
    fontWeight: '500',
  },
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
