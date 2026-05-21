import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'
import type { ApprovalItem } from '@/types/api'
import { DomainStripe } from '@/components/DomainBadge'
import { DomainBreadcrumb } from '@/components/DomainBreadcrumb'

const approvalFilters = [
  { key: 'pending', label: '待审批' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已驳回' },
] as const

export default function ApprovalsScreen() {
  const [filter, setFilter] = useState<(typeof approvalFilters)[number]['key']>('pending')
  const [approvals, setApprovals] = useState<ApprovalItem[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadApprovals = useCallback(async () => {
    try {
      setError(null)
      const result = await api.get<{ items: ApprovalItem[]; total: number }>(
        '/approvals?page_size=50',
      )
      setApprovals(result.items ?? [])
    } catch (err: any) {
      setApprovals([])
      setError(err?.message || '加载审批失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadApprovals()
  }, [loadApprovals])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadApprovals()
  }, [loadApprovals])

  const filteredApprovals = useMemo(
    () => approvals.filter((item) => item.status === filter),
    [approvals, filter]
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '审批处理' }} />
      {/* V3 合规域视觉锚点 — 4pt 高警示橙红彩条 + 紧凑面包屑 */}
      <DomainStripe domain="compliance" />
      <View style={{ paddingHorizontal: 16, paddingVertical: 8 }}>
        <DomainBreadcrumb domain="compliance" compact />
      </View>
      <View style={styles.filterRow}>
        {approvalFilters.map((item) => {
          const count = approvals.filter((approval) => approval.status === item.key).length
          const active = filter === item.key
          return (
            <TouchableOpacity
              key={item.key}
              style={[styles.filterChip, active && styles.filterChipActive]}
              onPress={() => setFilter(item.key)}
              activeOpacity={0.8}
            >
              <Text style={[styles.filterText, active && styles.filterTextActive]}>
                {item.label} · {count}
              </Text>
            </TouchableOpacity>
          )
        })}
      </View>

      {loading && approvals.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          data={filteredApprovals}
          keyExtractor={(item) => item.id}
          contentContainerStyle={
            filteredApprovals.length === 0 ? styles.emptyContainer : styles.listContent
          }
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={Colors.primary}
            />
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              activeOpacity={0.8}
              onPress={() =>
                router.push({
                  pathname: '/approvals/[id]',
                  params: {
                    id: item.id,
                    title: item.title,
                    type: item.type,
                    status: item.status,
                    description: item.description,
                  },
                })
              }
            >
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                <View style={styles.typeBadge}>
                  <Text style={styles.typeBadgeText}>{item.type}</Text>
                </View>
              </View>
              <Text style={styles.cardMeta}>
                {item.status === 'pending'
                  ? '等待处理'
                  : item.status === 'approved'
                    ? '已通过'
                    : '已驳回'}
                {item.created_at ? ` · ${item.created_at}` : ''}
              </Text>
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            error ? (
              <View style={styles.emptyState}>
                <Ionicons name="cloud-offline-outline" size={48} color="#DC2626" />
                <Text style={[styles.emptyTitle, { color: '#DC2626' }]}>{error}</Text>
                <TouchableOpacity style={styles.retryBtn} onPress={loadApprovals}>
                  <Text style={styles.retryBtnText}>点击重试</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.emptyState}>
                <Ionicons name="git-compare-outline" size={48} color={Colors.textMuted} />
                <Text style={styles.emptyTitle}>当前没有审批记录</Text>
                <Text style={styles.emptyText}>下拉可刷新。</Text>
              </View>
            )
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  retryBtn: {
    marginTop: Layout.spacing.md,
    paddingHorizontal: Layout.spacing.lg,
    paddingVertical: Layout.spacing.sm,
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.md,
  },
  retryBtnText: {
    fontSize: Layout.fontSize.sm,
    color: Colors.white,
    fontWeight: '500',
  },
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Layout.spacing.sm,
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.md,
  },
  filterChip: {
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    borderRadius: Layout.borderRadius.md,
    backgroundColor: Colors.surface,
  },
  filterChipActive: {
    backgroundColor: Colors.primary,
  },
  filterText: {
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    fontWeight: '500',
  },
  filterTextActive: {
    color: Colors.white,
  },
  listContent: {
    padding: Layout.spacing.md,
  },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: Layout.spacing.lg,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: Layout.spacing.sm,
    alignItems: 'center',
  },
  cardTitle: {
    flex: 1,
    color: Colors.text,
    fontSize: Layout.fontSize.md,
    fontWeight: '600',
  },
  typeBadge: {
    backgroundColor: Colors.primary + '15',
    borderRadius: Layout.borderRadius.sm,
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 4,
  },
  typeBadgeText: {
    color: Colors.primary,
    fontSize: Layout.fontSize.xs,
    fontWeight: '600',
  },
  cardMeta: {
    marginTop: Layout.spacing.xs,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
  },
  emptyState: {
    alignItems: 'center',
  },
  emptyTitle: {
    marginTop: Layout.spacing.md,
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    fontWeight: '600',
  },
  emptyText: {
    marginTop: Layout.spacing.xs,
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
})
