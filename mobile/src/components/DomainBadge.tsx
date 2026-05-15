// -*- coding: utf-8 -*-
/**
 * DomainBadge.tsx — 业务域可视化原子组件 (Mobile RN)
 *
 * 与 frontend Web 的 `components/ui/domain.tsx` 视觉对齐 — 同一套 8 大业务域、
 * 同一套色板（来自 `@/theme/colors.ts` 的 `domain.*`）。
 *
 * 用法：
 *   import { DomainBadge, DomainStripe } from '@/components/DomainBadge'
 *   <DomainBadge domain="legal" />
 *   <DomainStripe domain="finance" />
 *
 * 设计约束：
 * - 仅做"分类标识"，主行动按钮 / Tab active 仍走 palette.primary
 * - 与 risk-* 状态色互不重叠（风险是状态，域是分类）
 */

import React from 'react'
import { Ionicons } from '@expo/vector-icons'
import { StyleSheet, Text, View, type ViewStyle } from 'react-native'

import { domain, type DomainId } from '@/theme/colors'

// 域 → Ionicons 图标（mobile 端用 Ionicons 而非 lucide）
const DOMAIN_ICONS: Record<DomainId, keyof typeof Ionicons.glyphMap> = {
  legal:      'scale-outline',
  finance:    'calculator-outline',
  tax:        'business-outline',
  compliance: 'shield-checkmark-outline',
  operations: 'analytics-outline',
  growth:     'compass-outline',
  content:    'create-outline',
  global:     'globe-outline',
}

export interface DomainBadgeProps {
  domain: DomainId
  /** 是否显示图标（默认 true） */
  showIcon?: boolean
  /** 是否显示文本（默认 true）— 仅图标时通过 a11yLabel 提示语义 */
  showLabel?: boolean
  /** 尺寸 */
  size?: 'sm' | 'md'
  /** 容器额外样式 */
  style?: ViewStyle
}

export function DomainBadge({
  domain: domainId,
  showIcon = true,
  showLabel = true,
  size = 'sm',
  style,
}: DomainBadgeProps) {
  const meta = domain[domainId]
  const iconSize = size === 'sm' ? 12 : 14
  const padV = size === 'sm' ? 4 : 6
  const padH = size === 'sm' ? 10 : 12
  const fontSize = size === 'sm' ? 11 : 12
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={meta.labelZh}
      style={[
        styles.badge,
        {
          backgroundColor: meta.surface,
          paddingVertical: padV,
          paddingHorizontal: padH,
        },
        style,
      ]}
    >
      {showIcon ? (
        <Ionicons
          name={DOMAIN_ICONS[domainId]}
          size={iconSize}
          color={meta.color}
          style={showLabel ? styles.iconWithLabel : undefined}
        />
      ) : null}
      {showLabel ? (
        <Text style={[styles.label, { color: meta.color, fontSize }]} numberOfLines={1}>
          {meta.labelZh}
        </Text>
      ) : null}
    </View>
  )
}

/** 4pt 高的业务域顶部彩条，用于域内页面顶部识别 */
export function DomainStripe({
  domain: domainId,
  style,
}: {
  domain: DomainId
  style?: ViewStyle
}) {
  const meta = domain[domainId]
  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no"
      style={[styles.stripe, { backgroundColor: meta.color }, style]}
    />
  )
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 9999,
    alignSelf: 'flex-start',
  },
  iconWithLabel: {
    marginRight: 4,
  },
  label: {
    fontWeight: '500',
    lineHeight: 16,
  },
  stripe: {
    height: 4,
    width: '100%',
  },
})
