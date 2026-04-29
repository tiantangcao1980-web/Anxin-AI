// -*- coding: utf-8 -*-
/**
 * EmptyState —— 空状态 / 错误状态通用组件
 */

import { View, Text } from '@tarojs/components'
import './index.scss'

interface EmptyStateProps {
  emoji?: string
  title: string
  description?: string
  actionText?: string
  onAction?: () => void
}

export default function EmptyState(props: EmptyStateProps) {
  const { emoji = '📭', title, description, actionText, onAction } = props
  return (
    <View className='empty-state'>
      <Text className='empty-state__emoji'>{emoji}</Text>
      <Text className='empty-state__title'>{title}</Text>
      {description ? (
        <Text className='empty-state__desc'>{description}</Text>
      ) : null}
      {actionText && onAction ? (
        <View className='empty-state__action' onClick={onAction}>
          <Text className='empty-state__action-text'>{actionText}</Text>
        </View>
      ) : null}
    </View>
  )
}
