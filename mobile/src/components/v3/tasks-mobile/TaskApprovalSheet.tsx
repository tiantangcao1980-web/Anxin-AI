/**
 * TaskApprovalSheet — 审批弹层
 *
 * 提供「批准 / 驳回」两个操作。驳回需要填写 reason。
 */
import { useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'

import type { AgentTask } from '@/lib/api/agentTasks'
import { useTheme } from '@/lib/theme'

import { BottomSheet } from './BottomSheet'

interface Props {
  visible: boolean
  task: AgentTask | null
  onClose: () => void
  onApprove: (taskId: string) => Promise<void>
  onReject: (taskId: string, reason: string) => Promise<void>
}

export function TaskApprovalSheet({ visible, task, onClose, onApprove, onReject }: Props) {
  const t = useTheme()
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [mode, setMode] = useState<'choose' | 'reject'>('choose')

  const reset = () => {
    setReason('')
    setMode('choose')
    setSubmitting(false)
  }

  const handleClose = () => {
    if (submitting) return
    reset()
    onClose()
  }

  const handleApprove = async () => {
    if (!task) return
    setSubmitting(true)
    try {
      await onApprove(task.id)
      reset()
      onClose()
    } finally {
      setSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!task || reason.trim().length === 0) return
    setSubmitting(true)
    try {
      await onReject(task.id, reason.trim())
      reset()
      onClose()
    } finally {
      setSubmitting(false)
    }
  }

  const title = (task?.payload?.title as string | undefined) ?? '待审批任务'
  const desc = (task?.payload?.user_input as string | undefined) ?? ''

  return (
    <BottomSheet visible={visible} onClose={handleClose} heightRatio={mode === 'reject' ? 0.6 : 0.45}>
      <Text style={[styles.title, { color: t.text }]}>审批任务</Text>
      <Text style={[styles.taskTitle, { color: t.text }]} numberOfLines={2}>
        {title}
      </Text>
      {desc.length > 0 && (
        <Text style={[styles.desc, { color: t.textSecondary }]} numberOfLines={3}>
          {desc}
        </Text>
      )}

      {mode === 'choose' && (
        <View style={styles.actions}>
          <Pressable
            disabled={submitting}
            onPress={handleApprove}
            style={({ pressed }) => [
              styles.btn,
              { backgroundColor: t.success, opacity: pressed || submitting ? 0.7 : 1 },
            ]}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.approveText}>批准执行</Text>
            )}
          </Pressable>
          <Pressable
            disabled={submitting}
            onPress={() => setMode('reject')}
            style={({ pressed }) => [
              styles.btn,
              styles.rejectBtn,
              { borderColor: t.border, opacity: pressed ? 0.7 : 1 },
            ]}
          >
            <Text style={[styles.rejectText, { color: t.error }]}>驳回</Text>
          </Pressable>
        </View>
      )}

      {mode === 'reject' && (
        <View style={styles.rejectArea}>
          <Text style={[styles.label, { color: t.textSecondary }]}>请填写驳回原因</Text>
          <TextInput
            value={reason}
            onChangeText={setReason}
            placeholder="例如：执行风险过高 / 暂不需要 / ..."
            placeholderTextColor={t.textMuted}
            multiline
            numberOfLines={4}
            style={[
              styles.input,
              { color: t.text, borderColor: t.border, backgroundColor: t.surface },
            ]}
          />
          <View style={styles.actions}>
            <Pressable
              disabled={submitting}
              onPress={() => setMode('choose')}
              style={({ pressed }) => [
                styles.btn,
                styles.rejectBtn,
                { borderColor: t.border, opacity: pressed ? 0.7 : 1 },
              ]}
            >
              <Text style={[styles.rejectText, { color: t.text }]}>返回</Text>
            </Pressable>
            <Pressable
              disabled={submitting || reason.trim().length === 0}
              onPress={handleReject}
              style={({ pressed }) => [
                styles.btn,
                {
                  backgroundColor: t.error,
                  opacity:
                    submitting || reason.trim().length === 0 ? 0.5 : pressed ? 0.7 : 1,
                },
              ]}
            >
              {submitting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.approveText}>确认驳回</Text>
              )}
            </Pressable>
          </View>
        </View>
      )}
    </BottomSheet>
  )
}

const styles = StyleSheet.create({
  title: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 8,
  },
  taskTitle: {
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 6,
  },
  desc: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 12,
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
  approveText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  rejectBtn: {
    borderWidth: StyleSheet.hairlineWidth,
  },
  rejectText: {
    fontSize: 15,
    fontWeight: '600',
  },
  rejectArea: {
    marginTop: 8,
  },
  label: {
    fontSize: 13,
    marginBottom: 6,
  },
  input: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 10,
    padding: 10,
    minHeight: 90,
    fontSize: 14,
    textAlignVertical: 'top',
  },
})
