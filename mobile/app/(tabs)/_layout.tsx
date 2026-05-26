// -*- coding: utf-8 -*-
import React from 'react'
import { Platform } from 'react-native'
import { Tabs } from 'expo-router'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import {
  LayoutGrid,
  ListChecks,
  MessageSquare,
  User,
} from 'lucide-react-native'
import { useV3Theme } from '@/theme'

/**
 * 移动端底部 4 Tab 导航（飞书 / 企微对标 — 2026-05-22）。
 *
 * 对齐 DESIGN §10.3 / 产品蓝图 §3.2：
 *   1. 消息    -> messages.tsx     人 / agent / 群 / 系统通知（含远控授权 inline）
 *   2. 任务    -> tasks.tsx        Agent 任务中心 + 状态筛选
 *   3. 工作台  -> workbench.tsx    10 personas 按业务域分组（原 personas.tsx 重命名）
 *   4. 我      -> me.tsx           账号 / 订阅 / 桌面配对 / 设置
 *
 * 原 V2 tab（chat / collaboration / investigation / knowledge / profile / index）
 * 仍保留在文件系统中（href: null 隐藏），通过 router.push 直链访问。
 * capabilities tab 已并入"我"高级段（待 me.tsx 接入）。
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
      {/* ===== 飞书风 4 tab ===== */}
      <Tabs.Screen
        name="messages"
        options={{
          title: '消息',
          tabBarIcon: ({ color, size }) => <MessageSquare color={color} size={size} />,
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
        name="workbench"
        options={{
          title: '工作台',
          tabBarIcon: ({ color, size }) => <LayoutGrid color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="me"
        options={{
          title: '我',
          tabBarIcon: ({ color, size }) => <User color={color} size={size} />,
        }}
      />

      {/* ===== V2 老页面 / 已合并 tab：保留文件但从底部 tab 隐藏 ===== */}
      <Tabs.Screen name="index" options={{ href: null }} />
      <Tabs.Screen name="chat" options={{ href: null }} />
      <Tabs.Screen name="collaboration" options={{ href: null }} />
      <Tabs.Screen name="investigation" options={{ href: null }} />
      <Tabs.Screen name="knowledge" options={{ href: null }} />
      <Tabs.Screen name="profile" options={{ href: null }} />
      <Tabs.Screen name="capabilities" options={{ href: null }} />
    </Tabs>
  )
}
