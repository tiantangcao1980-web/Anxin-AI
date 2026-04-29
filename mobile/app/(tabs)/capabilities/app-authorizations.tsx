// -*- coding: utf-8 -*-
import { useEffect, useState, useCallback, useMemo } from 'react'
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
import { AppAuthCard } from '@/components/v3/capabilities-mobile/AppAuthCard'
import {
  appAuthApi,
  type AppProvider,
  type AppAuthorization,
} from '@/lib/api/__mocks__/capabilities.mock'
import { openAuthSession } from '@/components/v3/capabilities-mobile/oauth-flow'

/**
 * 应用授权页 — OAuth 应用列表 + Connect/Disconnect 流程 (P17-D)
 *
 * 移动端关键差异:
 *   - Web 用 Dialog;移动端用 expo-web-browser openAuthSession 跳到原生浏览器
 *   - Mock 模式 1.5s 后回到列表 (模拟 OAuth 跳转回调)
 *   - 已连接 / 未连接 分两段排序
 *   - pull-to-refresh
 */

export default function AppAuthorizationsScreen() {
  const [providers, setProviders] = useState<AppProvider[]>([])
  const [auths, setAuths] = useState<AppAuthorization[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [connecting, setConnecting] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [p, a] = await Promise.all([
        appAuthApi.listProviders(),
        appAuthApi.listAuthorizations(),
      ])
      setProviders(p)
      setAuths(a)
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

  const handleConnect = async (provider: AppProvider) => {
    setConnecting(provider.provider_id)
    try {
      const startResp = await appAuthApi.startConnect(provider.provider_id)
      // 跳转 OAuth 页 (mock 立即返回)
      await openAuthSession(startResp.authorize_url)
      // mock 1.5s 后回到列表
      const fresh = await appAuthApi.completeConnect(provider.provider_id)
      setAuths((prev) => {
        const exist = prev.find((a) => a.id === fresh.id)
        return exist ? prev.map((a) => (a.id === fresh.id ? fresh : a)) : [...prev, fresh]
      })
    } catch (e) {
      Alert.alert('授权失败', e instanceof Error ? e.message : '未知错误')
    } finally {
      setConnecting(null)
    }
  }

  const handleDisconnect = (provider: AppProvider, auth: AppAuthorization) => {
    Alert.alert(
      '断开授权',
      `确定要断开「${provider.display_name}」的授权吗?`,
      [
        { text: '取消', style: 'cancel' },
        {
          text: '断开',
          style: 'destructive',
          onPress: async () => {
            setAuths((prev) => prev.filter((a) => a.id !== auth.id))
            try {
              await appAuthApi.disconnect(auth.id)
            } catch {
              // 回滚
              setAuths((prev) => [...prev, auth])
            }
          },
        },
      ],
    )
  }

  const sorted = useMemo(() => {
    const connectedIds = new Set(
      auths.filter((a) => a.status === 'connected').map((a) => a.provider_id),
    )
    return [...providers].sort((a, b) => {
      const ac = connectedIds.has(a.provider_id) ? 0 : 1
      const bc = connectedIds.has(b.provider_id) ? 0 : 1
      if (ac !== bc) return ac - bc
      return a.display_name.localeCompare(b.display_name, 'zh-Hans-CN')
    })
  }, [providers, auths])

  const connectedCount = auths.filter((a) => a.status === 'connected').length

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <View style={styles.header}>
        <Text style={styles.summary}>
          {providers.length} 个应用 · 已授权{' '}
          <Text style={{ color: Colors.success, fontWeight: '700' }}>{connectedCount}</Text> 个
        </Text>
        {connecting && (
          <View style={styles.connectingHint}>
            <ActivityIndicator size="small" color={Colors.primary} />
            <Text style={styles.connectingText}>授权中,等待回调...</Text>
          </View>
        )}
      </View>
      {loading && providers.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          data={sorted}
          keyExtractor={(p) => p.provider_id}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
          }
          renderItem={({ item }) => (
            <AppAuthCard
              provider={item}
              authorization={auths.find((a) => a.provider_id === item.provider_id)}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
            />
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="key-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyText}>暂无可授权应用</Text>
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
  header: {
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    backgroundColor: Colors.background,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  summary: { fontSize: Layout.fontSize.sm, color: Colors.textSecondary },
  connectingHint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 6,
  },
  connectingText: { color: Colors.primary, fontSize: Layout.fontSize.xs },
  empty: { alignItems: 'center', paddingVertical: 60, gap: 12 },
  emptyText: { color: Colors.textSecondary },
})
