import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { Colors } from '../constants/colors'
import { Layout } from '../constants/layout'
import type { Message } from '../types/api'

interface ChatBubbleProps {
  message: Message
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === 'user'
  const isSending = message.status === 'sending'
  const isError = message.status === 'error'

  return (
    <View style={[styles.container, isUser ? styles.userContainer : styles.assistantContainer]}>
      <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
        <Text style={[styles.text, isUser ? styles.userText : styles.assistantText]}>
          {message.content}
        </Text>
        <View style={styles.meta}>
          <Text style={[styles.time, isUser ? styles.userTime : styles.assistantTime]}>
            {formatTime(message.created_at)}
          </Text>
          {isSending && <Text style={styles.statusText}>发送中...</Text>}
          {isError && <Text style={styles.errorText}>发送失败</Text>}
        </View>
      </View>
    </View>
  )
}

function formatTime(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  } catch {
    return ''
  }
}

const styles = StyleSheet.create({
  container: {
    marginVertical: Layout.spacing.xs,
    marginHorizontal: Layout.spacing.md,
  },
  userContainer: {
    alignItems: 'flex-end',
  },
  assistantContainer: {
    alignItems: 'flex-start',
  },
  bubble: {
    maxWidth: '80%',
    paddingVertical: Layout.spacing.sm + 2,
    paddingHorizontal: Layout.spacing.md,
    borderRadius: Layout.borderRadius.lg,
  },
  userBubble: {
    backgroundColor: Colors.primary,
    borderBottomRightRadius: Layout.borderRadius.sm,
  },
  assistantBubble: {
    backgroundColor: Colors.surface,
    borderBottomLeftRadius: Layout.borderRadius.sm,
  },
  text: {
    fontSize: Layout.fontSize.md,
    lineHeight: 22,
  },
  userText: {
    color: Colors.white,
  },
  assistantText: {
    color: Colors.text,
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Layout.spacing.xs,
    gap: Layout.spacing.xs,
  },
  time: {
    fontSize: Layout.fontSize.xs,
  },
  userTime: {
    color: 'rgba(255,255,255,0.7)',
  },
  assistantTime: {
    color: Colors.textMuted,
  },
  statusText: {
    fontSize: Layout.fontSize.xs,
    color: 'rgba(255,255,255,0.7)',
  },
  errorText: {
    fontSize: Layout.fontSize.xs,
    color: Colors.error,
  },
})
