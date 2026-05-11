/**
 * CreateTaskSheet — 创建任务弹层
 *
 * 选 persona + 输入 message，组装成 CreateTaskRequest
 */
import { useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'

import type { CreateTaskRequest } from '@/lib/api/agentTasks'
import { useTheme } from '@/lib/theme'

import { BottomSheet } from './BottomSheet'

const PERSONAS = [
  { value: 'anxin_assistant', label: '安心助手', emoji: '🤖', desc: '通用法务问答与流程' },
  { value: 'contract_steward', label: '合同管家', emoji: '📑', desc: '合同审查 / 比对 / 摘要' },
  { value: 'investigator', label: '调查员', emoji: '🔎', desc: '尽调 / 主体穿透 / 风险检索' },
  { value: 'litigator', label: '诉讼专员', emoji: '⚖️', desc: '案件检索 / 文书生成' },
] as const

interface Props {
  visible: boolean
  onClose: () => void
  onSubmit: (body: CreateTaskRequest) => Promise<void>
}

export function CreateTaskSheet({ visible, onClose, onSubmit }: Props) {
  const t = useTheme()
  const [persona, setPersona] = useState<string>(PERSONAS[0].value)
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const reset = () => {
    setPersona(PERSONAS[0].value)
    setMessage('')
    setSubmitting(false)
  }

  const handleClose = () => {
    if (submitting) return
    reset()
    onClose()
  }

  const handleSubmit = async () => {
    if (message.trim().length === 0) return
    setSubmitting(true)
    try {
      await onSubmit({
        agent_persona: persona,
        payload: {
          title: message.trim().slice(0, 40),
          user_input: message.trim(),
        },
        priority: 5,
      })
      reset()
      onClose()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <BottomSheet visible={visible} onClose={handleClose} heightRatio={0.78}>
      <Text style={[styles.title, { color: t.text }]}>新建 Agent 任务</Text>

      <Text style={[styles.label, { color: t.textSecondary }]}>选择 Agent</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.personaRow}
      >
        {PERSONAS.map((p) => {
          const active = persona === p.value
          return (
            <Pressable
              key={p.value}
              onPress={() => setPersona(p.value)}
              style={({ pressed }) => [
                styles.personaCard,
                {
                  backgroundColor: active ? t.primaryLight : t.surface,
                  borderColor: active ? t.primary : t.border,
                  opacity: pressed ? 0.85 : 1,
                },
              ]}
            >
              <Text style={styles.personaEmoji}>{p.emoji}</Text>
              <Text
                style={[
                  styles.personaLabel,
                  { color: active ? t.primaryDark : t.text },
                ]}
              >
                {p.label}
              </Text>
              <Text style={[styles.personaDesc, { color: t.textSecondary }]} numberOfLines={2}>
                {p.desc}
              </Text>
            </Pressable>
          )
        })}
      </ScrollView>

      <Text style={[styles.label, { color: t.textSecondary, marginTop: 14 }]}>
        任务描述
      </Text>
      <TextInput
        value={message}
        onChangeText={setMessage}
        placeholder="例如：审查附件中的服务合同，重点关注违约责任与知识产权条款"
        placeholderTextColor={t.textMuted}
        multiline
        numberOfLines={5}
        style={[
          styles.input,
          { color: t.text, borderColor: t.border, backgroundColor: t.surface },
        ]}
      />

      <View style={styles.actions}>
        <Pressable
          disabled={submitting}
          onPress={handleClose}
          style={({ pressed }) => [
            styles.btn,
            styles.cancelBtn,
            { borderColor: t.border, opacity: pressed ? 0.7 : 1 },
          ]}
        >
          <Text style={[styles.cancelText, { color: t.text }]}>取消</Text>
        </Pressable>
        <Pressable
          disabled={submitting || message.trim().length === 0}
          onPress={handleSubmit}
          style={({ pressed }) => [
            styles.btn,
            styles.submitBtn,
            { backgroundColor: t.primary },
            {
              opacity:
                submitting || message.trim().length === 0 ? 0.5 : pressed ? 0.85 : 1,
            },
          ]}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.submitText}>创建任务</Text>
          )}
        </Pressable>
      </View>
    </BottomSheet>
  )
}

const styles = StyleSheet.create({
  title: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  personaRow: {
    paddingVertical: 4,
    gap: 10,
  },
  personaCard: {
    width: 150,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    marginRight: 10,
  },
  personaEmoji: {
    fontSize: 22,
    marginBottom: 4,
  },
  personaLabel: {
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 4,
  },
  personaDesc: {
    fontSize: 11,
    lineHeight: 15,
  },
  input: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 10,
    padding: 10,
    minHeight: 110,
    fontSize: 14,
    textAlignVertical: 'top',
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 16,
  },
  btn: {
    flex: 1,
    paddingVertical: 13,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelBtn: {
    borderWidth: StyleSheet.hairlineWidth,
  },
  cancelText: {
    fontSize: 15,
    fontWeight: '600',
  },
  submitBtn: {},
  submitText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
})
