import { useEffect, useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Stack, useLocalSearchParams } from 'expo-router'
import { EmptyState } from '@/components/EmptyState'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'
import type { IMMessage } from '@/types/api'

export default function MessageDetailScreen() {
  const params = useLocalSearchParams<{ id: string; title?: string }>()
  const [messages, setMessages] = useState<IMMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const loadMessages = async () => {
      if (!params.id) {
        setError('缺少会话 ID')
        setLoading(false)
        return
      }

      setLoading(true)
      setError('')
      try {
        const result = await api.get<IMMessage[]>(`/im/conversations/${params.id}/messages?limit=30`)
        setMessages(result)
        await api.put(`/im/conversations/${params.id}/read`)
      } catch (err: any) {
        setMessages([])
        setError(err?.message || '消息加载失败')
      } finally {
        setLoading(false)
      }
    }

    loadMessages()
  }, [params.id])

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: params.title || '消息详情' }} />
      {loading ? (
        <View style={styles.stateContainer}>
          <Text style={styles.stateText}>正在加载消息...</Text>
        </View>
      ) : error ? (
        <EmptyState icon="alert-circle-outline" title="消息加载失败" description={error} />
      ) : messages.length === 0 ? (
        <EmptyState icon="chatbubble-ellipses-outline" title="暂无消息" description="当前会话还没有消息记录。" />
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          {messages.map((message) => (
            <View
              key={message.id}
              style={[
                styles.messageCard,
                message.sender_id === 'system' ? styles.messageCardSystem : styles.messageCardUser,
              ]}
            >
              <Text style={styles.messageContent}>{message.is_recalled ? '消息已撤回' : message.content}</Text>
              <Text style={styles.messageMeta}>{message.created_at}</Text>
            </View>
          ))}
        </ScrollView>
      )}
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
  },
  stateContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Layout.spacing.xl,
  },
  stateText: {
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
  },
  messageCard: {
    maxWidth: '88%',
    borderRadius: Layout.borderRadius.lg,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  messageCardSystem: {
    backgroundColor: Colors.surface,
    alignSelf: 'flex-start',
  },
  messageCardUser: {
    backgroundColor: Colors.primary + '14',
    alignSelf: 'flex-end',
  },
  messageContent: {
    color: Colors.text,
    fontSize: Layout.fontSize.sm,
    lineHeight: 20,
  },
  messageMeta: {
    marginTop: Layout.spacing.xs,
    color: Colors.textMuted,
    fontSize: Layout.fontSize.xs,
  },
})
