/**
 * Persona 详情页内嵌 Stack 布局（移动端 P17-C）
 *
 * 三屏：
 *   - index — 工作台首页（chat + capabilities 摘要）
 *   - chat — 全屏 chat
 *   - capabilities — 能力列表
 *
 * 在 personas/[personaId]/ 之下,这里是 Stack。
 * 子屏切换通过 PersonaHeader 内的自定义 tab + router.push 实现。
 */

import React from 'react'
import { Stack } from 'expo-router'
import { useColorScheme } from 'react-native'
import { Colors, DarkColors } from '../../../src/constants/colors'

export default function PersonaDetailLayout() {
  const scheme = useColorScheme()
  const theme = scheme === 'dark' ? DarkColors : Colors
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: theme.background },
        headerTintColor: theme.text,
        headerTitleStyle: { fontWeight: '600' },
        contentStyle: { backgroundColor: theme.background },
        headerShadowVisible: false,
        // 允许左滑返回 — 默认就是 true,显式声明保险
        gestureEnabled: true,
      }}
    >
      <Stack.Screen name="index" options={{ title: '智能体' }} />
      <Stack.Screen name="chat" options={{ title: '对话' }} />
      <Stack.Screen name="capabilities" options={{ title: '能力清单' }} />
    </Stack>
  )
}
