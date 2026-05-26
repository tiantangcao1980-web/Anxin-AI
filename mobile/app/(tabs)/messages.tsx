// -*- coding: utf-8 -*-
/**
 * 消息 tab — 飞书风第一个 tab。
 *
 * 内容：
 *   - 会话列表（人 / agent / 系统通知）
 *   - 远控授权请求 inline 卡片（不单独跳转，混在消息流里）
 *   - 任务卡更新通知
 *   - 顶部搜索 + 新建会话
 *
 * 后端：/im/conversations + /im-pairing/pending + WebSocket /ws/im
 * 关联：docs/openspec/03-cloud-services-contract.md §3
 *
 * 当前状态：占位，等 IM WebSocket 通道接入后填真实数据
 */

import React from 'react'
import { ScrollView, View, Text, TouchableOpacity, StyleSheet } from 'react-native'
import { useV3Theme } from '@/theme'

interface Conversation {
  id: string
  type: 'person' | 'agent' | 'group' | 'system'
  emoji: string
  title: string
  preview: string
  time: string
  unread?: number
}

// 占位数据，等 /im/conversations 接入后替换
const MOCK_CONVERSATIONS: Conversation[] = [
  {
    id: 'sys-onboarding',
    type: 'system',
    emoji: '🔔',
    title: '系统通知',
    preview: '欢迎使用安心智能助手。点击进入工作台开始使用。',
    time: '刚刚',
  },
  {
    id: 'agent-anxin',
    type: 'agent',
    emoji: '🎯',
    title: '安心助理',
    preview: '可以帮你做什么？尝试问我"今天有哪些待办"',
    time: '刚刚',
  },
]

export default function MessagesTabScreen() {
  const t = useV3Theme()

  return (
    <View style={{ flex: 1, backgroundColor: t.colors.backgroundMuted }}>
      <View style={[styles.header, { backgroundColor: t.colors.surface, borderBottomColor: t.colors.divider }]}>
        <Text style={[styles.headerTitle, { color: t.colors.text }]}>消息</Text>
      </View>

      <ScrollView contentContainerStyle={styles.list}>
        {MOCK_CONVERSATIONS.map((conv) => (
          <TouchableOpacity
            key={conv.id}
            style={[styles.item, { backgroundColor: t.colors.surface, borderBottomColor: t.colors.divider }]}
            activeOpacity={0.7}
          >
            <View style={[styles.avatar, { backgroundColor: t.colors.surfaceMuted }]}>
              <Text style={styles.avatarEmoji}>{conv.emoji}</Text>
            </View>
            <View style={styles.itemBody}>
              <View style={styles.itemRow}>
                <Text style={[styles.itemTitle, { color: t.colors.text }]} numberOfLines={1}>
                  {conv.title}
                </Text>
                <Text style={[styles.itemTime, { color: t.colors.textMuted }]}>{conv.time}</Text>
              </View>
              <Text style={[styles.itemPreview, { color: t.colors.textSecondary }]} numberOfLines={1}>
                {conv.preview}
              </Text>
            </View>
            {conv.unread ? (
              <View style={[styles.badge, { backgroundColor: t.colors.imPrimary }]}>
                <Text style={styles.badgeText}>{conv.unread}</Text>
              </View>
            ) : null}
          </TouchableOpacity>
        ))}

        <View style={styles.placeholder}>
          <Text style={[styles.placeholderText, { color: t.colors.textMuted }]}>
            消息推送 / 远控授权请求 / 任务卡更新将通过 IM 通道实时显示
          </Text>
          <Text style={[styles.placeholderHint, { color: t.colors.textMuted }]}>
            等 /im/ws WebSocket 接入完成
          </Text>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 12,
    borderBottomWidth: 0.5,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '600',
  },
  list: {
    paddingBottom: 32,
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 0.5,
    minHeight: 64,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  avatarEmoji: {
    fontSize: 20,
  },
  itemBody: {
    flex: 1,
    minWidth: 0,
  },
  itemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  itemTitle: {
    fontSize: 15,
    fontWeight: '500',
    flex: 1,
    marginRight: 8,
  },
  itemTime: {
    fontSize: 11,
  },
  itemPreview: {
    fontSize: 13,
    marginTop: 2,
  },
  badge: {
    marginLeft: 8,
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    paddingHorizontal: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '600',
  },
  placeholder: {
    padding: 24,
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
  placeholderHint: {
    fontSize: 10,
    marginTop: 4,
  },
})
