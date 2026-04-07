import { useEffect, useState } from 'react'
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { normalizeBadgeCount } from '@/features/inbox/engagement-model'
import { api } from '@/services/api'
import type { IMConversation } from '@/types/api'

const fallbackConversations: IMConversation[] = [
  {
    id: 'conv-1',
    type: 'group',
    title: '并购项目群',
    unread_count: 2,
    last_message_preview: '请确认尽调清单的最新版本。',
    last_message_at: '刚刚',
    participants: [],
    created_at: new Date().toISOString(),
  },
  {
    id: 'conv-2',
    type: 'private',
    title: '法务顾问',
    unread_count: 0,
    last_message_preview: '合同修订意见已经同步。',
    last_message_at: '今天 09:20',
    participants: [],
    created_at: new Date().toISOString(),
  },
]

export default function MessagesScreen() {
  const [conversations, setConversations] = useState<IMConversation[]>(fallbackConversations)

  useEffect(() => {
    const loadConversations = async () => {
      try {
        const result = await api.get<IMConversation[]>('/im/conversations')
        if (result.length > 0) {
          setConversations(result)
        }
      } catch {
        setConversations(fallbackConversations)
      }
    }

    loadConversations()
  }, [])

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '消息中心' }} />
      <FlatList
        data={conversations}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
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
          <View style={styles.emptyState}>
            <Ionicons name="mail-open-outline" size={48} color={Colors.textMuted} />
            <Text style={styles.emptyTitle}>暂无消息会话</Text>
            <Text style={styles.emptyText}>后续会接入新建会话、搜索和更完整的即时通讯能力。</Text>
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
