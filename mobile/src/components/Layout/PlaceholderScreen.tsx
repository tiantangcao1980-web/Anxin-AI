// -*- coding: utf-8 -*-
/**
 * V3 占位页（待 P17-B/C/D 替换为真实页面）。
 *
 * 用法：
 *   <PlaceholderScreen
 *     title="智能体加载中..."
 *     hint="P17-B 完成后将显示 10 个 persona 列表"
 *   />
 */

import React from 'react'
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native'
import { Screen } from './Screen'
import { useV3Theme } from '@/theme'

export interface PlaceholderScreenProps {
  title: string
  hint?: string
  showSpinner?: boolean
}

export function PlaceholderScreen({
  title,
  hint,
  showSpinner = true,
}: PlaceholderScreenProps) {
  const t = useV3Theme()
  return (
    <Screen padded>
      <View style={styles.center}>
        {showSpinner && (
          <ActivityIndicator
            size="large"
            color={t.colors.primary}
            style={{ marginBottom: t.spacing.lg }}
          />
        )}
        <Text style={[styles.title, { color: t.colors.text }]}>{title}</Text>
        {hint ? (
          <Text style={[styles.hint, { color: t.colors.textSecondary }]}>
            {hint}
          </Text>
        ) : null}
      </View>
    </Screen>
  )
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  title: {
    fontSize: 18,
    fontWeight: '500',
    textAlign: 'center',
  },
  hint: {
    marginTop: 8,
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 20,
  },
})
