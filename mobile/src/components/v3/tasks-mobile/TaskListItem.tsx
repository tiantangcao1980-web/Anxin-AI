/**
 * TaskListItem — 任务列表卡片
 *
 * 布局：左 emoji 头像 / 中标题+状态+时间 / 右展开箭头
 * 触屏交互：Pressable + onPress / onLongPress（外部传入弹 ActionSheet）
 */
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'

import type { AgentTask } from '@/lib/api/agentTasks'
import { useTheme } from '@/lib/theme'

import { TaskStatusBadge } from './TaskStatusBadge'

const PERSONA_EMOJI: Record<string, string> = {
  anxin_assistant: '🤖',
  contract_steward: '📑',
  investigator: '🔎',
  litigator: '⚖️',
}

const PERSONA_LABEL: Record<string, string> = {
  anxin_assistant: '安心助手',
  contract_steward: '合同管家',
  investigator: '调查员',
  litigator: '诉讼专员',
}

interface Props {
  task: AgentTask
  onPress: (task: AgentTask) => void
  onLongPress?: (task: AgentTask) => void
}

export function TaskListItem({ task, onPress, onLongPress }: Props) {
  const t = useTheme()
  const title =
    (task.payload?.title as string | undefined) ??
    (task.payload?.user_input as string | undefined)?.slice(0, 28) ??
    '未命名任务'
  const emoji = PERSONA_EMOJI[task.agent_persona] ?? '🧠'
  const personaLabel = PERSONA_LABEL[task.agent_persona] ?? task.agent_persona

  const updatedAt = formatRelative(task.updated_at)

  return (
    <Pressable
      onPress={() => onPress(task)}
      onLongPress={() => onLongPress?.(task)}
      delayLongPress={350}
      android_ripple={{ color: t.border }}
      style={({ pressed }) => [
        styles.card,
        { backgroundColor: t.surface, borderColor: t.border },
        pressed && { opacity: 0.85 },
      ]}
    >
      <View style={[styles.avatar, { backgroundColor: t.background, borderColor: t.border }]}>
        <Text style={styles.avatarEmoji}>{emoji}</Text>
      </View>
      <View style={styles.body}>
        <Text style={[styles.title, { color: t.text }]} numberOfLines={2}>
          {title}
        </Text>
        <View style={styles.metaRow}>
          <TaskStatusBadge status={task.status} size="sm" />
          <Text style={[styles.persona, { color: t.textSecondary }]}>· {personaLabel}</Text>
        </View>
        <Text style={[styles.time, { color: t.textMuted }]}>{updatedAt}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={t.textMuted} style={styles.chevron} />
    </Pressable>
  )
}

function formatRelative(iso: string): string {
  const d = new Date(iso).getTime()
  if (Number.isNaN(d)) return ''
  const diff = Math.floor((Date.now() - d) / 1000)
  if (diff < 60) return `${diff} 秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86_400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86_400)} 天前`
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    marginHorizontal: 16,
    marginVertical: 6,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: StyleSheet.hairlineWidth,
    marginRight: 12,
  },
  avatarEmoji: {
    fontSize: 22,
  },
  body: {
    flex: 1,
  },
  title: {
    fontSize: 15,
    fontWeight: '600',
    lineHeight: 20,
    marginBottom: 6,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  persona: {
    fontSize: 12,
    marginLeft: 6,
  },
  time: {
    fontSize: 11,
  },
  chevron: {
    marginLeft: 6,
  },
})
