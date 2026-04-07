import { useEffect, useMemo, useState } from 'react'
import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack, useLocalSearchParams } from 'expo-router'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { getNotificationTargetRoute } from '@/features/inbox/engagement-model'
import { api } from '@/services/api'
import type { NotificationItem } from '@/types/api'

export default function NotificationDetailScreen() {
  const params = useLocalSearchParams<{
    id: string
    title?: string
    message?: string
    event_type?: string
    created_at?: string
    is_read?: string
    target?: string
  }>()
  const [notification, setNotification] = useState<NotificationItem>({
    id: params.id || 'notification',
    type: 'info',
    title: params.title || '通知详情',
    message: params.message || '暂无通知内容',
    is_read: params.is_read === '1',
    event_type: params.event_type,
    created_at: params.created_at || '刚刚',
  })

  useEffect(() => {
    const markRead = async () => {
      if (!params.id || notification.is_read) {
        return
      }

      try {
        const updated = await api.post<NotificationItem>(`/notifications/${params.id}/read`)
        setNotification(updated)
      } catch {
      }
    }

    markRead()
  }, [notification.is_read, params.id])

  const targetRoute = useMemo(
    () => params.target || getNotificationTargetRoute(notification),
    [notification, params.target]
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '通知详情' }} />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.heroCard}>
          <Text style={styles.title}>{notification.title}</Text>
          <Text style={styles.metaText}>{notification.created_at}</Text>
          <Text style={styles.message}>{notification.message}</Text>
        </View>

        <View style={styles.actionCard}>
          <Text style={styles.sectionTitle}>后续动作</Text>
          <TouchableOpacity
            style={styles.actionButton}
            activeOpacity={0.8}
            onPress={() => router.push(targetRoute as any)}
          >
            <Text style={styles.actionButtonText}>查看关联内容</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.secondaryButton}
            activeOpacity={0.8}
            onPress={async () => {
              try {
                await api.post('/notifications/read-all')
                Alert.alert('已处理', '通知已标记为已读。')
              } catch (error: any) {
                Alert.alert('操作失败', error?.message || '通知处理失败')
              }
            }}
          >
            <Text style={styles.secondaryButtonText}>全部标记已读</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    padding: Layout.spacing.md,
    paddingBottom: Layout.spacing.xl,
    gap: Layout.spacing.md,
  },
  heroCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.lg,
    padding: Layout.spacing.lg,
  },
  title: {
    color: Colors.text,
    fontSize: Layout.fontSize.xl,
    fontWeight: '700',
  },
  metaText: {
    marginTop: Layout.spacing.sm,
    color: Colors.textMuted,
    fontSize: Layout.fontSize.xs,
  },
  message: {
    marginTop: Layout.spacing.md,
    color: Colors.text,
    fontSize: Layout.fontSize.sm,
    lineHeight: 22,
  },
  actionCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
  },
  sectionTitle: {
    color: Colors.text,
    fontSize: Layout.fontSize.md,
    fontWeight: '700',
    marginBottom: Layout.spacing.sm,
  },
  actionButton: {
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.md,
    paddingVertical: Layout.spacing.md,
    alignItems: 'center',
  },
  actionButtonText: {
    color: Colors.white,
    fontWeight: '600',
    fontSize: Layout.fontSize.sm,
  },
  secondaryButton: {
    marginTop: Layout.spacing.sm,
    backgroundColor: Colors.primary + '12',
    borderRadius: Layout.borderRadius.md,
    paddingVertical: Layout.spacing.md,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: Colors.primary,
    fontWeight: '600',
    fontSize: Layout.fontSize.sm,
  },
})
