import { useColorScheme } from 'react-native'
import { Colors, DarkColors } from '../constants/colors'

/**
 * 统一的主题 hook —— 自动响应系统 light/dark，避免各页面硬编码 `#FFF`。
 *
 * 用法：
 *   const t = useTheme()
 *   <Stack.Screen options={{
 *     headerStyle: { backgroundColor: t.background },
 *     headerTintColor: t.text,
 *   }} />
 */
export function useTheme() {
  const scheme = useColorScheme()
  const isDark = scheme === 'dark'
  const palette = isDark ? DarkColors : Colors
  return {
    ...palette,
    isDark,
    scheme,
  }
}

/**
 * 给业务页面用的 Stack.Screen 默认选项工厂。
 * 保持 header / 内容背景随系统变化，避免白底黑字在夜间刺眼。
 */
export function useStackHeaderOptions(overrides: Record<string, unknown> = {}) {
  const t = useTheme()
  return {
    headerStyle: { backgroundColor: t.background },
    headerTintColor: t.text,
    headerTitleStyle: { fontWeight: '600' as const, color: t.text },
    contentStyle: { backgroundColor: t.background },
    headerShadowVisible: false,
    ...overrides,
  }
}
