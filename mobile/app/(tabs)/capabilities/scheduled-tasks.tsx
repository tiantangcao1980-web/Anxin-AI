// -*- coding: utf-8 -*-
import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { ScheduledTaskRow } from '@/components/v3/capabilities-mobile/ScheduledTaskRow'
import {
  scheduledTasksApi,
  type ScheduledTask,
  type ScheduleKind,
} from '@/lib/api/scheduledTasks'

/**
 * 定时任务列表页 — 4 类预设 filter (P17-D)
 *
 * 移动端:
 *   - pull-to-refresh
 *   - filter chips 横向滚动 (移动端 vs Web 的 sidebar)
 *   - Optimistic UI: Switch 即时反馈,失败回滚
 */

const KIND_LABEL: Record<ScheduleKind, string> = {
  contract_expiry_alert: '合同到期',
  case_status_daily: '案件日报',
  sentiment_weekly: '舆情周报',
  compliance_monthly: '合规巡检',
}

type FilterKey = 'all' | ScheduleKind

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'contract_expiry_alert', label: KIND_LABEL.contract_expiry_alert },
  { key: 'case_status_daily', label: KIND_LABEL.case_status_daily },
  { key: 'sentiment_weekly', label: KIND_LABEL.sentiment_weekly },
  { key: 'compliance_monthly', label: KIND_LABEL.compliance_monthly },
]

export default function ScheduledTasksScreen() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterKey>('all')

  const load = useCallback(async () => {
    try {
      const data = await scheduledTasksApi.list()
      setTasks(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载定时任务失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onRefresh = () => {
    setRefreshing(true)
    load()
  }

  const handleToggle = async (task: ScheduledTask, next: boolean) => {
    const target = next ? 'active' : 'paused'
    // Optimistic
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, status: target } : t)),
    )
    try {
      await scheduledTasksApi.toggle(task.id, target)
    } catch {
      // 回滚
      setTasks((prev) =>
        prev.map((t) => (t.id === task.id ? { ...t, status: task.status } : t)),
      )
    }
  }

  const filtered = useMemo(
    () => (filter === 'all' ? tasks : tasks.filter((t) => t.kind === filter)),
    [tasks, filter],
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <View style={styles.filterRow}>
        <FlatList
          data={FILTERS}
          horizontal
          keyExtractor={(it) => it.key}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filterContent}
          renderItem={({ item }) => {
            const active = item.key === filter
            const count = item.key === 'all' ? tasks.length : tasks.filter((t) => t.kind === item.key).length
            return (
              <TouchableOpacity
                style={[styles.chip, active && styles.chipActive]}
                onPress={() => setFilter(item.key)}
                activeOpacity={0.8}
              >
                <Text style={[styles.chipText, active && styles.chipTextActive]}>
                  {item.label} {count > 0 && `· ${count}`}
                </Text>
              </TouchableOpacity>
            )
          }}
        />
      </View>
      {loading && tasks.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : error && tasks.length === 0 ? (
        <View style={styles.centered}>
          <Ionicons name="cloud-offline-outline" size={48} color={Colors.textMuted} />
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity
            style={styles.retryBtn}
            onPress={() => {
              setLoading(true)
              load()
            }}
            activeOpacity={0.8}
          >
            <Text style={styles.retryText}>重试</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(t) => t.id}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
          }
          renderItem={({ item }) => (
            <ScheduledTaskRow task={item} onToggle={handleToggle} />
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="time-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyText}>该分类下还没有定时任务</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  filterRow: {
    paddingVertical: Layout.spacing.sm,
    backgroundColor: Colors.background,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  filterContent: { paddingHorizontal: Layout.spacing.md, gap: 8 },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: Colors.surface,
    marginRight: 8,
  },
  chipActive: { backgroundColor: Colors.primary },
  chipText: { fontSize: Layout.fontSize.sm, color: Colors.textSecondary },
  chipTextActive: { color: Colors.white, fontWeight: '600' },
  empty: { alignItems: 'center', paddingVertical: 60, gap: 12 },
  emptyText: { color: Colors.textSecondary, fontSize: Layout.fontSize.sm },
  errorText: { color: Colors.textSecondary, fontSize: Layout.fontSize.sm, marginTop: 12, textAlign: 'center', paddingHorizontal: 24 },
  retryBtn: {
    marginTop: 16,
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: Colors.primary,
  },
  retryText: { color: Colors.white, fontWeight: '600', fontSize: Layout.fontSize.sm },
})
