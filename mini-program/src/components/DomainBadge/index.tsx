// -*- coding: utf-8 -*-
/**
 * DomainBadge — 业务域可视化原子组件 (Mini Program / Taro)
 *
 * 与 frontend `components/ui/domain.tsx` 和 mobile `components/DomainBadge.tsx`
 * 视觉对齐 — 同一套 8 大业务域、同一套色板（来自 `styles/design-tokens.ts`）。
 *
 * 用法：
 *   import DomainBadge, { DomainStripe } from '@/components/DomainBadge'
 *   <DomainBadge domain='legal' />
 *   <DomainStripe domain='finance' />
 *
 * 设计约束：
 * - 仅做"分类标识"，主行动按钮 / tabBar selectedColor 仍走品牌橙 `#D4A574`
 * - 与 riskTier 状态色互不重叠（风险是状态，域是分类）
 */

import { Text, View } from '@tarojs/components'
import { domain, type DomainId } from '@/styles/design-tokens'
import './index.scss'

// 域 → emoji 图标（小程序受限，避免引入外部图标 SVG 包）
const DOMAIN_EMOJI: Record<DomainId, string> = {
  legal: '⚖️',
  finance: '💰',
  tax: '🏛️',
  compliance: '🛡️',
  operations: '📊',
  growth: '🧭',
  content: '✍️',
  global: '🌐',
}

interface DomainBadgeProps {
  domain: DomainId
  /** 是否显示图标（默认 true） */
  showIcon?: boolean
  /** 是否显示文字（默认 true） */
  showLabel?: boolean
  /** 容器自定义类名（外部覆盖样式） */
  className?: string
}

export default function DomainBadge(props: DomainBadgeProps) {
  const { domain: domainId, showIcon = true, showLabel = true, className = '' } = props
  const meta = domain[domainId]
  return (
    <View
      className={`domain-badge ${className}`}
      style={{
        backgroundColor: meta.surface,
        color: meta.color,
      }}
    >
      {showIcon ? <Text className='domain-badge__icon'>{DOMAIN_EMOJI[domainId]}</Text> : null}
      {showLabel ? (
        <Text className='domain-badge__label' style={{ color: meta.color }}>
          {meta.labelZh}
        </Text>
      ) : null}
    </View>
  )
}

interface DomainStripeProps {
  domain: DomainId
  className?: string
}

/** 4rpx 高的顶部业务域彩条，用于域内页面顶部识别 */
export function DomainStripe(props: DomainStripeProps) {
  const { domain: domainId, className = '' } = props
  const meta = domain[domainId]
  return (
    <View
      className={`domain-stripe ${className}`}
      style={{ backgroundColor: meta.color }}
    />
  )
}
