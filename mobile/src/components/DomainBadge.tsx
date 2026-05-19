// -*- coding: utf-8 -*-
/**
 * DomainBadge.tsx — 业务域可视化原子组件 (Mobile RN · V3 · Editorial Luxury · Reset)
 *
 * 2026-05 Reset 说明：
 *   旧版使用 8 个高饱和域色 + surface 底色 + Ionicons 染色，
 *   违反 ui-design skill 与 DESIGN.md §1 设计哲学，已重写为：
 *     - 仅 micro UPPERCASE tracking 文字
 *     - 1.5px stroke Ionicons（不染色 — 走 text 颜色继承）
 *     - 单色调（color = textSecondary）
 *
 * 用法：
 *   <DomainBadge domain="legal" />
 *   <DomainStripe domain="legal" /> — Reset 后 no-op，兼容旧调用方
 */

import React from 'react'
import { StyleSheet, Text, View, type ViewStyle } from 'react-native'

import { domainMeta, lightTheme, type DomainId } from '@/theme/colors'

export interface DomainBadgeProps {
  domain: DomainId
  /** 是否前置 labelEn（如 "LEGAL · 法务"） */
  showEnglish?: boolean
  style?: ViewStyle
}

export function DomainBadge({
  domain,
  showEnglish = false,
  style,
}: DomainBadgeProps) {
  const meta = domainMeta[domain]
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`业务域：${meta.labelZh}`}
      style={[styles.badge, style]}
    >
      {showEnglish ? (
        <>
          <Text style={styles.labelEn}>{meta.labelEn}</Text>
          <Text style={styles.sep}> · </Text>
        </>
      ) : null}
      <Text style={styles.labelZh}>{meta.labelZh}</Text>
    </View>
  )
}

/**
 * DomainStripe — Reset 后 no-op shim
 * 旧版渲染 4pt 高彩条，已废除（业务子页头部用 DomainBadge 即可）
 */
export function DomainStripe(_props: { domain: DomainId; style?: ViewStyle }) {
  return null
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
  },
  labelEn: {
    fontSize: 11,
    fontWeight: '500',
    letterSpacing: 1.6, // ~0.16em on 11px
    textTransform: 'uppercase',
    color: lightTheme.textSecondary,
  },
  sep: {
    fontSize: 11,
    color: lightTheme.textMuted,
  },
  labelZh: {
    fontSize: 13,
    fontWeight: '400',
    color: lightTheme.text,
  },
})
