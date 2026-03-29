// -*- coding: utf-8 -*-
import { useState, useRef, useCallback } from 'react'
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  Alert,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { api } from '@/services/api'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  status?: 'sending' | 'sent' | 'error'
}

// @mock-data FALLBACK
const welcomeMessage: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    '你好！我是安心法务 AI 助手。我可以帮你解答法律问题、审查合同、分析案件等。请描述你的法律问题，我会尽力为你提供专业建议。\n\n你可以试试问我：\n- 劳动合同纠纷怎么处理？\n- 公司章程需要注意什么？\n- 知识产权侵权如何维权？',
  created_at: new Date().toISOString(),
}

export default function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage])
  const [inputText, setInputText] = useState('')
  const [sending, setSending] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const flatListRef = useRef<FlatList<ChatMessage>>(null)

  const generateId = () => `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

  const handleSend = useCallback(async () => {
    const content = inputText.trim()
    if (!content || sending) return

    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      status: 'sending',
    }

    setMessages((prev) => [...prev, userMsg])
    setInputText('')
    setSending(true)

    try {
      const response = await api.post<{
        reply: string
        conversation_id: string
      }>('/chat/', {
        content,
        conversation_id: conversationId,
      })

      if (response.conversation_id) {
        setConversationId(response.conversation_id)
      }

      // 更新用户消息状态
      setMessages((prev) =>
        prev.map((m) => (m.id === userMsg.id ? { ...m, status: 'sent' as const } : m))
      )

      // 添加 AI 回复
      const aiMsg: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: response.reply,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, aiMsg])
    } catch {
      // 标记发送失败
      setMessages((prev) =>
        prev.map((m) => (m.id === userMsg.id ? { ...m, status: 'error' as const } : m))
      )
      Alert.alert('发送失败', '网络异常，请稍后重试', [{ text: '知道了' }])
    } finally {
      setSending(false)
    }
  }, [inputText, sending, conversationId])

  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isUser = item.role === 'user'
    return (
      <View style={[styles.messageRow, isUser ? styles.messageRowUser : styles.messageRowAI]}>
        {!isUser && (
          <View style={styles.avatarAI}>
            <Ionicons name="sparkles" size={16} color={Colors.primary} />
          </View>
        )}
        <View
          style={[styles.messageBubble, isUser ? styles.bubbleUser : styles.bubbleAI]}
        >
          <Text style={[styles.messageText, isUser ? styles.textUser : styles.textAI]}>
            {item.content}
          </Text>
          {item.status === 'error' && (
            <TouchableOpacity style={styles.retryHint}>
              <Ionicons name="alert-circle" size={14} color={Colors.error} />
              <Text style={styles.retryText}>发送失败</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    )
  }

  const renderTypingIndicator = () => {
    if (!sending) return null
    return (
      <View style={[styles.messageRow, styles.messageRowAI]}>
        <View style={styles.avatarAI}>
          <Ionicons name="sparkles" size={16} color={Colors.primary} />
        </View>
        <View style={[styles.messageBubble, styles.bubbleAI, styles.typingBubble]}>
          <View style={styles.typingDots}>
            <View style={[styles.dot, styles.dot1]} />
            <View style={[styles.dot, styles.dot2]} />
            <View style={[styles.dot, styles.dot3]} />
          </View>
        </View>
      </View>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        {/* 消息列表 */}
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={renderMessage}
          ListFooterComponent={renderTypingIndicator}
          contentContainerStyle={styles.messageList}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        />

        {/* 输入栏 */}
        <View style={styles.inputBar}>
          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.textInput}
              placeholder="描述你的法律问题..."
              placeholderTextColor={Colors.textMuted}
              value={inputText}
              onChangeText={setInputText}
              multiline
              maxLength={2000}
              editable={!sending}
            />
          </View>
          <TouchableOpacity
            style={[
              styles.sendButton,
              (!inputText.trim() || sending) && styles.sendButtonDisabled,
            ]}
            onPress={handleSend}
            disabled={!inputText.trim() || sending}
            activeOpacity={0.7}
          >
            <Ionicons
              name="send"
              size={20}
              color={inputText.trim() && !sending ? Colors.white : Colors.textMuted}
            />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
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
  messageList: {
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    paddingBottom: Layout.spacing.sm,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: Layout.spacing.md,
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowAI: {
    justifyContent: 'flex-start',
  },
  avatarAI: {
    width: 32,
    height: 32,
    borderRadius: Layout.borderRadius.full,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Layout.spacing.sm,
  },
  messageBubble: {
    maxWidth: '75%',
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm + 2,
    borderRadius: Layout.borderRadius.lg,
  },
  bubbleUser: {
    backgroundColor: Colors.primary,
    borderBottomRightRadius: 4,
  },
  bubbleAI: {
    backgroundColor: Colors.surface,
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: Layout.fontSize.md,
    lineHeight: 22,
  },
  textUser: {
    color: Colors.white,
  },
  textAI: {
    color: Colors.text,
  },
  retryHint: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Layout.spacing.xs,
    gap: 4,
  },
  retryText: {
    fontSize: Layout.fontSize.xs,
    color: Colors.error,
  },
  typingBubble: {
    paddingVertical: Layout.spacing.md,
    paddingHorizontal: Layout.spacing.lg,
  },
  typingDots: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.textMuted,
  },
  dot1: {
    opacity: 0.4,
  },
  dot2: {
    opacity: 0.6,
  },
  dot3: {
    opacity: 0.8,
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.border,
    backgroundColor: Colors.background,
    gap: Layout.spacing.sm,
  },
  inputWrapper: {
    flex: 1,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.xl,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Platform.OS === 'ios' ? Layout.spacing.sm : 0,
    maxHeight: 120,
  },
  textInput: {
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    maxHeight: 100,
    paddingVertical: Platform.OS === 'ios' ? 0 : Layout.spacing.sm,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: Colors.surface,
  },
})
