/**
 * ChatInput（移动端 persona chat 输入框）
 *
 * - 输入框（多行,3 行内自适应）
 * - 附件按钮（占位 — 后续接相机/相册/文件）
 * - 发送按钮（disabled 当无内容或 pending 中）
 *
 * KeyboardAvoidingView 由父屏负责，本组件只关注 UI。
 */

import React, { useState } from 'react'
import { View, TextInput, TouchableOpacity, StyleSheet, Text } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '../../../constants/colors'
import { Layout } from '../../../constants/layout'

interface ChatInputProps {
  pending: boolean
  onSend: (message: string) => void
  onAttach?: () => void
  placeholder?: string
}

export function ChatInput({ pending, onSend, onAttach, placeholder }: ChatInputProps) {
  const [text, setText] = useState('')
  const trimmed = text.trim()
  const canSend = trimmed.length > 0 && !pending

  const handleSend = () => {
    if (!canSend) return
    onSend(trimmed)
    setText('')
  }

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.attachBtn}
        onPress={onAttach}
        disabled={!onAttach}
        activeOpacity={0.6}
        accessibilityLabel="附件"
      >
        <Ionicons name="add-circle-outline" size={26} color={Colors.textSecondary} />
      </TouchableOpacity>

      <TextInput
        style={styles.input}
        value={text}
        onChangeText={setText}
        placeholder={placeholder ?? '问问这个智能体...'}
        placeholderTextColor={Colors.textMuted}
        multiline
        maxLength={1500}
        editable={!pending}
      />

      <TouchableOpacity
        style={[styles.sendBtn, canSend ? styles.sendBtnActive : styles.sendBtnDisabled]}
        onPress={handleSend}
        disabled={!canSend}
        activeOpacity={0.85}
        accessibilityLabel="发送"
      >
        {pending ? (
          <Text style={styles.sendIconText}>...</Text>
        ) : (
          <Ionicons name="send" size={18} color={canSend ? Colors.white : Colors.textMuted} />
        )}
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: Layout.spacing.sm,
    backgroundColor: Colors.background,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.border,
    gap: Layout.spacing.sm,
  },
  attachBtn: {
    paddingBottom: Layout.spacing.xs,
  },
  input: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.lg,
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.sm,
    paddingBottom: Layout.spacing.sm,
    fontSize: Layout.fontSize.md,
    color: Colors.text,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnActive: {
    backgroundColor: Colors.primary,
  },
  sendBtnDisabled: {
    backgroundColor: Colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  sendIconText: {
    color: Colors.white,
    fontWeight: '700',
  },
})
