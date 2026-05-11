// -*- coding: utf-8 -*-
/**
 * PersonaCard —— 智能体卡片
 *
 * 用于 home 横向滚动 / personas 分包入口列表。
 * 点击行为由父组件 onClick 决定（通常是跳到 /subpackages/personas/detail/index?id=xx）。
 */

import { View, Text } from '@tarojs/components'
import type { Persona } from '../../types/persona'
import { domainPalette } from '../../utils/theme/colors'
import './index.scss'

interface PersonaCardProps {
  persona: Persona
  /** 紧凑模式：home 横向 scroll 时使用 */
  compact?: boolean
  onClick?: (persona: Persona) => void
}

export default function PersonaCard(props: PersonaCardProps) {
  const { persona, compact = false, onClick } = props
  const accent = persona.domain
    ? domainPalette[persona.domain] || '#D4A574'
    : '#D4A574'

  const handle = () => {
    onClick?.(persona)
  }

  return (
    <View
      className={`persona-card ${compact ? 'persona-card--compact' : ''}`}
      style={`border-top: 6rpx solid ${accent};`}
      onClick={handle}
    >
      <View className='persona-card__head'>
        <Text className='persona-card__emoji'>{persona.emoji}</Text>
        {persona.is_implemented === false ? (
          <Text className='persona-card__badge persona-card__badge--planning'>规划中</Text>
        ) : (
          <Text className='persona-card__badge persona-card__badge--ready'>可用</Text>
        )}
      </View>
      <Text className='persona-card__name'>{persona.display_name}</Text>
      <Text className='persona-card__desc' numberOfLines={2}>
        {persona.description}
      </Text>
      {!compact && persona.capabilities?.length ? (
        <View className='persona-card__caps'>
          {persona.capabilities.slice(0, 3).map((c, i) => (
            <Text key={i} className='persona-card__cap'>
              · {c}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  )
}
