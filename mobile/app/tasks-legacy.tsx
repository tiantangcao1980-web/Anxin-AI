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
import type { TaskItem } from '@/types/api'

const taskFilters = [
  { key: 'todo', label: '待办' },
  { key: 'in_progress', label: '进行中' },
  { key: 'done', label: '已完成' },
] as const

export default function TasksScreen() {
  const [filter, setFilter] = useState<(typeof taskFilters)[number]['key']>('todo')
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadTasks = useCallback(async () => {
    try {
      setError(null)
      const result = await api.get<{ items: TaskItem[]; total: number }>('/tasks/?page_size=50')
      setTasks(result.items ?? [])
    } catch (err: any) {
      setTasks([])
      setError(err?.message || '加载任务失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadTasks()
  }, [loadTasks])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadTasks()
  }, [loadTasks])

  const filteredTasks = useMemo(
    () => tasks.filter((item) => item.status === filter),
    [filter, tasks]
  )

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '任务中心' }} />
      <View style={styles.summaryRow}>
        {taskFilters.map((item) => {
          const count = tasks.filter((task) => task.status === item.key).length
          const active = filter === item.key
          return (
            <TouchableOpacity
              key={item.key}
              style={[styles.summaryCard, active && styles.summaryCardActive]}
              onPress={() => setFilter(item.key)}
              activeOpacity={0.8}
            >
              <Text style={[styles.summaryValue, active && styles.summaryValueActive]}>{count}</Text>
              <Text style={[styles.summaryLabel, active && styles.summaryLabelActive]}>{item.label}</Text>
            </TouchableOpacity>
          )
        })}
      </View>

      {loading && tasks.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          data={filteredTasks}
          keyExtractor={(item) => item.id}
          contentContainerStyle={
            filteredTasks.length === 0 ? styles.emptyContainer : styles.listContent
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
                  pathname: '/tasks/[id]',
                  params: {
                    id: item.id,
                    title: item.title,
                    description: item.description,
                    status: item.status,
                    priority: item.priority,
                    dueDate: item.dueDate,
                    tags: item.tags.join('|'),
                  },
                })
              }
            >
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                <Text style={styles.priorityText}>
                  {item.priority === 'high' ? '高' : item.priority === 'medium' ? '中' : '低'}
                </Text>
              </View>
              <Text style={styles.cardMeta}>
                {(item.tags.length > 0 ? item.tags.join(' · ') : '任务') +
                  (item.dueDate ? ` · 截止 ${item.dueDate}` : '')}
              </Text>
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            error ? (
              <View style={styles.emptyState}>
                <Ionicons name="cloud-offline-outline" size={48} color="#DC2626" />
                <Text style={[styles.emptyTitle, { color: '#DC2626' }]}>{error}</Text>
                <TouchableOpacity style={styles.retryBtn} onPress={loadTasks}>
                  <Text style={styles.retryBtnText}>点击重试</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.emptyState}>
                <Ionicons name="checkbox-outline" size={48} color={Colors.textMuted} />
                <Text style={styles.emptyTitle}>当前筛选下暂无任务</Text>
                <Text style={styles.emptyText}>
                  下拉可刷新；新建任务会同步出现在这里。
                </Text>
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
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
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
  summaryRow: {
    flexDirection: 'row',
    paddingHorizontal: Layout.spacing.md,
    gap: Layout.spacing.sm,
    marginTop: Layout.spacing.sm,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    paddingVertical: Layout.spacing.md,
    alignItems: 'center',
  },
  summaryCardActive: {
    backgroundColor: Colors.primary,
  },
  summaryValue: {
    fontSize: Layout.fontSize.xl,
    color: Colors.text,
    fontWeight: '700',
  },
  summaryValueActive: {
    color: Colors.white,
  },
  summaryLabel: {
    marginTop: Layout.spacing.xs,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.xs,
  },
  summaryLabelActive: {
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
    alignItems: 'center',
    gap: Layout.spacing.sm,
  },
  cardTitle: {
    flex: 1,
    color: Colors.text,
    fontWeight: '600',
    fontSize: Layout.fontSize.md,
  },
  priorityText: {
    color: Colors.primary,
    fontSize: Layout.fontSize.xs,
    fontWeight: '700',
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
    fontWeight: '600',
    color: Colors.text,
  },
  emptyText: {
    marginTop: Layout.spacing.xs,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    textAlign: 'center',
  },
})
