// -*- coding: utf-8 -*-
import { useEffect, useState, useCallback } from 'react'
import { ScrollView, StyleSheet, View, Text, RefreshControl } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { CapabilityCategoryCard } from '@/components/v3/capabilities-mobile/CapabilityCategoryCard'
import {
  scheduledTasksApi,
  appAuthApi,
  skillsApi,
  pluginsApi,
  imChannelsApi,
  pairingApi,
} from '@/lib/api/__mocks__/capabilities.mock'

/**
 * 能力中心 — 6 子模块入口聚合页 (P17-D)
 *
 * 与 Web 的差异:
 *   - Web 是 sidebar + tab 布局,移动端简化为单列入口卡 + 右侧角标
 *   - 一次拉取各域计数,以数字角标暗示「需要关注」
 */

interface Counts {
  tasks: number
  tasksFailed: number
  apps: number
  appsConnected: number
  skills: number
  skillsEnabled: number
  channels: number
  channelsConnected: number
  pairings: number
  plugins: number
  pluginsEnabled: number
}

const ZERO: Counts = {
  tasks: 0, tasksFailed: 0,
  apps: 0, appsConnected: 0,
  skills: 0, skillsEnabled: 0,
  channels: 0, channelsConnected: 0,
  pairings: 0,
  plugins: 0, pluginsEnabled: 0,
}

export default function CapabilitiesIndex() {
  const [counts, setCounts] = useState<Counts>(ZERO)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    try {
      const [tasks, providers, auths, skills, channels, pairings, plugins] = await Promise.all([
        scheduledTasksApi.list(),
        appAuthApi.listProviders(),
        appAuthApi.listAuthorizations(),
        skillsApi.list(),
        imChannelsApi.list(),
        pairingApi.listPending(),
        pluginsApi.list(),
      ])
      setCounts({
        tasks: tasks.length,
        tasksFailed: tasks.filter((t) => t.status === 'failed').length,
        apps: providers.length,
        appsConnected: auths.filter((a) => a.status === 'connected').length,
        skills: skills.length,
        skillsEnabled: skills.filter((s) => s.enabled).length,
        channels: channels.length,
        channelsConnected: channels.filter((c) => c.status === 'connected').length,
        pairings: pairings.length,
        plugins: plugins.length,
        pluginsEnabled: plugins.filter((p) => p.status === 'enabled').length,
      })
    } catch {
      setCounts(ZERO)
    } finally {
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

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <Stack.Screen options={{ title: '能力中心' }} />
      <ScrollView
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.heading}>能力中心</Text>
          <Text style={styles.sub}>
            集中管理智能体的「定时任务、应用授权、技能、插件、IM 渠道与配对审批」
          </Text>
        </View>

        <View style={styles.section}>
          <CapabilityCategoryCard
            icon="time-outline"
            title="定时任务"
            description={`${counts.tasks} 个 · 当前 ${counts.tasksFailed > 0 ? counts.tasksFailed + ' 个失败' : '运行健康'}`}
            badge={counts.tasksFailed > 0 ? counts.tasksFailed : undefined}
            badgeTone="warning"
            onPress={() => router.push('/(tabs)/capabilities/scheduled-tasks')}
          />
          <CapabilityCategoryCard
            icon="key-outline"
            title="应用授权"
            description={`已连接 ${counts.appsConnected} / ${counts.apps} 个第三方应用`}
            badge={counts.appsConnected}
            badgeTone="success"
            onPress={() => router.push('/(tabs)/capabilities/app-authorizations')}
          />
          <CapabilityCategoryCard
            icon="sparkles-outline"
            title="技能"
            description={`已启用 ${counts.skillsEnabled} / ${counts.skills} 个原子技能`}
            badge={counts.skillsEnabled}
            badgeTone="primary"
            onPress={() => router.push('/(tabs)/capabilities/skills')}
          />
          <CapabilityCategoryCard
            icon="extension-puzzle-outline"
            title="插件"
            description={`已启用 ${counts.pluginsEnabled} / ${counts.plugins} 个插件`}
            badge={counts.pluginsEnabled}
            badgeTone="primary"
            onPress={() => router.push('/(tabs)/capabilities/plugins')}
          />
          <CapabilityCategoryCard
            icon="chatbubbles-outline"
            title="消息渠道"
            description={`${counts.channelsConnected} / ${counts.channels} 个 IM 平台已接入`}
            badge={counts.channelsConnected}
            badgeTone="success"
            onPress={() => router.push('/(tabs)/capabilities/message-channels')}
          />
          <CapabilityCategoryCard
            icon="people-outline"
            title="配对审批"
            description={
              counts.pairings > 0
                ? `有 ${counts.pairings} 个用户等待绑定`
                : '没有待审批的配对请求'
            }
            badge={counts.pairings || undefined}
            badgeTone="warning"
            onPress={() => router.push('/(tabs)/capabilities/pairing-authorizations')}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: { paddingHorizontal: Layout.spacing.md, paddingTop: Layout.spacing.lg, paddingBottom: Layout.spacing.md },
  heading: { fontSize: Layout.fontSize.title, fontWeight: '700', color: Colors.text },
  sub: { marginTop: 4, fontSize: Layout.fontSize.sm, color: Colors.textSecondary },
  section: { marginTop: Layout.spacing.sm, backgroundColor: Colors.background },
})
