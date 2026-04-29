/**
 * 任务中心列表（V3 P17-B 移动端）
 *
 * - 三段 Tab：进行中 / 待审批 / 已完成
 * - pull-to-refresh
 * - 长按任务卡片 → ActionSheet（取消 / 查看详情 / 复制 ID）
 * - 5s 轮询刷新
 * - 右上 + 按钮跳 modal new
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ActionSheetIOS,
  ActivityIndicator,
  Alert,
  Clipboard,
  FlatList,
  Platform,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'

import { TaskListItem } from '@/components/v3/tasks-mobile/TaskListItem'
import type { AgentTask, AgentTaskStatus } from '@/lib/api/agentTasks'
import { useAgentTasksStore } from '@/lib/store/agentTasksStore'
import { useTheme } from '@/lib/theme'

const POLL_INTERVAL_MS = 5_000

const TABS: { key: 'active' | 'approval' | 'finished'; label: string }[] = [
  { key: 'active', label: '进行中' },
  { key: 'approval', label: '待审批' },
  { key: 'finished', label: '已完成' },
]

const TAB_BUCKETS: Record<'active' | 'approval' | 'finished', AgentTaskStatus[]> = {
  active: ['queued', 'provisioning', 'running', 'reporting'],
  approval: ['needs_approval'],
  finished: ['done', 'failed', 'cancelled'],
}

export default function TasksIndexScreen() {
  const t = useTheme()
  const tasks = useAgentTasksStore((s) => s.tasks)
  const loading = useAgentTasksStore((s) => s.loading)
  const loadError = useAgentTasksStore((s) => s.loadError)
  const loadTasks = useAgentTasksStore((s) => s.loadTasks)
  const cancelTask = useAgentTasksStore((s) => s.cancelTask)

  const [tab, setTab] = useState<'active' | 'approval' | 'finished'>('active')
  const [refreshing, setRefreshing] = useState(false)

  // 初次 + 5s 轮询
  useEffect(() => {
    void loadTasks()
    const id = setInterval(() => {
      void loadTasks()
    }, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [loadTasks])

  const onRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await loadTasks()
    } finally {
      setRefreshing(false)
    }
  }, [loadTasks])

  const grouped = useMemo(() => {
    const buckets = {
      active: [] as AgentTask[],
      approval: [] as AgentTask[],
      finished: [] as AgentTask[],
    }
    for (const task of tasks) {
      if (TAB_BUCKETS.active.includes(task.status)) buckets.active.push(task)
      else if (TAB_BUCKETS.approval.includes(task.status)) buckets.approval.push(task)
      else if (TAB_BUCKETS.finished.includes(task.status)) buckets.finished.push(task)
    }
    return buckets
  }, [tasks])

  const visible = grouped[tab]

  const goDetail = useCallback((task: AgentTask) => {
    router.push(`/(tabs)/tasks/${task.id}`)
  }, [])

  const handleLongPress = useCallback(
    (task: AgentTask) => {
      const cancelable = TAB_BUCKETS.active.includes(task.status)
      const options = ['查看详情', '复制任务 ID']
      if (cancelable) options.push('取消任务')
      options.push('关闭')

      const cancelButtonIndex = options.length - 1
      const destructiveIndex = cancelable ? options.length - 2 : undefined

      const handleSelect = (idx: number) => {
        if (idx === cancelButtonIndex) return
        if (options[idx] === '查看详情') goDetail(task)
        else if (options[idx] === '复制任务 ID') {
          Clipboard.setString(task.id)
          // 简单反馈：用 Alert（不引入 Toast 库）
          Alert.alert('已复制', `任务 ID：${task.id}`)
        } else if (options[idx] === '取消任务') {
          Alert.alert('取消任务', `确定取消「${task.payload?.title ?? task.id}」？`, [
            { text: '保留', style: 'cancel' },
            {
              text: '取消任务',
              style: 'destructive',
              onPress: () => {
                void cancelTask(task.id)
              },
            },
          ])
        }
      }

      if (Platform.OS === 'ios') {
        ActionSheetIOS.showActionSheetWithOptions(
          {
            options,
            cancelButtonIndex,
            destructiveButtonIndex: destructiveIndex,
            title: task.payload?.title as string | undefined,
          },
          handleSelect,
        )
      } else {
        // Android: 用 Alert 模拟（避免引入额外依赖）
        Alert.alert(
          (task.payload?.title as string | undefined) ?? '操作',
          undefined,
          options.map((opt, i) => ({
            text: opt,
            style:
              i === cancelButtonIndex
                ? 'cancel'
                : i === destructiveIndex
                  ? 'destructive'
                  : 'default',
            onPress: () => handleSelect(i),
          })),
        )
      }
    },
    [cancelTask, goDetail],
  )

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: t.background }]} edges={['top']}>
      {/* 自定义 header */}
      <View style={[styles.header, { borderBottomColor: t.border }]}>
        <Text style={[styles.title, { color: t.text }]}>任务中心</Text>
        <Pressable
          onPress={() => router.push('/(tabs)/tasks/new')}
          hitSlop={10}
          style={({ pressed }) => [
            styles.addBtn,
            { backgroundColor: t.primary, opacity: pressed ? 0.85 : 1 },
          ]}
        >
          <Ionicons name="add" size={20} color="#fff" />
          <Text style={styles.addBtnText}>新建</Text>
        </Pressable>
      </View>

      {/* Tab 切换 */}
      <View style={[styles.tabBar, { borderBottomColor: t.border }]}>
        {TABS.map((it) => {
          const active = tab === it.key
          const count = grouped[it.key].length
          return (
            <Pressable
              key={it.key}
              onPress={() => setTab(it.key)}
              style={styles.tabItem}
              hitSlop={6}
            >
              <View style={styles.tabRow}>
                <Text
                  style={[
                    styles.tabLabel,
                    { color: active ? t.primaryDark : t.textSecondary },
                  ]}
                >
                  {it.label}
                </Text>
                {count > 0 && (
                  <View
                    style={[
                      styles.tabBadge,
                      { backgroundColor: active ? t.primary : t.border },
                    ]}
                  >
                    <Text
                      style={[
                        styles.tabBadgeText,
                        { color: active ? '#fff' : t.textSecondary },
                      ]}
                    >
                      {count}
                    </Text>
                  </View>
                )}
              </View>
              {active && <View style={[styles.tabUnderline, { backgroundColor: t.primary }]} />}
            </Pressable>
          )
        })}
      </View>

      {/* 列表 */}
      {loading && tasks.length === 0 ? (
        <View style={styles.loadingState}>
          <ActivityIndicator color={t.primary} />
          <Text style={[styles.loadingText, { color: t.textSecondary }]}>加载任务中...</Text>
        </View>
      ) : (
        <FlatList
          data={visible}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TaskListItem task={item} onPress={goDetail} onLongPress={handleLongPress} />
          )}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={t.primary}
            />
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={[styles.emptyEmoji, { opacity: 0.55 }]}>🗂️</Text>
              <Text style={[styles.emptyText, { color: t.textSecondary }]}>
                {tab === 'active' && '当前没有进行中的任务，点右上角创建一个吧'}
                {tab === 'approval' && '没有等待你审批的任务'}
                {tab === 'finished' && '尚未有已完成或失败的任务'}
              </Text>
            </View>
          }
          ListFooterComponent={
            loadError ? (
              <Text style={[styles.errText, { color: t.error }]}>加载失败：{loadError}</Text>
            ) : null
          }
          contentContainerStyle={visible.length === 0 ? styles.flexGrow : undefined}
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
  },
  addBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 999,
    gap: 4,
  },
  addBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
  tabBar: {
    flexDirection: 'row',
    paddingHorizontal: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 12,
  },
  tabRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  tabLabel: {
    fontSize: 14,
    fontWeight: '600',
  },
  tabBadge: {
    minWidth: 18,
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabBadgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  tabUnderline: {
    position: 'absolute',
    bottom: 0,
    height: 2,
    width: 36,
    borderRadius: 2,
  },
  loadingState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  loadingText: {
    fontSize: 13,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingVertical: 64,
  },
  emptyEmoji: {
    fontSize: 56,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
  errText: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 12,
  },
  flexGrow: {
    flexGrow: 1,
  },
})
