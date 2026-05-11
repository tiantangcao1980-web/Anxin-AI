// -*- coding: utf-8 -*-
/**
 * V3 主题入口。
 *
 * 用法：
 *   import { useV3Theme } from '@/theme'
 *   const t = useV3Theme()
 *   <Text style={{ color: t.colors.text }} />
 *
 * 与现有 `@/lib/theme`（V2 调色板）共存：V3 业务页统一从这里导入。
 */

import React, { createContext, useContext, useMemo } from 'react'
import { useColorScheme } from 'react-native'
import { lightTheme, darkTheme, type ThemeColors } from './colors'
import { spacing, radius, shadow } from './spacing'
import { text, fontSize, fontWeight, fontFamily, lineHeight } from './typography'

export * from './colors'
export * from './spacing'
export * from './typography'

export interface V3Theme {
  colors: ThemeColors
  spacing: typeof spacing
  radius: typeof radius
  shadow: typeof shadow
  text: typeof text
  fontSize: typeof fontSize
  fontWeight: typeof fontWeight
  fontFamily: typeof fontFamily
  lineHeight: typeof lineHeight
  isDark: boolean
}

const ThemeContext = createContext<V3Theme | null>(null)

export function V3ThemeProvider({ children }: { children: React.ReactNode }) {
  const scheme = useColorScheme()
  const isDark = scheme === 'dark'
  const value = useMemo<V3Theme>(
    () => ({
      colors: isDark ? darkTheme : lightTheme,
      spacing,
      radius,
      shadow,
      text,
      fontSize,
      fontWeight,
      fontFamily,
      lineHeight,
      isDark,
    }),
    [isDark],
  )
  return React.createElement(ThemeContext.Provider, { value }, children)
}

export function useV3Theme(): V3Theme {
  const ctx = useContext(ThemeContext)
  if (ctx) return ctx
  // fallback：未包裹 Provider 时也能用（直接 light）
  return {
    colors: lightTheme,
    spacing,
    radius,
    shadow,
    text,
    fontSize,
    fontWeight,
    fontFamily,
    lineHeight,
    isDark: false,
  }
}
