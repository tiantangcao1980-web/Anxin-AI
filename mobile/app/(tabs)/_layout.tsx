import React, { useEffect, useState } from 'react'
import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useColorScheme, Platform } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Colors, DarkColors } from '../../src/constants/colors'
import { Layout } from '../../src/constants/layout'
import { normalizeBadgeCount } from '../../src/features/inbox/engagement-model'
import { api } from '../../src/services/api'
import type { IMConversation } from '../../src/types/api'

/**
 * 移动端底部 5 Tab 导航。
 *
 * 对齐 PRD 四大业务域：AI法务 / 智能协作 / 智能调查 / 法律智库，
 * 第 5 项「我的」承载账号、订阅、运行模式、设置。
 *
 * 徽章：合并了通知未读数 + IM 会话未读数进入「协作」tab。
 */
export default function TabLayout() {
  const colorScheme = useColorScheme()
  const theme = colorScheme === 'dark' ? DarkColors : Colors
  const insets = useSafeAreaInsets()
  const [collabBadge, setCollabBadge] = useState<number | string | undefined>(undefined)

  useEffect(() => {
    const loadBadges = async () => {
      try {
        const [notificationResult, conversationResult] = await Promise.allSettled([
          api.get<{ count: number }>('/notifications/unread-count'),
          api.get<IMConversation[]>('/im/conversations'),
        ])

        const notificationCount = notificationResult.status === 'fulfilled'
          ? notificationResult.value.count
          : 0
        const conversationCount = conversationResult.status === 'fulfilled'
          ? conversationResult.value.reduce((sum, item) => sum + (item.unread_count ?? 0), 0)
          : 0

        setCollabBadge(normalizeBadgeCount(notificationCount + conversationCount))
      } catch {
        setCollabBadge(undefined)
      }
    }

    loadBadges()
  }, [])

  const baseTabBarHeight = Math.max(Layout.tabBarBaseHeight, Layout.touchTarget.min)
  const paddingBottom = Math.max(insets.bottom, Platform.OS === 'ios' ? 8 : 8)

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: theme.textMuted,
        tabBarStyle: {
          backgroundColor: theme.background,
          borderTopColor: theme.border,
          height: baseTabBarHeight + paddingBottom,
          minHeight: Layout.touchTarget.min + paddingBottom,
          paddingBottom,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
        },
        headerStyle: { backgroundColor: theme.background },
        headerTintColor: theme.text,
        headerTitleStyle: { fontWeight: '600' },
        headerShadowVisible: false,
      }}
    >
      <Tabs.Screen
        name="chat"
        options={{
          title: 'AI法务',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="sparkles-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="collaboration"
        options={{
          title: '协作',
          tabBarBadge: collabBadge,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="investigation"
        options={{
          title: '智能调查',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="search-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="knowledge"
        options={{
          title: '法律智库',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="library-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: '我的',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-outline" size={size} color={color} />
          ),
        }}
      />

      {/* 原 index 收件箱仍保留页面但从 tab 中隐藏，避免破坏已有路由；
          从「我的」进入「消息中心」后使用 */}
      <Tabs.Screen
        name="index"
        options={{
          href: null,
          title: '收件箱',
        }}
      />
    </Tabs>
  )
}
