// -*- coding: utf-8 -*-
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import type { IMChannel, IMChannelType } from '@/lib/api/imChannels'

/**
 * IMChannelCard — IM 渠道卡 (5 平台)
 *
 * 移动端做法:
 *   - 平台图标 + 配置状态 + 用户/群数 + 待审批数
 *   - "设置" 在卡片末尾,触屏区域足够大
 */

interface Props {
  channel: IMChannel
  onPress: (channel: IMChannel) => void
}

const CHANNEL_LABEL: Record<IMChannelType, string> = {
  feishu: '飞书',
  wechat: '微信',
  dingtalk: '钉钉',
  telegram: 'Telegram',
  discord: 'Discord',
  slack: 'Slack',
}

const CHANNEL_ICON: Record<IMChannelType, keyof typeof Ionicons.glyphMap> = {
  feishu: 'chatbubbles',
  wechat: 'logo-wechat',
  dingtalk: 'megaphone-outline',
  telegram: 'paper-plane-outline',
  discord: 'game-controller-outline',
  slack: 'chatbubble-ellipses',
}

const CHANNEL_TONE: Record<IMChannelType, string> = {
  feishu: '#4080FF',
  wechat: '#1AAD19',
  dingtalk: '#1296DB',
  telegram: '#0088CC',
  discord: '#5865F2',
  slack: '#611F69',
}

export function IMChannelCard({ channel, onPress }: Props) {
  const tone = CHANNEL_TONE[channel.channel_type]
  const connected = channel.status === 'connected'

  return (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.8}
      onPress={() => onPress(channel)}
    >
      <View style={[styles.icon, { backgroundColor: tone + '15' }]}>
        <Ionicons
          name={CHANNEL_ICON[channel.channel_type]}
          size={22}
          color={tone}
        />
      </View>
      <View style={styles.body}>
        <View style={styles.titleRow}>
          <Text style={styles.title}>{CHANNEL_LABEL[channel.channel_type]}</Text>
          <View
            style={[
              styles.pill,
              {
                backgroundColor: connected
                  ? Colors.success + '20'
                  : Colors.textMuted + '20',
              },
            ]}
          >
            <Text
              style={[
                styles.pillText,
                { color: connected ? Colors.success : Colors.textMuted },
              ]}
            >
              {connected ? '已连接' : '未配置'}
            </Text>
          </View>
        </View>
        <Text style={styles.subtitle} numberOfLines={1}>
          {channel.name}
        </Text>
        {connected && (
          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <Ionicons name="person-outline" size={12} color={Colors.textSecondary} />
              <Text style={styles.statText}>{channel.stats.bound_users} 用户</Text>
            </View>
            <View style={styles.stat}>
              <Ionicons name="people-outline" size={12} color={Colors.textSecondary} />
              <Text style={styles.statText}>{channel.stats.bound_groups} 群</Text>
            </View>
            {channel.stats.pending_pairings > 0 && (
              <View style={styles.stat}>
                <Ionicons name="alert-circle" size={12} color={Colors.warning} />
                <Text style={[styles.statText, { color: Colors.warning }]}>
                  {channel.stats.pending_pairings} 待审批
                </Text>
              </View>
            )}
          </View>
        )}
      </View>
      <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.md,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    backgroundColor: Colors.background,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  icon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  title: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  subtitle: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  statsRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 6 },
  stat: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  statText: { fontSize: 11, color: Colors.textSecondary },
  pill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  pillText: { fontSize: 10, fontWeight: '600' },
})
