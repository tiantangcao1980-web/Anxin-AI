import { useEffect, useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Stack, useLocalSearchParams } from 'expo-router'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'
import type { IMMessage } from '@/types/api'

const fallbackMessages: IMMessage[] = [
  {
    id: 'm1',
    conversation_id: 'fallback',
    sender_id: 'system',
    content: '这里会展示消息详情和会话历史。',
    message_type: 'text',
    is_recalled: false,
    created_at: '刚刚',
  },
]

export default function MessageDetailScreen() {
  const params = useLocalSearchParams<{ id: string; title?: string }>()
  const [messages, setMessages] = useState<IMMessage[]>(fallbackMessages)

  useEffect(() => {
    const loadMessages = async () => {
      if (!params.id) {
        return
      }

      try {
        const result = await api.get<IMMessage[]>(`/im/conversations/${params.id}/messages?limit=30`)
        if (result.length > 0) {
          setMessages(result)
        }
        await api.put(`/im/conversations/${params.id}/read`)
      } catch {
        setMessages(fallbackMessages)
      }
    }

    loadMessages()
  }, [params.id])

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: params.title || '消息详情' }} />
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
