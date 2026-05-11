// -*- coding: utf-8 -*-
import { useEffect, useState, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { IMChannelCard } from '@/components/v3/capabilities-mobile/IMChannelCard'
import {
  imChannelsApi,
  type IMChannel,
} from '@/lib/api/__mocks__/capabilities.mock'

/**
 * 消息渠道列表页 — 5 IM 平台 (P17-D)
 *
 * 移动端做法:
 *   - 卡片样式 + 点击进入设置 (Mock: Alert 提示进入设置)
 *   - 已连接 / 未配置 用左右徽标区分
 */

export default function MessageChannelsScreen() {
  const [channels, setChannels] = useState<IMChannel[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await imChannelsApi.list()
      setChannels(data)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onRefresh = () => {
    setRefreshing(true)
    load()
  }

  const handlePress = (c: IMChannel) => {
    if (c.status === 'connected') {
      Alert.alert(
        c.name,
        `用户 ${c.stats.bound_users} · 群 ${c.stats.bound_groups} · 待审批 ${c.stats.pending_pairings}`,
        [{ text: '关闭' }],
      )
    } else {
      Alert.alert(
        '配置渠道',
        `${c.channel_type} 渠道暂未配置,请在 Web 后台填写 webhook / token`,
        [{ text: '知道了' }],
      )
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      {loading && channels.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          data={channels}
          keyExtractor={(c) => c.id}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
          }
          renderItem={({ item }) => (
            <IMChannelCard channel={item} onPress={handlePress} />
          )}
          ListHeaderComponent={
            <Text style={styles.hint}>
              智能体可在以下 IM 平台接收消息并回复用户
            </Text>
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="chatbubbles-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyText}>暂无 IM 渠道</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  hint: {
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    fontSize: Layout.fontSize.xs,
    color: Colors.textSecondary,
  },
  empty: { alignItems: 'center', paddingVertical: 60, gap: 12 },
  emptyText: { color: Colors.textSecondary },
})
