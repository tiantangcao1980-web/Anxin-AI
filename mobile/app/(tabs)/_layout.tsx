// -*- coding: utf-8 -*-
import React from 'react'
import { Platform } from 'react-native'
import { Tabs } from 'expo-router'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import {
  Bot,
  ListChecks,
  Sparkles,
  User,
} from 'lucide-react-native'
import { useV3Theme } from '@/theme'

/**
 * V3 移动端底部 4 Tab 导航。
 *
 * 对齐 V3 PRD：
 *   1. 智能体  -> personas.tsx        10 个 persona 入口（待 P17-B）
 *   2. 任务    -> tasks.tsx           agent 任务中心（待 P17-C）
 *   3. 能力    -> capabilities.tsx    5 个能力中心（待 P17-D）
 *   4. 我      -> me.tsx              账号 / 订阅 / 推送 / 登出
 *
 * V2 老 tab（chat / collaboration / investigation / knowledge / profile / index）
 * 暂保留在文件系统中，通过 `href: null` 从底部栏隐藏，避免 P17-B/C/D 还没接入时
 * 误触老页面。可通过 router.push 直链访问。
 */
export default function TabLayout() {
  const t = useV3Theme()
  const insets = useSafeAreaInsets()

  const baseTabBarHeight = 56
  const paddingBottom = Math.max(insets.bottom, Platform.OS === 'ios' ? 8 : 8)

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: t.colors.primary,
        tabBarInactiveTintColor: t.colors.textMuted,
        tabBarStyle: {
          backgroundColor: t.colors.surface,
          borderTopColor: t.colors.divider,
          borderTopWidth: 0.5,
          height: baseTabBarHeight + paddingBottom,
          paddingBottom,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
          marginTop: 2,
        },
        headerStyle: { backgroundColor: t.colors.background },
        headerTintColor: t.colors.text,
        headerTitleStyle: { fontWeight: '600' },
        headerShadowVisible: false,
      }}
    >
      {/* ===== V3 4 个 tab ===== */}
      <Tabs.Screen
        name="personas"
        options={{
          title: '智能体',
          tabBarIcon: ({ color, size }) => <Bot color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="tasks"
        options={{
          title: '任务',
          tabBarIcon: ({ color, size }) => <ListChecks color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="capabilities"
        options={{
          title: '能力',
          tabBarIcon: ({ color, size }) => <Sparkles color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="me"
        options={{
          title: '我',
          tabBarIcon: ({ color, size }) => <User color={color} size={size} />,
        }}
      />

      {/* ===== V2 老页面：保留文件但从底部 tab 隐藏，避免破坏 router 路径 ===== */}
      <Tabs.Screen name="index" options={{ href: null }} />
      <Tabs.Screen name="chat" options={{ href: null }} />
      <Tabs.Screen name="collaboration" options={{ href: null }} />
      <Tabs.Screen name="investigation" options={{ href: null }} />
      <Tabs.Screen name="knowledge" options={{ href: null }} />
      <Tabs.Screen name="profile" options={{ href: null }} />
    </Tabs>
  )
}
