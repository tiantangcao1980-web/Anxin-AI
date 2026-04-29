// -*- coding: utf-8 -*-
import React, { useEffect } from 'react'
import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useColorScheme } from 'react-native'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { Colors, DarkColors } from '../src/constants/colors'
import { PrivacyProvider } from '../src/lib/privacy-context'
import { V3ThemeProvider } from '../src/theme'
import { setupV3PushNotifications } from '../src/lib/notifications'

/**
 * Root layout（V3 P17-A 升级）。
 *
 * 包裹层级：
 *   SafeAreaProvider
 *     -> PrivacyProvider（V2 隐私模式上下文，仍兼容老页面）
 *       -> V3ThemeProvider（V3 主题：颜色 / 字体 / 间距）
 *         -> Stack
 *
 * 启动副作用：
 *   1. 申请推送权限并注册 ExpoPushToken
 *   2. 绑定前台 / 后台通知 handler，任务通知自动 deep-link 到 /(tabs)/tasks/[id]
 */
export default function RootLayout() {
  const colorScheme = useColorScheme()
  const theme = colorScheme === 'dark' ? DarkColors : Colors

  useEffect(() => {
    let unsub: (() => void) | undefined
    setupV3PushNotifications().then((result) => {
      unsub = result.unsubscribe
    })
    return () => {
      if (unsub) unsub()
    }
  }, [])

  return (
    <SafeAreaProvider>
      <PrivacyProvider>
        <V3ThemeProvider>
          <StatusBar style={colorScheme === 'dark' ? 'light' : 'dark'} />
          <Stack
            screenOptions={{
              headerStyle: { backgroundColor: theme.background },
              headerTintColor: theme.text,
              headerTitleStyle: { fontWeight: '600' },
              contentStyle: { backgroundColor: theme.background },
              headerShadowVisible: false,
            }}
          >
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="(auth)" options={{ headerShown: false }} />
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          </Stack>
        </V3ThemeProvider>
      </PrivacyProvider>
    </SafeAreaProvider>
  )
}
