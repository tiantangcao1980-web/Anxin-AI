import { useCallback, useEffect, useState } from 'react'
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
import { normalizeBadgeCount } from '@/features/inbox/engagement-model'
import { api } from '@/services/api'
import type { IMConversation } from '@/types/api'

export default function MessagesScreen() {
  const [conversations, setConversations] = useState<IMConversation[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadConversations = useCallback(async () => {
    try {
      setError(null)
      const result = await api.get<IMConversation[]>('/im/conversations')
      setConversations(result ?? [])
    } catch (err: any) {
      setConversations([])
      setError(err?.message || '加载会话失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadConversations()
  }, [loadConversations])

  if (loading && conversations.length === 0) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <Stack.Screen options={{ title: '消息中心' }} />
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '消息中心' }} />
      <FlatList
        data={conversations}
        keyExtractor={(item) => item.id}
        contentContainerStyle={
          conversations.length === 0 ? styles.emptyContainer : styles.listContent
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
                pathname: '/messages/[id]',
                params: {
                  id: item.id,
                  title: item.title || '未命名会话',
                },
              })
            }
          >
            <View style={styles.avatar}>
              <Ionicons name="chatbubble-ellipses-outline" size={18} color={Colors.primary} />
            </View>
            <View style={styles.cardBody}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle} numberOfLines={1}>
                  {item.title || '未命名会话'}
                </Text>
                <Text style={styles.cardTime}>{item.last_message_at || '刚刚'}</Text>
              </View>
              <Text style={styles.cardPreview} numberOfLines={2}>
                {item.last_message_preview || '暂无消息内容'}
              </Text>
            </View>
            {normalizeBadgeCount(item.unread_count) ? (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{normalizeBadgeCount(item.unread_count)}</Text>
              </View>
            ) : null}
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          error ? (
            <View style={styles.emptyState}>
              <Ionicons name="cloud-offline-outline" size={48} color="#DC2626" />
              <Text style={[styles.emptyTitle, { color: '#DC2626' }]}>{error}</Text>
              <TouchableOpacity style={styles.retryBtn} onPress={loadConversations}>
                <Text style={styles.retryBtnText}>点击重试</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.emptyState}>
              <Ionicons name="mail-open-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyTitle}>暂无消息会话</Text>
              <Text style={styles.emptyText}>下拉可刷新；新消息会立刻推送到这里。</Text>
            </View>
          )
        }
      />
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
  listContent: {
    padding: Layout.spacing.md,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
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
  cardPreview: {
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    marginTop: Layout.spacing.xs,
    lineHeight: 20,
  },
  badge: {
    minWidth: 24,
    paddingHorizontal: Layout.spacing.xs,
    height: 24,
    borderRadius: 12,
    backgroundColor: Colors.error,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    color: Colors.white,
    fontSize: Layout.fontSize.xs,
    fontWeight: '700',
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
