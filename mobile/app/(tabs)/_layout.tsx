import React, { useEffect, useState } from 'react'
import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useColorScheme, Platform } from 'react-native'
import { Colors, DarkColors } from '../../src/constants/colors'
import { normalizeBadgeCount } from '../../src/features/inbox/engagement-model'
import { api } from '../../src/services/api'
import type { IMConversation } from '../../src/types/api'

export default function TabLayout() {
  const colorScheme = useColorScheme()
  const theme = colorScheme === 'dark' ? DarkColors : Colors
  const [inboxBadge, setInboxBadge] = useState<number | string | undefined>(undefined)
  const [chatBadge, setChatBadge] = useState<number | string | undefined>(undefined)

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

        setInboxBadge(normalizeBadgeCount(notificationCount + conversationCount))
        setChatBadge(normalizeBadgeCount(conversationCount))
      } catch {
        setInboxBadge(undefined)
        setChatBadge(undefined)
      }
    }

    loadBadges()
  }, [])

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: theme.textMuted,
        tabBarStyle: {
          backgroundColor: theme.background,
          borderTopColor: theme.border,
          height: Platform.OS === 'ios' ? 83 : 56,
          paddingBottom: Platform.OS === 'ios' ? 28 : 8,
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
        name="index"
        options={{
          title: '收件箱',
          tabBarBadge: inboxBadge,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="file-tray-full-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: '咨询',
          tabBarBadge: chatBadge,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="chatbubbles-outline" size={size} color={color} />
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
    </Tabs>
  )
}
