// -*- coding: utf-8 -*-
/**
 * V3 通用 Screen 容器：自动处理 SafeArea + 主题背景。
 *
 * 用法：
 *   <Screen>
 *     <Text>...</Text>
 *   </Screen>
 *
 * 可选：scrollable / padded / withHeader（隐藏 SafeArea top 给 header 用）
 */

import React from 'react'
import { ScrollView, StyleSheet, View, type ViewStyle } from 'react-native'
import { SafeAreaView, type Edge } from 'react-native-safe-area-context'
import { useV3Theme } from '@/theme'

export interface ScreenProps {
  children: React.ReactNode
  scrollable?: boolean
  padded?: boolean
  /** 哪些边缘应用 SafeArea inset，默认 ['top', 'bottom'] */
  edges?: Edge[]
  style?: ViewStyle
  contentStyle?: ViewStyle
  /** 自定义底色（不传走主题 background） */
  background?: string
}

export function Screen({
  children,
  scrollable = false,
  padded = false,
  edges = ['top', 'bottom'],
  style,
  contentStyle,
  background,
}: ScreenProps) {
  const t = useV3Theme()
  const bg = background ?? t.colors.background
  const padding = padded ? t.spacing.lg : 0

  const content = scrollable ? (
    <ScrollView
      style={[styles.scroll, { backgroundColor: bg }]}
      contentContainerStyle={[
        styles.scrollContent,
        { padding, backgroundColor: bg },
        contentStyle,
      ]}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.content, { padding, backgroundColor: bg }, contentStyle]}>
      {children}
    </View>
  )

  return (
    <SafeAreaView
      style={[styles.safe, { backgroundColor: bg }, style]}
      edges={edges}
    >
      {content}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  scroll: { flex: 1 },
  scrollContent: { flexGrow: 1 },
  content: { flex: 1 },
})
