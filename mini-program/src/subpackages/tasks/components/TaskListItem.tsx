// -*- coding: utf-8 -*-
/**
 * TaskListItem —— 任务列表卡片
 *
 * - persona emoji + 标题（payload.title 或截取 user_input）
 * - 相对时间 + status badge
 * - 失败 / 已完成 时显示摘要
 */

import { View, Text } from '@tarojs/components'
import type { AgentTask } from '../../../types/agentTask'
import TaskStatusBadge from './TaskStatusBadge'
import { findPersona } from '../_lib/personas'
import { relativeTime, taskTitleOf } from '../_lib/statusMap'
import './TaskListItem.scss'

interface Props {
  task: AgentTask
  onClick?: (task: AgentTask) => void
}

export default function TaskListItem({ task, onClick }: Props) {
  const persona = findPersona(task.agent_persona)
  const title = taskTitleOf(task.payload, task.id)
  const subtitle =
    typeof task.payload?.user_input === 'string' && task.payload.title
      ? (task.payload.user_input as string)
      : ''
  const showFailHint = task.status === 'failed' && task.error?.message
  const showDoneHint =
    task.status === 'done' && task.result && typeof task.result.summary === 'string'

  return (
    <View className='task-card' onClick={() => onClick?.(task)} hoverClass='task-card--hover'>
      <View className='task-card__head'>
        <Text className='task-card__emoji'>{persona.emoji}</Text>
        <View className='task-card__head-text'>
          <Text className='task-card__name'>{persona.name}</Text>
          <Text className='task-card__time'>{relativeTime(task.updated_at || task.created_at)}</Text>
        </View>
        <TaskStatusBadge status={task.status} />
      </View>

      <Text className='task-card__title' numberOfLines={2}>
        {title}
      </Text>

      {subtitle ? (
        <Text className='task-card__sub' numberOfLines={1}>
          {subtitle}
        </Text>
      ) : null}

      {showFailHint ? (
        <View className='task-card__hint task-card__hint--fail'>
          <Text className='task-card__hint-text' numberOfLines={2}>
            {task.error?.message}
          </Text>
        </View>
      ) : null}

      {showDoneHint ? (
        <View className='task-card__hint task-card__hint--done'>
          <Text className='task-card__hint-text' numberOfLines={2}>
            {String(task.result?.summary)}
          </Text>
        </View>
      ) : null}
    </View>
  )
}
