import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Stack, useLocalSearchParams } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { getTaskActions } from '@/features/workflow/detail-model'
import { api } from '@/services/api'
import type { TaskItem } from '@/types/api'

const fallbackTask: TaskItem = {
  id: 'fallback-task',
  title: '待处理任务',
  description: '任务详情将在这里展示。',
  status: 'todo',
  priority: 'medium',
  tags: [],
}

export default function TaskDetailScreen() {
  const params = useLocalSearchParams<{
    id: string
    title?: string
    description?: string
    status?: TaskItem['status']
    priority?: TaskItem['priority']
    dueDate?: string
    tags?: string
  }>()
  const [task, setTask] = useState<TaskItem>({
    ...fallbackTask,
    id: params.id || fallbackTask.id,
    title: params.title || fallbackTask.title,
    description: params.description || fallbackTask.description,
    status: params.status || fallbackTask.status,
    priority: params.priority || fallbackTask.priority,
    dueDate: params.dueDate,
    tags: params.tags ? params.tags.split('|').filter(Boolean) : [],
  })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const loadTaskFromList = async () => {
      if (!params.id) {
        return
      }
      try {
        const result = await api.get<{ items: TaskItem[]; total: number }>('/tasks/?page_size=50')
        const found = result.items.find((item) => item.id === params.id)
        if (found) {
          setTask(found)
        }
      } catch {
      }
    }

    loadTaskFromList()
  }, [params.id])

  const actions = useMemo(() => getTaskActions(task.status), [task.status])

  const handleTransition = async (nextStatus: TaskItem['status']) => {
    if (!params.id) {
      return
    }
    setSubmitting(true)
    try {
      const updated = await api.put<TaskItem>(`/tasks/${params.id}/transition`, { status: nextStatus })
      setTask(updated)
      Alert.alert('已更新', nextStatus === 'done' ? '任务已标记完成' : '任务状态已更新')
    } catch (error: any) {
      Alert.alert('操作失败', error?.message || '任务状态更新失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '任务详情' }} />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.heroCard}>
          <View style={styles.heroHeader}>
            <Text style={styles.title}>{task.title}</Text>
            <View style={styles.priorityBadge}>
              <Text style={styles.priorityBadgeText}>
                {task.priority === 'high' ? '高优先级' : task.priority === 'medium' ? '中优先级' : '低优先级'}
              </Text>
            </View>
          </View>
          <Text style={styles.statusText}>
            {task.status === 'todo' ? '待办' : task.status === 'in_progress' ? '进行中' : '已完成'}
          </Text>
          <Text style={styles.description}>{task.description || '暂无任务说明'}</Text>
        </View>

        <View style={styles.metaCard}>
          <Text style={styles.sectionTitle}>任务信息</Text>
          <Text style={styles.metaRow}>截止时间：{task.dueDate || '未设置'}</Text>
          <Text style={styles.metaRow}>标签：{task.tags.length > 0 ? task.tags.join(' · ') : '暂无标签'}</Text>
          <Text style={styles.metaRow}>负责人：{task.assignee || '待分配'}</Text>
        </View>

        <View style={styles.metaCard}>
          <Text style={styles.sectionTitle}>可执行动作</Text>
          {actions.map((action) => (
            <TouchableOpacity
              key={action.label}
              style={[styles.actionButton, action.tone === 'secondary' && styles.actionButtonSecondary]}
              onPress={() => handleTransition(action.nextStatus)}
              disabled={submitting}
              activeOpacity={0.8}
            >
              <Ionicons
                name={action.nextStatus === 'done' ? 'checkmark-circle-outline' : 'play-circle-outline'}
                size={18}
                color={action.tone === 'secondary' ? Colors.primary : Colors.white}
              />
              <Text style={[styles.actionButtonText, action.tone === 'secondary' && styles.actionButtonTextSecondary]}>
                {submitting ? '处理中...' : action.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
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
  heroHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: Layout.spacing.sm,
  },
  title: {
    flex: 1,
    color: Colors.text,
    fontSize: Layout.fontSize.xl,
    fontWeight: '700',
  },
  priorityBadge: {
    backgroundColor: Colors.primary + '15',
    borderRadius: Layout.borderRadius.sm,
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 4,
  },
  priorityBadgeText: {
    color: Colors.primary,
    fontSize: Layout.fontSize.xs,
    fontWeight: '600',
  },
  statusText: {
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
  actionButton: {
    marginTop: Layout.spacing.sm,
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.md,
    paddingVertical: Layout.spacing.md,
    paddingHorizontal: Layout.spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Layout.spacing.sm,
  },
  actionButtonSecondary: {
    backgroundColor: Colors.primary + '12',
  },
  actionButtonText: {
    color: Colors.white,
    fontWeight: '600',
    fontSize: Layout.fontSize.sm,
  },
  actionButtonTextSecondary: {
    color: Colors.primary,
  },
})
