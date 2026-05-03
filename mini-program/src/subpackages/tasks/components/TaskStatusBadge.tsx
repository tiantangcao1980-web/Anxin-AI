// -*- coding: utf-8 -*-
/**
 * TaskStatusBadge —— 任务状态徽章
 *
 * - 8 状态颜色（来自 statusMap）
 * - running 状态下小圆点脉冲动画
 */

import { View, Text } from '@tarojs/components'
import type { AgentTaskStatus } from '../../../types/agentTask'
import { STATUS_META } from '../_lib/statusMap'
import './TaskStatusBadge.scss'

interface TaskStatusBadgeProps {
  status: AgentTaskStatus
  size?: 'sm' | 'md'
}

export default function TaskStatusBadge(props: TaskStatusBadgeProps) {
  const { status, size = 'sm' } = props
  const meta = STATUS_META[status]
  const cls = `tsb tsb--${size}${meta.pulse ? ' tsb--pulse' : ''}`
  const style = `background-color: ${meta.bg}; color: ${meta.fg}; border-color: ${meta.border};`
  return (
    <View className={cls} style={style}>
      {meta.pulse ? <View className='tsb__dot' style={`background-color: ${meta.fg};`} /> : null}
      <Text className='tsb__text'>{meta.label}</Text>
    </View>
  )
}
