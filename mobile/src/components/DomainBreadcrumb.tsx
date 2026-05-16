// -*- coding: utf-8 -*-
/**
 * DomainBreadcrumb (Mobile RN) — 业务域面包屑
 *
 * 与 frontend/src/components/ui/DomainBreadcrumb.tsx 视觉对齐。
 * Mobile 端不做 pathname 自动推断（expo-router 路径推断需要 hook 链路），
 * 改为由调用方显式传入 domainId（业务页通常和 DomainStripe 配对使用）。
 *
 * 用法：
 *   <DomainBreadcrumb domain="legal" moduleName="找律师" />
 *   <DomainBreadcrumb domain="legal" compact />
 */

import React from 'react'
import { Ionicons } from '@expo/vector-icons'
import { StyleSheet, Text, View, type ViewStyle } from 'react-native'

import { domain, type DomainId } from '@/theme/colors'

// 与 DomainBadge 共享同一套 Ionicons 映射
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

export interface DomainBreadcrumbProps {
  domain: DomainId
  /** 可选：当前模块/子页名称，显示在域名之后 */
  moduleName?: string
  /** 紧凑变体：仅显示 6pt 圆点 + 域名 */
  compact?: boolean
  /** 容器额外样式 */
  style?: ViewStyle
}

export function DomainBreadcrumb({
  domain: domainId,
  moduleName,
  compact = false,
  style,
}: DomainBreadcrumbProps) {
  const meta = domain[domainId]

  if (compact) {
    return (
      <View
        accessibilityRole="text"
        accessibilityLabel={`当前业务域：${meta.labelZh}`}
        style={[styles.compactContainer, style]}
      >
        <View
          style={[styles.dot, { backgroundColor: meta.color }]}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={[styles.compactLabel, { color: meta.color }]} numberOfLines={1}>
          {meta.labelZh}
        </Text>
      </View>
    )
  }

  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={
        moduleName
          ? `当前业务域 ${meta.labelZh}，模块 ${moduleName}`
          : `当前业务域：${meta.labelZh}`
      }
      style={[styles.container, style]}
    >
      <View style={[styles.iconBox, { backgroundColor: meta.surface }]}>
        <Ionicons name={DOMAIN_ICONS[domainId]} size={12} color={meta.color} />
      </View>
      <Text style={[styles.label, { color: meta.color }]} numberOfLines={1}>
        {meta.labelZh}
      </Text>
      {moduleName ? (
        <>
          <Text style={styles.sep} accessibilityElementsHidden importantForAccessibility="no">
            ·
          </Text>
          <Text style={styles.moduleName} numberOfLines={1}>
            {moduleName}
          </Text>
        </>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  compactContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  iconBox: {
    width: 20,
    height: 20,
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  label: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 16,
  },
  compactLabel: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 16,
  },
  sep: {
    color: 'rgba(120, 113, 108, 0.4)',
    fontSize: 12,
    lineHeight: 16,
  },
  moduleName: {
    fontSize: 12,
    color: 'rgba(120, 113, 108, 0.8)',
    lineHeight: 16,
    flexShrink: 1,
  },
})
