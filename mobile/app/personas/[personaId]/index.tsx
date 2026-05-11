/**
 * Persona 工作台首页（移动端 P17-C）
 *
 * 顶部 PersonaHeader（含 tabs：工作台 / 对话 / 能力）
 * 主体：
 *   - sample questions 一行可滚动 chips
 *   - 当前 chat 历史（精简版）+ 输入框
 *   - 推荐能力前 4 个 CapabilityCard
 *
 * 切换 tab 时 router.replace 到对应子路由,保留 personaId 参数。
 */

import React, { useCallback, useMemo, useState } from 'react'
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
  ActionSheetIOS,
  Alert,
  Share,
} from 'react-native'
import { router, Stack, useLocalSearchParams } from 'expo-router'
import { Colors } from '../../../src/constants/colors'
import { Layout } from '../../../src/constants/layout'
import { PersonaHeader, type PersonaTabKey } from '../../../src/components/v3/personas-mobile/PersonaHeader'
import { ChatBubble, type ChatBubbleMessage } from '../../../src/components/v3/personas-mobile/ChatBubble'
import { ChatInput } from '../../../src/components/v3/personas-mobile/ChatInput'
import { CapabilityCard } from '../../../src/components/v3/personas-mobile/CapabilityCard'
import { getPersonaMeta } from '../../../src/lib/personas/registry'
import { usePersonaChat } from '../../../src/lib/personas/usePersonaChat'

export default function PersonaWorkspaceScreen() {
  const params = useLocalSearchParams<{ personaId: string }>()
  const personaId = String(params.personaId || '')
  const persona = getPersonaMeta(personaId)
  const [activeTab, setActiveTab] = useState<PersonaTabKey>('home')

  const { messages, pending, send, triggerCapability, regenerate } = usePersonaChat(personaId)

  const recommendedCapabilities = useMemo(
    () => (persona ? persona.capabilities.slice(0, 4) : []),
    [persona],
  )

  const handleTabChange = useCallback(
    (next: PersonaTabKey) => {
      setActiveTab(next)
      if (next === 'chat') {
        router.push({
          pathname: '/personas/[personaId]/chat',
          params: { personaId },
        })
      } else if (next === 'capabilities') {
        router.push({
          pathname: '/personas/[personaId]/capabilities',
          params: { personaId },
        })
      }
    },
    [personaId],
  )

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
        ActionSheetIOS.showActionSheetWithOptions(
          { options, cancelButtonIndex },
          onAction,
        )
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

  if (!persona) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Stack.Screen options={{ title: '智能体' }} />
        <View style={styles.center}>
          <Text style={styles.errorText}>未找到该智能体: {personaId}</Text>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.linkText}>返回</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <Stack.Screen options={{ title: persona.display_name, headerBackTitle: '智能体' }} />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 88 : 0}
      >
        <PersonaHeader persona={persona} active={activeTab} onChangeTab={handleTabChange} />

        <ScrollView
          style={styles.flex}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* Sample questions chips */}
          {messages.length === 0 && (
            <View style={styles.chipsBlock}>
              <Text style={styles.sectionLabel}>💡 你可以这样问</Text>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.chipsRow}
              >
                {persona.sample_questions.map((q) => (
                  <TouchableOpacity
                    key={q}
                    style={styles.chip}
                    onPress={() => send(q)}
                    activeOpacity={0.85}
                  >
                    <Text style={styles.chipText} numberOfLines={1}>
                      {q}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          )}

          {/* Inline chat 列表（精简） */}
          {messages.length > 0 && (
            <View style={styles.chatBlock}>
              {messages.map((m) => (
                <ChatBubble key={m.id} message={m} onLongPress={handleLongPressMessage} />
              ))}
              <TouchableOpacity
                style={styles.expandChatBtn}
                onPress={() =>
                  router.push({
                    pathname: '/personas/[personaId]/chat',
                    params: { personaId },
                  })
                }
              >
                <Text style={styles.expandChatText}>展开全屏对话 →</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* 推荐能力 */}
          <View style={styles.capsBlock}>
            <View style={styles.capsHeader}>
              <Text style={styles.sectionLabel}>⚡ 推荐能力</Text>
              <TouchableOpacity
                onPress={() =>
                  router.push({
                    pathname: '/personas/[personaId]/capabilities',
                    params: { personaId },
                  })
                }
              >
                <Text style={styles.linkText}>全部 {persona.capabilities.length} 项</Text>
              </TouchableOpacity>
            </View>
            {recommendedCapabilities.map((cap) => (
              <CapabilityCard
                key={cap.id}
                capability={cap}
                pending={pending}
                onTrigger={triggerCapability}
              />
            ))}
          </View>
        </ScrollView>

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
  scrollContent: {
    paddingBottom: Layout.spacing.xl,
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
  chipsBlock: {
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.md,
  },
  sectionLabel: {
    fontSize: Layout.fontSize.sm,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Layout.spacing.sm,
  },
  chipsRow: {
    gap: Layout.spacing.sm,
    paddingRight: Layout.spacing.md,
  },
  chip: {
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.full,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    maxWidth: 280,
  },
  chipText: {
    fontSize: Layout.fontSize.xs,
    color: Colors.text,
  },
  chatBlock: {
    paddingTop: Layout.spacing.md,
  },
  expandChatBtn: {
    alignSelf: 'center',
    marginTop: Layout.spacing.sm,
    paddingVertical: Layout.spacing.sm,
    paddingHorizontal: Layout.spacing.md,
  },
  expandChatText: {
    color: Colors.primary,
    fontSize: Layout.fontSize.sm,
    fontWeight: '600',
  },
  capsBlock: {
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.lg,
  },
  capsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Layout.spacing.sm,
  },
})
