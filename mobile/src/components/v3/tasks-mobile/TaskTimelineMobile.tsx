/**
 * TaskTimelineMobile — 任务事件 timeline
 *
 * - VirtualizedList 倒序事件（最新在底部，符合"对话式"阅读习惯）
 * - 事件类型分色
 * - 自动滚到底部 + 上拉看更早
 */
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef } from 'react'
import {
  StyleSheet,
  Text,
  View,
  VirtualizedList,
  type ListRenderItemInfo,
} from 'react-native'

import type { TaskEvent, TaskEventType } from '@/lib/api/agentTasks'
import { useTheme } from '@/lib/theme'

const TYPE_META: Record<
  TaskEventType,
  { label: string; bg: string; fg: string; emoji: string }
> = {
  status_changed: { label: '状态变更', bg: '#E8F0FE', fg: '#1A73E8', emoji: '🔁' },
  progress: { label: '进度', bg: '#E6F4EA', fg: '#137333', emoji: '⏳' },
  tool_call: { label: '工具调用', bg: '#FEF7E0', fg: '#B06000', emoji: '🛠️' },
  tool_result: { label: '工具结果', bg: '#FCE8E6', fg: '#A50E0E', emoji: '📥' },
  error: { label: '错误', bg: '#FADBD8', fg: '#922B21', emoji: '⚠️' },
  done: { label: '完成', bg: '#D5F5E3', fg: '#196F3D', emoji: '✅' },
}

export interface TaskTimelineMobileHandle {
  scrollToBottom: () => void
}

interface Props {
  events: TaskEvent[]
  /** 自动滚到底部（新事件到达时）。默认 true */
  autoScroll?: boolean
}

export const TaskTimelineMobile = forwardRef<TaskTimelineMobileHandle, Props>(
  function TaskTimelineMobile({ events, autoScroll = true }, ref) {
    const t = useTheme()
    const listRef = useRef<VirtualizedList<TaskEvent>>(null)

    // 倒序：旧 -> 新（底部最新）
    const data = useMemo(
      () =>
        [...events].sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
        ),
      [events],
    )

    useImperativeHandle(ref, () => ({
      scrollToBottom: () => {
        const len = data.length
        if (len > 0) {
          listRef.current?.scrollToIndex({ index: len - 1, animated: true })
        }
      },
    }))

    // 新事件到达时自动滚到底部
    useEffect(() => {
      if (!autoScroll) return
      const len = data.length
      if (len === 0) return
      const id = setTimeout(() => {
        listRef.current?.scrollToIndex({ index: len - 1, animated: true })
      }, 50)
      return () => clearTimeout(id)
    }, [data.length, autoScroll])

    if (data.length === 0) {
      return (
        <View style={[styles.empty, { backgroundColor: t.surface }]}>
          <Text style={[styles.emptyText, { color: t.textMuted }]}>
            暂无事件，等待 Agent 推送进度...
          </Text>
        </View>
      )
    }

    return (
      <VirtualizedList<TaskEvent>
        ref={listRef}
        data={data}
        getItem={(d, i) => d[i]}
        getItemCount={(d) => d.length}
        keyExtractor={(item, i) => `${item.timestamp}-${item.event_type}-${i}`}
        renderItem={({ item }: ListRenderItemInfo<TaskEvent>) => (
          <EventRow event={item} theme={t} />
        )}
        contentContainerStyle={styles.listContent}
        onScrollToIndexFailed={({ index }) => {
          // VirtualizedList 在内容尚未测量完成时可能失败 —— 重试
          setTimeout(() => {
            listRef.current?.scrollToIndex({ index, animated: false })
          }, 100)
        }}
      />
    )
  },
)

interface EventRowProps {
  event: TaskEvent
  theme: ReturnType<typeof useTheme>
}

function EventRow({ event, theme }: EventRowProps) {
  const meta = TYPE_META[event.event_type] ?? TYPE_META.progress
  const time = new Date(event.timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
  const summary = renderPayload(event)

  return (
    <View style={styles.row}>
      <View style={styles.rail}>
        <View style={[styles.dot, { backgroundColor: meta.fg }]} />
      </View>
      <View
        style={[
          styles.bubble,
          { backgroundColor: theme.surface, borderColor: theme.border },
        ]}
      >
        <View style={styles.bubbleHeader}>
          <View style={[styles.typePill, { backgroundColor: meta.bg }]}>
            <Text style={[styles.typeText, { color: meta.fg }]}>
              {meta.emoji} {meta.label}
            </Text>
          </View>
          <Text style={[styles.time, { color: theme.textMuted }]}>{time}</Text>
        </View>
        <Text style={[styles.summary, { color: theme.text }]}>{summary}</Text>
      </View>
    </View>
  )
}

function renderPayload(ev: TaskEvent): string {
  const p = ev.payload ?? {}
  if (ev.event_type === 'progress' && typeof p.thought === 'string') {
    const pct = typeof p.percent === 'number' ? `（${p.percent}%）` : ''
    return `${p.thought}${pct}`
  }
  if (ev.event_type === 'status_changed') {
    return `${p.from ?? '?'} → ${p.to ?? '?'}`
  }
  if (ev.event_type === 'tool_call') {
    return `调用 ${p.tool ?? '?'}：${JSON.stringify(p.arguments ?? {})}`
  }
  if (ev.event_type === 'tool_result') {
    return p.summary ?? `${p.tool ?? '?'} 返回结果`
  }
  if (ev.event_type === 'done') {
    return p.summary ?? '任务已完成'
  }
  if (ev.event_type === 'error') {
    return p.message ?? '出现错误'
  }
  return JSON.stringify(p)
}

const styles = StyleSheet.create({
  empty: {
    padding: 24,
    margin: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 13,
  },
  listContent: {
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  row: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  rail: {
    width: 16,
    alignItems: 'center',
    paddingTop: 14,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  bubble: {
    flex: 1,
    marginLeft: 6,
    padding: 10,
    borderRadius: 10,
    borderWidth: StyleSheet.hairlineWidth,
  },
  bubbleHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  typePill: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 999,
  },
  typeText: {
    fontSize: 11,
    fontWeight: '600',
  },
  time: {
    fontSize: 11,
  },
  summary: {
    fontSize: 13,
    lineHeight: 19,
  },
})
