/**
 * Persona 全屏 Chat（移动端 P17-C）
 *
 * 全屏 FlatList + 输入框,底部 KeyboardAvoidingView。
 * 长按消息 → ActionSheet（复制 / 重新生成 / 反馈）。
 */

import React, { useCallback, useRef } from 'react'
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
  ActionSheetIOS,
  Alert,
  Share,
} from 'react-native'
import { Stack, router, useLocalSearchParams } from 'expo-router'
import { Colors } from '../../../src/constants/colors'
import { Layout } from '../../../src/constants/layout'
import { ChatBubble, type ChatBubbleMessage } from '../../../src/components/v3/personas-mobile/ChatBubble'
import { ChatInput } from '../../../src/components/v3/personas-mobile/ChatInput'
import { getPersonaMeta } from '../../../src/lib/personas/registry'
import { usePersonaChat } from '../../../src/lib/personas/usePersonaChat'

export default function PersonaChatScreen() {
  const params = useLocalSearchParams<{ personaId: string }>()
  const personaId = String(params.personaId || '')
  const persona = getPersonaMeta(personaId)
  const { messages, pending, send, regenerate, clear } = usePersonaChat(personaId)
  const listRef = useRef<FlatList<ChatBubbleMessage>>(null)

  const handleLongPressMessage = useCallback(
    (msg: ChatBubbleMessage) => {
      const options = ['复制', '重新生成', '反馈问题', '取消']
      const cancelButtonIndex = 3
      const onAction = (index: number) => {
        if (index === 0) {
          Share.share({ message: msg.content })
        } else if (index === 1) {
          regenerate(msg.id)
        } else if (index === 2) {
          Alert.alert('反馈已记录', '感谢反馈,我们会改进这位智能体的回答质量。')
        }
      }
      if (Platform.OS === 'ios') {
        ActionSheetIOS.showActionSheetWithOptions({ options, cancelButtonIndex }, onAction)
      } else {
        Alert.alert('消息操作', '', [
          { text: '复制', onPress: () => onAction(0) },
          { text: '重新生成', onPress: () => onAction(1) },
          { text: '反馈问题', onPress: () => onAction(2) },
          { text: '取消', style: 'cancel' },
        ])
      }
    },
    [regenerate],
  )

  const onContentSizeChange = useCallback(() => {
    listRef.current?.scrollToEnd({ animated: true })
  }, [])

  if (!persona) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Stack.Screen options={{ title: '对话' }} />
        <View style={styles.center}>
          <Text style={styles.errorText}>未找到该智能体</Text>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.linkText}>返回</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <Stack.Screen
        options={{
          title: `${persona.emoji} ${persona.display_name}`,
          headerRight: () =>
            messages.length > 0 ? (
              <TouchableOpacity onPress={clear} style={styles.headerBtn}>
                <Text style={styles.linkText}>清空</Text>
              </TouchableOpacity>
            ) : null,
        }}
      />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 88 : 0}
      >
        {messages.length === 0 ? (
          <View style={styles.emptyBlock}>
            <Text style={styles.emptyEmoji}>{persona.emoji}</Text>
            <Text style={styles.emptyTitle}>和 {persona.display_name} 开始对话</Text>
            <Text style={styles.emptyDesc}>{persona.tagline}</Text>
            <View style={styles.suggestBlock}>
              {persona.sample_questions.map((q) => (
                <TouchableOpacity
                  key={q}
                  style={styles.suggestRow}
                  onPress={() => send(q)}
                  activeOpacity={0.85}
                >
                  <Text style={styles.suggestText}>{q}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.id}
            renderItem={({ item }) => (
              <ChatBubble message={item} onLongPress={handleLongPressMessage} />
            )}
            contentContainerStyle={styles.listContent}
            onContentSizeChange={onContentSizeChange}
            keyboardShouldPersistTaps="handled"
          />
        )}

        <ChatInput
          pending={pending}
          onSend={send}
          onAttach={() => Alert.alert('附件', '附件上传将在下个版本接入')}
          placeholder={`@${persona.display_name}: 直接问吧...`}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  flex: {
    flex: 1,
  },
  listContent: {
    paddingTop: Layout.spacing.md,
    paddingBottom: Layout.spacing.md,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Layout.spacing.md,
  },
  errorText: {
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.md,
  },
  linkText: {
    color: Colors.primary,
    fontSize: Layout.fontSize.sm,
    fontWeight: '600',
  },
  emptyBlock: {
    flex: 1,
    paddingHorizontal: Layout.spacing.lg,
    paddingTop: Layout.spacing.xl,
    alignItems: 'center',
  },
  emptyEmoji: {
    fontSize: 56,
    marginBottom: Layout.spacing.md,
  },
  emptyTitle: {
    fontSize: Layout.fontSize.xl,
    fontWeight: '700',
    color: Colors.text,
  },
  emptyDesc: {
    marginTop: Layout.spacing.sm,
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
  suggestBlock: {
    marginTop: Layout.spacing.lg,
    width: '100%',
    gap: Layout.spacing.sm,
  },
  suggestRow: {
    width: '100%',
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  suggestText: {
    color: Colors.text,
    fontSize: Layout.fontSize.sm,
    lineHeight: 20,
  },
  headerBtn: {
    paddingHorizontal: Layout.spacing.sm,
  },
})
