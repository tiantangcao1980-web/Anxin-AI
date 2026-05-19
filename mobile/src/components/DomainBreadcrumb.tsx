// -*- coding: utf-8 -*-
/**
 * DomainBreadcrumb — 业务域面包屑 (Mobile RN · V3 · Editorial Luxury · Reset)
 *
 * 2026-05 Reset 说明：
 *   旧版有域色 dot + 域色文字 + iconbox surface 底，全部删除。
 *   新版纯文字 micro UPPERCASE tracking。
 *
 * 用法：
 *   <DomainBreadcrumb domain="legal" />
 *   <DomainBreadcrumb domain="legal" moduleName="合同审查" />
 */

import React from 'react'
import { StyleSheet, Text, View, type ViewStyle } from 'react-native'

import { domainMeta, lightTheme, type DomainId } from '@/theme/colors'

interface DomainBreadcrumbProps {
  domain: DomainId
  moduleName?: string
  /** 兼容旧 API；Reset 后 compact 等同默认 */
  compact?: boolean
  style?: ViewStyle
}

export function DomainBreadcrumb({
  domain,
  moduleName,
  style,
}: DomainBreadcrumbProps) {
  const meta = domainMeta[domain]
  return (
    <View
      style={[styles.crumb, style]}
      accessibilityRole="header"
      accessibilityLabel={`${meta.labelZh} ${moduleName ?? ''}`}
    >
      <Text style={styles.en}>{meta.labelEn}</Text>
      <Text style={styles.sep}> · </Text>
      <Text style={styles.zh}>{meta.labelZh}</Text>
      {moduleName ? (
        <>
          <Text style={styles.sep}> · </Text>
          <Text style={styles.module} numberOfLines={1}>{moduleName}</Text>
        </>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  crumb: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
  },
  en: {
    fontSize: 11,
    fontWeight: '500',
    letterSpacing: 1.6,
    textTransform: 'uppercase',
    color: lightTheme.textSecondary,
  },
  sep: {
    fontSize: 11,
    color: lightTheme.textMuted,
  },
  zh: {
    fontSize: 13,
    color: lightTheme.text,
  },
  module: {
    fontSize: 13,
    color: lightTheme.textSecondary,
    maxWidth: 180,
  },
})
