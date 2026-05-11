/**
 * 任务详情（V3 P17-B 移动端）
 *
 * - timeline 自动滚到底部 + 上拉看更早（VirtualizedList 行为）
 * - 顶部状态卡 / 任务摘要 / 操作按钮（审批 / 取消）
 * - swipe back gesture 由 _layout 的 Stack gestureEnabled 提供
 * - 5s 轮询单条任务 + subscribeTaskEvents 流式事件
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import { Stack, useLocalSearchParams } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'

import { TaskApprovalSheet } from '@/components/v3/tasks-mobile/TaskApprovalSheet'
import { TaskStatusBadge } from '@/components/v3/tasks-mobile/TaskStatusBadge'
import {
  TaskTimelineMobile,
  type TaskTimelineMobileHandle,
} from '@/components/v3/tasks-mobile/TaskTimelineMobile'
import {
  agentTasksApi,
  type AgentTask,
  type AgentTaskStatus,
} from '@/lib/api/agentTasks'
import { useAgentTasksStore } from '@/lib/store/agentTasksStore'
import { useTheme } from '@/lib/theme'

const ACTIVE_STATUSES: AgentTaskStatus[] = [
  'queued',
  'provisioning',
  'running',
  'reporting',
]

export default function TaskDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const t = useTheme()
  const tasks = useAgentTasksStore((s) => s.tasks)
  const eventsMap = useAgentTasksStore((s) => s.events)
  const appendEvent = useAgentTasksStore((s) => s.appendEvent)
  const upsertTask = useAgentTasksStore((s) => s.upsertTask)
  const cancelTaskAction = useAgentTasksStore((s) => s.cancelTask)
  const approveAction = useAgentTasksStore((s) => s.approveTask)
  const rejectAction = useAgentTasksStore((s) => s.rejectTask)

  const [loading, setLoading] = useState(true)
  const [approvalOpen, setApprovalOpen] = useState(false)

  const timelineRef = useRef<TaskTimelineMobileHandle>(null)

  const task = useMemo(() => tasks.find((x) => x.id === id) ?? null, [tasks, id])
  const events = (id && eventsMap[id]) || []

  // 拉取一次任务详情（兜底，避免列表里没有该任务的情况）
  useEffect(() => {
    let cancelled = false
    if (!id) return
    setLoading(true)
    agentTasksApi
      .getTask(id)
      .then((tk) => {
        if (cancelled) return
        upsertTask(tk)
      })
      .catch(() => {
        // 列表已有则忽略
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, upsertTask])

  // 订阅事件 + 5s 轮询单任务
  useEffect(() => {
    if (!id) return
    const unsub = agentTasksApi.subscribeTaskEvents(id, (ev) => {
      appendEvent(id, ev)
    })
    const poll = setInterval(async () => {
      try {
        const fresh = await agentTasksApi.getTask(id)
        upsertTask(fresh)
      } catch {
        // ignore
      }
    }, 5_000)
    return () => {
      unsub()
      clearInterval(poll)
    }
  }, [id, appendEvent, upsertTask])

  const handleCancel = useCallback(() => {
    if (!task) return
    Alert.alert('取消任务', `确定取消「${task.payload?.title ?? task.id}」？`, [
      { text: '保留', style: 'cancel' },
      {
        text: '取消任务',
        style: 'destructive',
        onPress: () => {
          void cancelTaskAction(task.id)
        },
      },
    ])
  }, [task, cancelTaskAction])

  if (!task) {
    return (
      <>
        <Stack.Screen options={{ title: '任务详情' }} />
        <View style={[styles.loadingContainer, { backgroundColor: t.background }]}>
          {loading ? (
            <ActivityIndicator color={t.primary} />
          ) : (
            <Text style={[styles.loadingText, { color: t.textSecondary }]}>
              未找到任务（{id}）
            </Text>
          )}
        </View>
      </>
    )
  }

  const title = (task.payload?.title as string | undefined) ?? '任务详情'
  const userInput = (task.payload?.user_input as string | undefined) ?? ''
  const isActive = ACTIVE_STATUSES.includes(task.status)
  const needsApproval = task.status === 'needs_approval'

  return (
    <>
      <Stack.Screen options={{ title: title.length > 16 ? '任务详情' : title }} />
      <View style={[styles.container, { backgroundColor: t.background }]}>
        <ScrollView
          style={styles.headerScroll}
          contentContainerStyle={styles.headerContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={[styles.card, { backgroundColor: t.surface, borderColor: t.border }]}>
            <View style={styles.cardHeader}>
              <TaskStatusBadge status={task.status} />
              <Pressable
                onPress={() =>
                  timelineRef.current?.scrollToBottom()
                }
                hitSlop={6}
                style={styles.scrollBtn}
              >
                <Ionicons name="arrow-down-circle-outline" size={20} color={t.textSecondary} />
              </Pressable>
            </View>
            <Text style={[styles.cardTitle, { color: t.text }]}>{title}</Text>
            {userInput.length > 0 && (
              <Text style={[styles.cardDesc, { color: t.textSecondary }]} numberOfLines={4}>
                {userInput}
              </Text>
            )}
            <View style={styles.metaRow}>
              <Text style={[styles.metaLabel, { color: t.textMuted }]}>Persona</Text>
              <Text style={[styles.metaValue, { color: t.text }]}>{task.agent_persona}</Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={[styles.metaLabel, { color: t.textMuted }]}>创建时间</Text>
              <Text style={[styles.metaValue, { color: t.text }]}>
                {new Date(task.created_at).toLocaleString('zh-CN')}
              </Text>
            </View>
            {task.error && (
              <View style={[styles.errorBox, { backgroundColor: '#FADBD8' }]}>
                <Text style={styles.errorText}>{task.error.message}</Text>
              </View>
            )}
            {task.result && task.status === 'done' && (
              <View style={[styles.resultBox, { backgroundColor: '#D5F5E3' }]}>
                <Text style={styles.resultText}>
                  {(task.result.summary as string | undefined) ?? '任务已完成'}
                </Text>
              </View>
            )}
          </View>
        </ScrollView>

        {/* timeline 占主区域 */}
        <View style={styles.timelineWrap}>
          <Text style={[styles.sectionTitle, { color: t.textSecondary }]}>事件流</Text>
          <TaskTimelineMobile ref={timelineRef} events={events} />
        </View>

        {/* 底部操作 */}
        {(needsApproval || isActive) && (
          <View style={[styles.footer, { backgroundColor: t.background, borderTopColor: t.border }]}>
            {needsApproval && (
              <Pressable
                onPress={() => setApprovalOpen(true)}
                style={({ pressed }) => [
                  styles.footerBtn,
                  { backgroundColor: t.primary, opacity: pressed ? 0.85 : 1 },
                ]}
              >
                <Text style={styles.footerBtnText}>审批</Text>
              </Pressable>
            )}
            {isActive && (
              <Pressable
                onPress={handleCancel}
                style={({ pressed }) => [
                  styles.footerBtn,
                  styles.cancelBtn,
                  { borderColor: t.border, opacity: pressed ? 0.7 : 1 },
                ]}
              >
                <Text style={[styles.cancelText, { color: t.error }]}>取消任务</Text>
              </Pressable>
            )}
          </View>
        )}

        <TaskApprovalSheet
          visible={approvalOpen}
          task={task}
          onClose={() => setApprovalOpen(false)}
          onApprove={async (taskId) => {
            await approveAction(taskId)
          }}
          onReject={async (taskId, reason) => {
            await rejectAction(taskId, reason)
          }}
        />
      </View>
    </>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    fontSize: 13,
    marginTop: 8,
  },
  headerScroll: {
    maxHeight: 280,
  },
  headerContent: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 14,
    padding: 14,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  scrollBtn: {
    padding: 4,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 6,
  },
  cardDesc: {
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 10,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  metaLabel: {
    fontSize: 12,
  },
  metaValue: {
    fontSize: 12,
    fontWeight: '600',
  },
  errorBox: {
    marginTop: 10,
    padding: 10,
    borderRadius: 8,
  },
  errorText: {
    color: '#922B21',
    fontSize: 12,
    fontWeight: '600',
  },
  resultBox: {
    marginTop: 10,
    padding: 10,
    borderRadius: 8,
  },
  resultText: {
    color: '#196F3D',
    fontSize: 12,
    fontWeight: '600',
  },
  timelineWrap: {
    flex: 1,
    paddingTop: 8,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    paddingHorizontal: 20,
    marginBottom: 4,
  },
  footer: {
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 18,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  footerBtn: {
    flex: 1,
    paddingVertical: 13,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  footerBtnText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
  cancelBtn: {
    backgroundColor: 'transparent',
    borderWidth: StyleSheet.hairlineWidth,
  },
  cancelText: {
    fontSize: 15,
    fontWeight: '600',
  },
})
