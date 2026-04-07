import { useEffect, useMemo, useState } from 'react'
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'
import type { ApprovalItem } from '@/types/api'

const approvalFilters = [
  { key: 'pending', label: '待审批' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已驳回' },
] as const

const fallbackApprovals: ApprovalItem[] = [
  { id: 'approval-1', title: '合同用印申请', type: 'contract', status: 'pending', priority: 1, created_at: '今天 09:30' },
  { id: 'approval-2', title: '外聘律师付款申请', type: 'expense', status: 'pending', priority: 2, created_at: '今天 11:10' },
  { id: 'approval-3', title: '资料共享授权', type: 'custom', status: 'approved', priority: 2, created_at: '昨天 17:40' },
]

export default function ApprovalsScreen() {
  const [filter, setFilter] = useState<(typeof approvalFilters)[number]['key']>('pending')
  const [approvals, setApprovals] = useState<ApprovalItem[]>(fallbackApprovals)

  useEffect(() => {
    loadApprovals()
  }, [])

  const loadApprovals = async () => {
    try {
      const result = await api.get<{ items: ApprovalItem[]; total: number }>('/approvals?page_size=20')
      if (result.items.length > 0) {
        setApprovals(result.items)
      }
    } catch {
      setApprovals(fallbackApprovals)
    }
  }

  const filteredApprovals = useMemo(
    () => approvals.filter((item) => item.status === filter),
    [approvals, filter]
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '审批处理' }} />
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

      <FlatList
        data={filteredApprovals}
        keyExtractor={(item) => item.id}
        contentContainerStyle={filteredApprovals.length === 0 ? styles.emptyContainer : styles.listContent}
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
              {item.status === 'pending' ? '等待处理' : item.status === 'approved' ? '已通过' : '已驳回'}
              {item.created_at ? ` · ${item.created_at}` : ''}
            </Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="git-compare-outline" size={48} color={Colors.textMuted} />
            <Text style={styles.emptyTitle}>当前没有审批记录</Text>
            <Text style={styles.emptyText}>后续会接入审批详情、批量处理和 SLA 提醒。</Text>
          </View>
        }
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
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
