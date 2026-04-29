/**
 * ChatBubble（移动端 persona chat）
 *
 * user 右侧蓝（这里复用 brand primary 暖色调）/ assistant 左侧灰。
 * assistant 内容走 MarkdownRenderer。长按由父组件挂 onLongPress 调起 ActionSheet。
 */

import React from 'react'
import { View, Text, StyleSheet, TouchableWithoutFeedback } from 'react-native'
import { Colors } from '../../../constants/colors'
import { Layout } from '../../../constants/layout'
import { MarkdownRenderer } from './MarkdownRenderer'

export type ChatBubbleRole = 'user' | 'assistant' | 'system'

export interface ChatBubbleMessage {
  id: string
  role: ChatBubbleRole
  content: string
  /** assistant 流式中标记,用来显示打字光标 */
  pending?: boolean
}

interface ChatBubbleProps {
  message: ChatBubbleMessage
  onLongPress?: (message: ChatBubbleMessage) => void
}

export function ChatBubble({ message, onLongPress }: ChatBubbleProps) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <View style={styles.systemRow}>
        <Text style={styles.systemText}>{message.content}</Text>
      </View>
    )
  }

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      <TouchableWithoutFeedback
        onLongPress={() => onLongPress?.(message)}
        delayLongPress={400}
      >
        <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
          {isAssistant ? (
            <MarkdownRenderer content={message.content || (message.pending ? '...' : '')} />
          ) : (
            <Text style={styles.userText}>{message.content}</Text>
          )}
          {message.pending && isAssistant && (
            <Text style={styles.pendingMark}>▋</Text>
          )}
        </View>
      </TouchableWithoutFeedback>
    </View>
  )
}

const styles = StyleSheet.create({
  row: {
    paddingHorizontal: Layout.spacing.md,
    marginVertical: Layout.spacing.xs,
    flexDirection: 'row',
  },
  rowUser: {
    justifyContent: 'flex-end',
  },
  rowAssistant: {
    justifyContent: 'flex-start',
  },
  bubble: {
    maxWidth: '82%',
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    borderRadius: Layout.borderRadius.lg,
  },
  bubbleUser: {
    backgroundColor: Colors.primary,
    borderBottomRightRadius: Layout.borderRadius.sm,
  },
  bubbleAssistant: {
    backgroundColor: Colors.surface,
    borderBottomLeftRadius: Layout.borderRadius.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  userText: {
    color: Colors.white,
    fontSize: Layout.fontSize.md,
    lineHeight: 22,
  },
  pendingMark: {
    marginTop: 4,
    color: Colors.primary,
    fontSize: Layout.fontSize.md,
  },
  systemRow: {
    paddingVertical: Layout.spacing.sm,
    alignItems: 'center',
  },
  systemText: {
    fontSize: Layout.fontSize.xs,
    color: Colors.textMuted,
  },
})
