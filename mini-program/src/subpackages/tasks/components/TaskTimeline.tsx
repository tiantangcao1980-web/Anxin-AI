// -*- coding: utf-8 -*-
/**
 * TaskTimeline —— 任务事件流（按时间倒序）
 *
 * 6 事件类型：
 *   status_changed → 状态徽章卡（中性）
 *   progress       → 灰卡 + thought
 *   tool_call      → 蓝卡 + tool name + arguments JSON 折叠
 *   tool_result    → 浅绿卡 + result 摘要
 *   error          → 红卡 + traceback
 *   done           → 绿卡 + summary
 */

import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import type { TaskEvent } from '../../../types/agentTask'
import { relativeTime } from '../_lib/statusMap'
import './TaskTimeline.scss'

interface Props {
  events: TaskEvent[]
}

export default function TaskTimeline({ events }: Props) {
  if (!events || events.length === 0) {
    return (
      <View className='timeline timeline--empty'>
        <Text className='timeline__empty-text'>暂无事件</Text>
      </View>
    )
  }

  // 倒序展示（最新在上）
  const ordered = [...events].sort((a, b) =>
    a.timestamp < b.timestamp ? 1 : a.timestamp > b.timestamp ? -1 : 0,
  )

  return (
    <View className='timeline'>
      {ordered.map((ev, i) => (
        <TimelineItem event={ev} key={`${ev.timestamp}-${i}`} />
      ))}
    </View>
  )
}

function TimelineItem({ event }: { event: TaskEvent }) {
  const [expanded, setExpanded] = useState(false)
  const variant = variantOf(event.event_type)
  const meta = renderMeta(event)
  const time = relativeTime(event.timestamp)

  return (
    <View className={`tl-item tl-item--${variant}`}>
      <View className='tl-item__bullet' />
      <View className='tl-item__body'>
        <View className='tl-item__head'>
          <Text className='tl-item__type'>{meta.title}</Text>
          <Text className='tl-item__time'>{time}</Text>
        </View>
        {meta.body ? (
          <Text className='tl-item__body-text' numberOfLines={4}>
            {meta.body}
          </Text>
        ) : null}
        {meta.code ? (
          <View className='tl-item__code-wrap' onClick={() => setExpanded((s) => !s)}>
            <Text className='tl-item__code-toggle'>
              {expanded ? '收起 ▾' : '展开 JSON ▸'}
            </Text>
            {expanded ? (
              <Text className='tl-item__code'>{meta.code}</Text>
            ) : null}
          </View>
        ) : null}
      </View>
    </View>
  )
}

type Variant = 'status' | 'progress' | 'tool-call' | 'tool-result' | 'error' | 'done'

function variantOf(type: TaskEvent['event_type']): Variant {
  switch (type) {
    case 'status_changed':
      return 'status'
    case 'progress':
      return 'progress'
    case 'tool_call':
      return 'tool-call'
    case 'tool_result':
      return 'tool-result'
    case 'error':
      return 'error'
    case 'done':
      return 'done'
    default:
      return 'progress'
  }
}

interface Meta {
  title: string
  body?: string
  code?: string
}

function renderMeta(event: TaskEvent): Meta {
  const p = event.payload || {}
  switch (event.event_type) {
    case 'status_changed': {
      const from = (p.from as string) || '空'
      const to = (p.to as string) || '?'
      const reason = p.reason as string | undefined
      return {
        title: `状态变更：${from} → ${to}`,
        body: reason,
      }
    }
    case 'progress':
      return {
        title: '进度',
        body: (p.thought as string) || (p.message as string) || JSON.stringify(p),
      }
    case 'tool_call': {
      const tool = (p.tool as string) || '工具'
      return {
        title: `调用工具：${tool}`,
        body: `参数：`,
        code: tryStringify(p.arguments),
      }
    }
    case 'tool_result': {
      const tool = (p.tool as string) || '工具'
      return {
        title: `工具返回：${tool}`,
        body: (p.summary as string) || '已完成',
      }
    }
    case 'error':
      return {
        title: '错误',
        body: (p.message as string) || '执行出错',
        code: (p.traceback as string) || undefined,
      }
    case 'done':
      return {
        title: '完成',
        body: (p.summary as string) || '任务执行完成',
      }
    default:
      return { title: event.event_type, body: JSON.stringify(p) }
  }
}

function tryStringify(v: unknown): string {
  if (v === undefined || v === null) return '{}'
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}
