import { useEffect, useState, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'

/**
 * 智能协作 Tab —— 汇聚案件 / 合同 / 任务 / 审批 / 消息 / 找律师 六大协作场景。
 *
 * 每个卡片点击进入对应 Root Stack 页面（不在 tab 内嵌以避免滚动/导航冲突），
 * 顶部展示用户侧近 7 天摘要（任务待处理数 / 消息未读数 / 合同待审数）。
 */

interface CollaborationSummary {
  pendingTasks: number
  pendingApprovals: number
  unreadMessages: number
  pendingContracts: number
}

const DEFAULT_SUMMARY: CollaborationSummary = {
  pendingTasks: 0,
  pendingApprovals: 0,
  unreadMessages: 0,
  pendingContracts: 0,
}

const CARDS = [
  { key: 'cases', label: '我的案件', icon: 'briefcase-outline', desc: '案件全生命周期跟进', route: '/cases' },
  { key: 'contracts', label: '合同管理', icon: 'document-text-outline', desc: 'AI 审查、风险识别', route: '/contracts' },
  { key: 'tasks', label: '任务', icon: 'checkmark-done-outline', desc: '待办事项与指派', route: '/tasks' },
  { key: 'approvals', label: '审批', icon: 'shield-checkmark-outline', desc: '合同与用印审批流', route: '/approvals' },
  { key: 'messages', label: '消息', icon: 'chatbubble-ellipses-outline', desc: 'IM 与会话记录', route: '/messages' },
  { key: 'find-lawyer', label: '找律师', icon: 'people-outline', desc: 'AI 匹配专业律师', route: '/find-lawyer' },
] as const

export default function CollaborationScreen() {
  const [summary, setSummary] = useState<CollaborationSummary>(DEFAULT_SUMMARY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const loadSummary = useCallback(async () => {
    try {
      setError(null)
      const results = await Promise.allSettled([
        api.get<{ count: number }>('/tasks/stats/pending'),
        api.get<{ count: number }>('/approvals/stats/pending'),
        api.get<{ count: number }>('/notifications/unread-count'),
        api.get<{ count: number }>('/contracts/stats/pending-review'),
      ])

      setSummary({
        pendingTasks: results[0].status === 'fulfilled' ? results[0].value.count : 0,
        pendingApprovals: results[1].status === 'fulfilled' ? results[1].value.count : 0,
        unreadMessages: results[2].status === 'fulfilled' ? results[2].value.count : 0,
        pendingContracts: results[3].status === 'fulfilled' ? results[3].value.count : 0,
      })
    } catch (err: any) {
      // 已用 Promise.allSettled 包住，这里只捕获极端情况
      setError(err?.message || '加载协作摘要失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadSummary()
  }, [loadSummary])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadSummary()
  }, [loadSummary])

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
        }
      >
        <Text style={styles.heading}>智能协作</Text>
        <Text style={styles.subheading}>案件 · 合同 · 任务 · 审批 · 消息 一屏直达</Text>

        {/* 摘要四色块 */}
        <View style={styles.summaryRow}>
          <StatBlock label="待处理任务" value={summary.pendingTasks} color={Colors.primary} />
          <StatBlock label="待审批" value={summary.pendingApprovals} color="#3B82F6" />
          <StatBlock label="未读消息" value={summary.unreadMessages} color="#10B981" />
          <StatBlock label="待审合同" value={summary.pendingContracts} color="#EF4444" />
        </View>

        {error && !loading && (
          <View style={styles.errorBanner}>
            <Ionicons name="warning-outline" size={16} color="#DC2626" />
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity onPress={loadSummary}>
              <Text style={styles.retryText}>重试</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* 卡片网格 */}
        <View style={styles.grid}>
          {CARDS.map((card) => (
            <TouchableOpacity
              key={card.key}
              style={styles.card}
              activeOpacity={0.8}
              onPress={() => router.push(card.route as any)}
            >
              <View style={styles.cardIcon}>
                <Ionicons name={card.icon as any} size={22} color={Colors.primary} />
              </View>
              <Text style={styles.cardTitle}>{card.label}</Text>
              <Text style={styles.cardDesc}>{card.desc}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

function StatBlock({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <View style={[styles.statBlock, { borderLeftColor: color }]}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.background },
  container: { flex: 1 },
  content: { padding: Layout.spacing.lg, paddingBottom: Layout.spacing.xl * 2 },
  heading: {
    fontSize: 28,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 4,
  },
  subheading: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    marginBottom: Layout.spacing.lg,
  },
  summaryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Layout.spacing.sm,
    marginBottom: Layout.spacing.lg,
  },
  statBlock: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    borderLeftWidth: 3,
  },
  statValue: {
    fontSize: 22,
    fontWeight: '700',
    color: Colors.text,
  },
  statLabel: {
    fontSize: Layout.fontSize.xs,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    backgroundColor: '#FEE2E2',
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.md,
  },
  errorText: { flex: 1, fontSize: Layout.fontSize.sm, color: '#DC2626' },
  retryText: { fontSize: Layout.fontSize.sm, color: '#DC2626', fontWeight: '600' },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Layout.spacing.md,
  },
  card: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.lg,
    padding: Layout.spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  cardIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Layout.spacing.sm,
  },
  cardTitle: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  cardDesc: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 4 },
})
