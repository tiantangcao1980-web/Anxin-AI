// -*- coding: utf-8 -*-
/**
 * Home tabBar —— 智能体首页
 *
 * 区块：
 *   1. Hero — 你好 {nickname} + 子标题
 *   2. 4 大业务域分组入口（点击跳 personas 分包列表 + 默认筛选）
 *   3. 10 个 personas 卡片（横向 ScrollView）
 *   4. 推荐场景 chips —— 直接发起对话
 */

import { useEffect, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { usePullDownRefresh } from '@tarojs/taro'

import { Screen } from '../../components/Layout'
import PersonaCard from '../../components/PersonaCard'
import { listPersonas } from '../../utils/api/personas'
import { tokenStorage } from '../../utils/auth/token'
import {
  PERSONA_SEEDS,
  DOMAIN_LIST,
  RECOMMENDED_PROMPTS,
  type SeededPersona,
} from '../../utils/personaSeeds'
import type { Persona, PersonaDomain } from '../../types/persona'
import './index.scss'

export default function HomePage() {
  const [personas, setPersonas] = useState<Persona[]>(PERSONA_SEEDS)
  const [nickname, setNickname] = useState('朋友')

  useEffect(() => {
    const u = tokenStorage.getUser()
    if (u?.name) setNickname(u.name)
    void loadPersonas()
  }, [])

  usePullDownRefresh(() => {
    loadPersonas().finally(() => Taro.stopPullDownRefresh())
  })

  async function loadPersonas() {
    if (!tokenStorage.isAuthenticated()) return
    try {
      const list = await listPersonas()
      if (Array.isArray(list) && list.length > 0) {
        // merge：以后端为主，缺 domain 时 fallback 到 seeds
        const seedMap = new Map<string, SeededPersona>(
          PERSONA_SEEDS.map((s) => [s.persona_id, s]),
        )
        const merged = list.map((p) => {
          const seed = seedMap.get(p.persona_id)
          return {
            ...seed,
            ...p,
            domain: p.domain || seed?.domain,
            is_implemented: p.is_implemented ?? seed?.is_implemented,
          } as Persona
        })
        setPersonas(merged)
      }
    } catch {
      // 静默失败 —— 保持 seeds 即可
    }
  }

  function handleDomainTap(domain: PersonaDomain) {
    Taro.navigateTo({
      url: `/subpackages/personas/index/index?domain=${encodeURIComponent(domain)}`,
    }).catch(() => {
      Taro.showToast({ title: 'P21-C 即将就位', icon: 'none' })
    })
  }

  function handlePersonaTap(persona: Persona) {
    Taro.navigateTo({
      url: `/subpackages/personas/detail/index?id=${encodeURIComponent(persona.persona_id)}`,
    }).catch(() => {
      Taro.showToast({ title: 'P21-C 即将就位', icon: 'none' })
    })
  }

  function handlePromptTap(prompt: { text: string; persona_id: string }) {
    const target =
      `/subpackages/personas/chat/index?id=${encodeURIComponent(prompt.persona_id)}` +
      `&prompt=${encodeURIComponent(prompt.text)}`
    Taro.navigateTo({ url: target }).catch(() => {
      Taro.showToast({ title: prompt.text, icon: 'none' })
    })
  }

  return (
    <Screen padded={false}>
      {/* Hero */}
      <View className='home-hero'>
        <Text className='home-hero__greeting'>你好，{nickname}</Text>
        <Text className='home-hero__sub'>选一个智能体，让它替你跑腿</Text>
      </View>

      {/* 4 大分类 */}
      <View className='home-domains'>
        {DOMAIN_LIST.map((d) => (
          <View
            key={d.domain}
            className='home-domains__item'
            onClick={() => handleDomainTap(d.domain)}
          >
            <Text className='home-domains__emoji'>{d.emoji}</Text>
            <Text className='home-domains__name'>{d.domain}</Text>
            <Text className='home-domains__desc'>{d.description}</Text>
          </View>
        ))}
      </View>

      {/* 10 personas 横向滚动 */}
      <View className='home-section'>
        <View className='home-section__head'>
          <Text className='home-section__title'>10 位智能助手</Text>
          <Text className='home-section__sub'>挑一个交付工作</Text>
        </View>
        <ScrollView
          className='home-personas'
          scrollX
          enableFlex
          showScrollbar={false}
        >
          {personas.map((p) => (
            <PersonaCard
              key={p.persona_id}
              persona={p}
              compact
              onClick={handlePersonaTap}
            />
          ))}
        </ScrollView>
      </View>

      {/* 推荐场景 chips */}
      <View className='home-section'>
        <View className='home-section__head'>
          <Text className='home-section__title'>试试这些场景</Text>
        </View>
        <View className='home-prompts'>
          {RECOMMENDED_PROMPTS.map((p, i) => (
            <View
              key={i}
              className='home-prompts__chip'
              onClick={() => handlePromptTap(p)}
            >
              <Text className='home-prompts__text'>{p.text}</Text>
            </View>
          ))}
        </View>
      </View>

      <View className='home-footer'>
        <Text className='home-footer__text'>
          安心智能助手 V3 · 制造业全链路 AI 助手
        </Text>
      </View>
    </Screen>
  )
}
