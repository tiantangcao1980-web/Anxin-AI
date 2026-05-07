import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Stack, useLocalSearchParams } from 'expo-router'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { EmptyState } from '@/components/EmptyState'
import { getApprovalActions, getDetailLoadErrorMessage } from '@/features/workflow/detail-model'
import { api } from '@/services/api'
import type { ApprovalItem } from '@/types/api'

export default function ApprovalDetailScreen() {
  const params = useLocalSearchParams<{
    id: string
    title?: string
    type?: string
    status?: ApprovalItem['status']
    description?: string
  }>()
  const [approval, setApproval] = useState<ApprovalItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadDetail = useCallback(async () => {
    if (!params.id) {
      setApproval(null)
      setLoadError('缺少审批 ID，无法加载审批详情')
      setLoading(false)
      return
    }

    setLoading(true)
    setLoadError(null)
    try {
      const detail = await api.get<ApprovalItem>(`/approvals/${params.id}`)
      setApproval(detail)
    } catch (error) {
      setApproval(null)
      setLoadError(getDetailLoadErrorMessage(error, '加载审批详情失败'))
    } finally {
      setLoading(false)
    }
  }, [params.id])

  useEffect(() => {
    loadDetail()
  }, [loadDetail])

  const actions = useMemo(() => (approval ? getApprovalActions(approval.status) : []), [approval])

  const handleAction = async (action: 'approve' | 'reject' | 'withdraw') => {
    if (!params.id || !approval) {
      return
    }

    if (action === 'reject' && !comment.trim()) {
      Alert.alert('请填写驳回意见', '驳回审批前请填写处理意见。')
      return
    }

    setSubmitting(true)
    try {
      const endpoint = action === 'approve'
        ? `/approvals/${params.id}/approve`
        : action === 'reject'
          ? `/approvals/${params.id}/reject`
          : `/approvals/${params.id}/withdraw`
      const payload = action === 'withdraw' ? undefined : { comment: comment.trim() || undefined }
      const updated = await api.put<ApprovalItem>(endpoint, payload)
      setApproval(updated)
      if (action !== 'withdraw') {
        setComment('')
      }
      Alert.alert('已完成', action === 'approve' ? '审批已通过' : action === 'reject' ? '审批已驳回' : '审批已撤回')
    } catch (error: any) {
      Alert.alert('操作失败', error?.message || '审批操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <Stack.Screen options={{ title: '审批详情' }} />
        <View style={styles.centered}>
          <ActivityIndicator color={Colors.primary} size="large" />
          <Text style={styles.loadingText}>正在加载审批详情</Text>
        </View>
      </SafeAreaView>
    )
  }

  if (!approval) {
    return (
      <SafeAreaView style={styles.container} edges={['bottom']}>
        <Stack.Screen options={{ title: '审批详情' }} />
        <EmptyState
          icon="alert-circle-outline"
          title="无法加载审批详情"
          description={loadError || '请稍后重试'}
          actionLabel={params.id ? '重试' : undefined}
          onAction={params.id ? loadDetail : undefined}
        />
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '审批详情' }} />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.heroCard}>
          <Text style={styles.title}>{approval.title}</Text>
          <Text style={styles.metaText}>
            {approval.status === 'pending' ? '待审批' : approval.status === 'approved' ? '已通过' : approval.status === 'rejected' ? '已驳回' : '已撤回'}
            {' · '}
            {approval.type}
          </Text>
          <Text style={styles.description}>{approval.description || '暂无审批说明'}</Text>
        </View>

        <View style={styles.metaCard}>
          <Text style={styles.sectionTitle}>审批信息</Text>
          <Text style={styles.metaRow}>发起人：{approval.requester_name || approval.requester_id || '未知'}</Text>
          <Text style={styles.metaRow}>审批人：{approval.approver_name || approval.approver_id || '待指派'}</Text>
          <Text style={styles.metaRow}>发起时间：{approval.created_at || '暂无时间'}</Text>
          <Text style={styles.metaRow}>备注：{approval.comment || '暂无备注'}</Text>
        </View>

        {actions.length > 0 ? (
          <View style={styles.metaCard}>
            <Text style={styles.sectionTitle}>处理意见</Text>
            <TextInput
              style={styles.commentInput}
              multiline
              value={comment}
              onChangeText={setComment}
              placeholder="可填写审批意见或驳回原因"
              placeholderTextColor={Colors.textMuted}
            />
            {actions.map((action) => (
              <TouchableOpacity
                key={action.label}
                style={[
                  styles.actionButton,
                  action.tone === 'secondary' && styles.actionButtonSecondary,
                  action.tone === 'danger' && styles.actionButtonDanger,
                ]}
                onPress={() => handleAction(action.action)}
                disabled={submitting}
                activeOpacity={0.8}
              >
                <Text
                  style={[
                    styles.actionButtonText,
                    action.tone !== 'primary' && styles.actionButtonTextSecondary,
                    action.tone === 'danger' && styles.actionButtonTextDanger,
                  ]}
                >
                  {submitting ? '处理中...' : action.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: Layout.spacing.xl,
  },
  loadingText: {
    marginTop: Layout.spacing.md,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
  },
  content: {
    padding: Layout.spacing.md,
    paddingBottom: Layout.spacing.xl,
    gap: Layout.spacing.md,
  },
  heroCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.lg,
    padding: Layout.spacing.lg,
  },
  title: {
    color: Colors.text,
    fontSize: Layout.fontSize.xl,
    fontWeight: '700',
  },
  metaText: {
    marginTop: Layout.spacing.sm,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
  },
  description: {
    marginTop: Layout.spacing.md,
    color: Colors.text,
    fontSize: Layout.fontSize.sm,
    lineHeight: 22,
  },
  metaCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
  },
  sectionTitle: {
    color: Colors.text,
    fontSize: Layout.fontSize.md,
    fontWeight: '700',
    marginBottom: Layout.spacing.sm,
  },
  metaRow: {
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    marginBottom: Layout.spacing.sm,
  },
  commentInput: {
    minHeight: 96,
    borderRadius: Layout.borderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: Layout.spacing.md,
    color: Colors.text,
    fontSize: Layout.fontSize.sm,
    textAlignVertical: 'top',
  },
  actionButton: {
    marginTop: Layout.spacing.sm,
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.md,
    paddingVertical: Layout.spacing.md,
    alignItems: 'center',
  },
  actionButtonSecondary: {
    backgroundColor: Colors.primary + '12',
  },
  actionButtonDanger: {
    backgroundColor: '#FEE2E2',
  },
  actionButtonText: {
    color: Colors.white,
    fontSize: Layout.fontSize.sm,
    fontWeight: '600',
  },
  actionButtonTextSecondary: {
    color: Colors.primary,
  },
  actionButtonTextDanger: {
    color: '#DC2626',
  },
})
