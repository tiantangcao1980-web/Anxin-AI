// -*- coding: utf-8 -*-
import { useEffect, useState, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  Switch,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import {
  pluginsApi,
  type Plugin,
  type PluginSource,
} from '@/lib/api/__mocks__/capabilities.mock'

/**
 * 插件列表页 — 官方 / MCP / 私有 三类 (P17-D)
 *
 * 移动端做法:
 *   - 单列卡片 + 来源 chip
 *   - pending_review 状态用「审批中」黄色徽标
 *   - Switch 即时启停
 */

const SOURCE_LABEL: Record<PluginSource, string> = {
  official: '官方',
  mcp: 'MCP',
  private: '私有',
}

const SOURCE_TONE: Record<PluginSource, string> = {
  official: Colors.primary,
  mcp: Colors.info,
  private: '#7C3AED',
}

export default function PluginsScreen() {
  const [plugins, setPlugins] = useState<Plugin[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await pluginsApi.list()
      setPlugins(data)
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

  const handleToggle = async (p: Plugin, next: boolean) => {
    if (p.status === 'pending_review') return
    setPlugins((prev) =>
      prev.map((x) =>
        x.id === p.id ? { ...x, status: next ? 'enabled' : 'disabled' } : x,
      ),
    )
    try {
      await pluginsApi.toggle(p.id, next)
    } catch {
      setPlugins((prev) =>
        prev.map((x) => (x.id === p.id ? { ...x, status: p.status } : x)),
      )
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      {loading && plugins.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          data={plugins}
          keyExtractor={(p) => p.id}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
          }
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={styles.iconWrap}>
                <Ionicons name="extension-puzzle-outline" size={22} color={Colors.primary} />
              </View>
              <View style={styles.body}>
                <View style={styles.titleRow}>
                  <Text style={styles.title}>{item.display_name}</Text>
                  <View
                    style={[styles.pill, { backgroundColor: SOURCE_TONE[item.source] + '20' }]}
                  >
                    <Text style={[styles.pillText, { color: SOURCE_TONE[item.source] }]}>
                      {SOURCE_LABEL[item.source]}
                    </Text>
                  </View>
                  {item.status === 'pending_review' && (
                    <View style={[styles.pill, { backgroundColor: Colors.warning + '20' }]}>
                      <Text style={[styles.pillText, { color: Colors.warning }]}>审批中</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.desc} numberOfLines={2}>
                  {item.description}
                </Text>
                <Text style={styles.publisher}>by {item.publisher}</Text>
              </View>
              <Switch
                value={item.status === 'enabled'}
                onValueChange={(v) => handleToggle(item, v)}
                disabled={item.status === 'pending_review'}
                trackColor={{ false: Colors.border, true: Colors.primary + '60' }}
                thumbColor={item.status === 'enabled' ? Colors.primary : Colors.surface}
              />
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="extension-puzzle-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyText}>暂无可用插件</Text>
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
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  title: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  desc: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 4 },
  publisher: { fontSize: 11, color: Colors.textMuted, marginTop: 2 },
  pill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  pillText: { fontSize: 10, fontWeight: '600' },
  empty: { alignItems: 'center', paddingVertical: 60, gap: 12 },
  emptyText: { color: Colors.textSecondary },
})
