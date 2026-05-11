import { useEffect, useState, useCallback } from 'react'
import { View, Text, Input, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  scheduledTasksApi, appAuthApi, skillsApi, pluginsApi, imChannelsApi, pairingApi,
} from '../_mock'
import './index.scss'

/**
 * 能力中心入口（P21-D 小程序）
 * 与 web (frontend/src/pages/v3/capabilities/) / mobile ((tabs)/capabilities/index.tsx)
 * 保持产品一致：6 个分组卡片 + 顶部搜索 + 数字角标。
 */

interface Counts {
  tasks: number; tasksFailed: number
  apps: number; appsConnected: number
  skills: number; skillsEnabled: number
  channels: number; channelsConnected: number
  pairings: number
  plugins: number; pluginsEnabled: number
}
const ZERO: Counts = {
  tasks: 0, tasksFailed: 0,
  apps: 0, appsConnected: 0,
  skills: 0, skillsEnabled: 0,
  channels: 0, channelsConnected: 0,
  pairings: 0,
  plugins: 0, pluginsEnabled: 0,
}

interface CardDef {
  key: string
  emoji: string
  title: string
  subtitle: (c: Counts) => string
  badge?: (c: Counts) => number
  badgeTone?: 'warning' | 'success' | 'primary'
  path: string
}

const CARDS: CardDef[] = [
  {
    key: 'scheduled',
    emoji: '⏰',
    title: '定时任务',
    subtitle: (c) => `${c.tasks} 个任务 · ${c.tasksFailed > 0 ? `${c.tasksFailed} 失败` : '运行健康'}`,
    badge: (c) => c.tasksFailed,
    badgeTone: 'warning',
    path: '/subpackages/capabilities/scheduled-tasks/index',
  },
  {
    key: 'apps',
    emoji: '🔑',
    title: '应用授权',
    subtitle: (c) => `已连接 ${c.appsConnected} / ${c.apps} 个第三方应用`,
    badge: (c) => c.appsConnected,
    badgeTone: 'success',
    path: '/subpackages/capabilities/app-authorizations/index',
  },
  {
    key: 'skills',
    emoji: '✨',
    title: '技能',
    subtitle: (c) => `已启用 ${c.skillsEnabled} / ${c.skills} 个原子技能`,
    badge: (c) => c.skillsEnabled,
    badgeTone: 'primary',
    path: '/subpackages/capabilities/skills/index',
  },
  {
    key: 'plugins',
    emoji: '🧩',
    title: '插件',
    subtitle: (c) => `已激活 ${c.pluginsEnabled} / ${c.plugins} 个行业垂直包`,
    badge: (c) => c.pluginsEnabled,
    badgeTone: 'primary',
    path: '/subpackages/capabilities/plugins/index',
  },
  {
    key: 'channels',
    emoji: '💬',
    title: '消息渠道',
    subtitle: (c) => `${c.channelsConnected} / ${c.channels} 个 IM 平台已接入`,
    badge: (c) => c.channelsConnected,
    badgeTone: 'success',
    path: '/subpackages/capabilities/message-channels/index',
  },
  {
    key: 'pairing',
    emoji: '👥',
    title: '配对授权',
    subtitle: (c) => (c.pairings > 0 ? `${c.pairings} 个用户等待审核` : '没有待审核的配对'),
    badge: (c) => c.pairings,
    badgeTone: 'warning',
    path: '/subpackages/capabilities/pairing-authorizations/index',
  },
]

export default function CapabilitiesIndex() {
  const [counts, setCounts] = useState<Counts>(ZERO)
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
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
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // 子页操作后回到入口需刷新计数
  useDidShow(() => {
    load()
  })

  const filtered = keyword.trim()
    ? CARDS.filter((c) => c.title.includes(keyword.trim()))
    : CARDS

  const handleClick = (card: CardDef) => {
    Taro.navigateTo({ url: card.path })
  }

  return (
    <ScrollView scrollY className='caps-index'>
      <View className='caps-header'>
        <Text className='caps-heading'>能力中心</Text>
        <Text className='caps-sub'>统一管理智能体的定时、授权、技能、插件、IM 与配对</Text>
      </View>

      <View className='caps-search'>
        <Text className='caps-search-icon'>🔍</Text>
        <Input
          className='caps-search-input'
          placeholder='搜索能力...'
          value={keyword}
          onInput={(e) => setKeyword(e.detail.value)}
        />
      </View>

      <View className='caps-grid'>
        {filtered.map((card) => {
          const badgeNum = card.badge ? card.badge(counts) : 0
          return (
            <View
              key={card.key}
              className='caps-card'
              onClick={() => handleClick(card)}
              hoverClass='caps-card--hover'
            >
              <View className='caps-card-emoji'>{card.emoji}</View>
              <View className='caps-card-body'>
                <View className='caps-card-titlerow'>
                  <Text className='caps-card-title'>{card.title}</Text>
                  {badgeNum > 0 && (
                    <View className={`caps-badge caps-badge--${card.badgeTone || 'primary'}`}>
                      <Text className='caps-badge-text'>{badgeNum}</Text>
                    </View>
                  )}
                </View>
                <Text className='caps-card-sub'>
                  {loading ? '加载中…' : card.subtitle(counts)}
                </Text>
              </View>
              <Text className='caps-card-arrow'>›</Text>
            </View>
          )
        })}
        {filtered.length === 0 && (
          <View className='caps-empty'>
            <Text className='caps-empty-icon'>🪶</Text>
            <Text className='caps-empty-text'>未找到匹配的能力</Text>
          </View>
        )}
      </View>
    </ScrollView>
  )
}
