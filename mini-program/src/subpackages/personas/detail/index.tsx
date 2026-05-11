/**
 * P21-C 智能体详情页
 *
 * - 顶部：emoji + 名称 + 描述
 * - 标签栏：能力 / Skills / 集成应用 / 示例对话
 * - 能力列表（5-7 项）
 * - 关联 skills + 集成应用 chips
 * - 2 个示例对话气泡
 * - 底部固定 [开始对话] CTA → 跳 chat
 */

import { useEffect, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'

import { getPersona, type Persona } from '../_mock/index'

import './index.scss'

type TabKey = 'capabilities' | 'skills' | 'apps' | 'samples'

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: 'capabilities', label: '能力' },
  { key: 'skills', label: 'Skills' },
  { key: 'apps', label: '集成应用' },
  { key: 'samples', label: '示例对话' },
]

export default function PersonaDetail() {
  const router = useRouter()
  const personaId = (router.params.personaId as string) || ''

  const [persona, setPersona] = useState<Persona | undefined>()
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<TabKey>('capabilities')

  useEffect(() => {
    let cancelled = false
    if (!personaId) {
      setLoading(false)
      return
    }
    setLoading(true)
    getPersona(personaId)
      .then((p) => {
        if (!cancelled) setPersona(p)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [personaId])

  const handleStartChat = () => {
    if (!persona) return
    Taro.redirectTo({
      url: `/subpackages/personas/chat/index?personaId=${persona.persona_id}`,
    })
  }

  if (loading) {
    return (
      <View className='detail-page'>
        <View className='loading-block'>
          <Text className='loading-text'>详情加载中...</Text>
        </View>
      </View>
    )
  }

  if (!persona) {
    return (
      <View className='detail-page'>
        <View className='loading-block'>
          <Text className='loading-text'>未找到该智能体</Text>
          <View
            className='back-btn'
            onClick={() => Taro.navigateBack({ delta: 1 })}
          >
            <Text>返回</Text>
          </View>
        </View>
      </View>
    )
  }

  return (
    <View className='detail-page'>
      <ScrollView className='detail-scroll' scrollY enhanced showScrollbar={false}>
        {/* 顶部 hero */}
        <View className='hero'>
          <View className='hero-emoji-wrap'>
            <Text className='hero-emoji'>{persona.emoji}</Text>
          </View>
          <Text className='hero-name'>{persona.display_name}</Text>
          <Text
            className={`hero-tag ${persona.is_implemented ? 'tag-on' : 'tag-plan'}`}
          >
            {persona.is_implemented ? '后端已实装' : '规划中 · mock 应答'}
          </Text>
          <Text className='hero-desc'>{persona.description}</Text>
        </View>

        {/* 标签栏 */}
        <View className='tab-bar'>
          {TABS.map((t) => (
            <View
              key={t.key}
              className={`tab-item ${tab === t.key ? 'active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              <Text className='tab-label'>{t.label}</Text>
              <View className='tab-underline' />
            </View>
          ))}
        </View>

        {/* tab content */}
        <View className='tab-content'>
          {tab === 'capabilities' && (
            <View className='cap-list'>
              {persona.capabilities.map((c, i) => (
                <View key={i} className='cap-item'>
                  <Text className='cap-num'>{(i + 1).toString().padStart(2, '0')}</Text>
                  <Text className='cap-text'>{c}</Text>
                </View>
              ))}
            </View>
          )}
          {tab === 'skills' && (
            <View className='chip-list'>
              {persona.backed_by_skills.map((s) => (
                <Text key={s} className='chip skill-chip'>
                  {s}
                </Text>
              ))}
              <View className='sub-title'>
                <Text>关联 Specialized Agents</Text>
              </View>
              {persona.backed_by_agents.map((a) => (
                <Text key={a} className='chip agent-chip'>
                  {a}
                </Text>
              ))}
            </View>
          )}
          {tab === 'apps' && (
            <View className='chip-list'>
              {persona.supported_apps.map((a) => (
                <Text key={a} className='chip app-chip'>
                  {a}
                </Text>
              ))}
              <Text className='helper-text'>
                共 {persona.supported_apps.length} 个集成应用，可在云端模式下直接调用。
              </Text>
            </View>
          )}
          {tab === 'samples' && (
            <View className='samples-list'>
              {persona.sample_dialogs.slice(0, 2).map((d, i) => (
                <View key={i} className='sample-block'>
                  <View className='bubble user-bubble'>
                    <Text>{d.q}</Text>
                  </View>
                  <View className='bubble ai-bubble'>
                    <Text className='bubble-emoji'>{persona.emoji}</Text>
                    <Text className='bubble-text'>{d.a}</Text>
                  </View>
                </View>
              ))}
              {persona.sample_dialogs.length > 2 && (
                <Text className='helper-text'>
                  还有 {persona.sample_dialogs.length - 2} 条示例，进入对话后逐步解锁。
                </Text>
              )}
            </View>
          )}
        </View>

        {/* 底部留白 给固定 CTA */}
        <View style={{ height: '160rpx' }} />
      </ScrollView>

      {/* 底部固定 CTA */}
      <View className='cta-bar'>
        <View className='cta-btn' onClick={handleStartChat}>
          <Text className='cta-text'>开始对话</Text>
        </View>
      </View>
    </View>
  )
}
