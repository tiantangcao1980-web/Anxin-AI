/**
 * P21-C 智能体工作台列表页
 *
 * - 顶部 search bar（"搜索智能体..."）
 * - 4 大组（法务 / 经营 / 增长 / 综合），每组下网格 2 列
 * - 卡片：emoji + 名称 + 一句话定位 + capabilities 数 + [开始对话] 按钮
 * - 点击卡片 → navigateTo chat/index?personaId=xxx
 * - 长按 → ActionSheet（查看详情 / 收藏 / 分享）
 *
 * 覆盖 P21-A 占位 stub。
 */

import { useEffect, useMemo, useState } from 'react'
import { View, Text, Input, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'

import {
  listPersonas,
  groupPersonas,
  type Persona,
  type PersonaGroup,
} from '../_mock/index'

import './index.scss'

export default function PersonasIndex() {
  const [personas, setPersonas] = useState<Persona[]>([])
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const [favorites, setFavorites] = useState<string[]>([])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    listPersonas()
      .then((data) => {
        if (!cancelled) setPersonas(data)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    // 收藏从 storage 拿
    try {
      const fav = Taro.getStorageSync('persona_favorites')
      if (Array.isArray(fav)) setFavorites(fav)
    } catch {
      /* ignore */
    }
    return () => {
      cancelled = true
    }
  }, [])

  // 关键词过滤后再分组
  const filteredGroups: PersonaGroup[] = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    const filtered = !kw
      ? personas
      : personas.filter(
          (p) =>
            p.display_name.toLowerCase().includes(kw) ||
            p.description.toLowerCase().includes(kw) ||
            p.capabilities.some((c) => c.toLowerCase().includes(kw)),
        )
    return groupPersonas(filtered)
  }, [keyword, personas])

  const handleOpenChat = (p: Persona) => {
    Taro.navigateTo({
      url: `/subpackages/personas/chat/index?personaId=${p.persona_id}`,
    })
  }

  const handleOpenDetail = (p: Persona) => {
    Taro.navigateTo({
      url: `/subpackages/personas/detail/index?personaId=${p.persona_id}`,
    })
  }

  const handleLongPress = (p: Persona) => {
    Taro.showActionSheet({
      itemList: [
        '查看详情',
        favorites.includes(p.persona_id) ? '取消收藏' : '收藏',
        '分享',
      ],
      success: (res) => {
        if (res.tapIndex === 0) {
          handleOpenDetail(p)
        } else if (res.tapIndex === 1) {
          const next = favorites.includes(p.persona_id)
            ? favorites.filter((id) => id !== p.persona_id)
            : [...favorites, p.persona_id]
          setFavorites(next)
          try {
            Taro.setStorageSync('persona_favorites', next)
          } catch {
            /* ignore */
          }
          Taro.showToast({
            title: favorites.includes(p.persona_id) ? '已取消收藏' : '已收藏',
            icon: 'success',
            duration: 1200,
          })
        } else if (res.tapIndex === 2) {
          Taro.showToast({ title: '请使用右上角胶囊分享', icon: 'none' })
        }
      },
    })
  }

  return (
    <View className='personas-page'>
      {/* 顶部 search bar */}
      <View className='search-bar'>
        <View className='search-input-wrapper'>
          <Text className='search-icon'>🔍</Text>
          <Input
            className='search-input'
            placeholder='搜索智能体...'
            value={keyword}
            onInput={(e) => setKeyword(e.detail.value)}
            confirmType='search'
          />
          {keyword ? (
            <Text className='search-clear' onClick={() => setKeyword('')}>
              ✕
            </Text>
          ) : null}
        </View>
      </View>

      <ScrollView className='groups-scroll' scrollY enhanced showScrollbar={false}>
        {loading ? (
          <View className='loading-block'>
            <Text className='loading-text'>智能体加载中...</Text>
          </View>
        ) : filteredGroups.length === 0 ? (
          <View className='empty-block'>
            <Text className='empty-emoji'>🤔</Text>
            <Text className='empty-title'>没有匹配的智能体</Text>
            <Text className='empty-desc'>试试换个关键词</Text>
          </View>
        ) : (
          filteredGroups.map((group) => (
            <View key={group.label} className='group-section'>
              <View className='group-header'>
                <Text className='group-title'>{group.label}</Text>
                <Text className='group-count'>共 {group.personas.length} 个</Text>
              </View>
              <View className='persona-grid'>
                {group.personas.map((p) => (
                  <View
                    key={p.persona_id}
                    className='persona-card'
                    onClick={() => handleOpenChat(p)}
                    onLongPress={() => handleLongPress(p)}
                  >
                    <View className='card-head'>
                      <Text className='card-emoji'>{p.emoji}</Text>
                      {favorites.includes(p.persona_id) ? (
                        <Text className='card-fav'>★</Text>
                      ) : null}
                    </View>
                    <Text className='card-name'>{p.display_name}</Text>
                    <Text className='card-desc'>{p.description}</Text>
                    <View className='card-meta'>
                      <Text className='card-cap'>
                        {p.capabilities.length} 项能力
                      </Text>
                      <Text
                        className={`card-tag ${p.is_implemented ? 'tag-on' : 'tag-plan'}`}
                      >
                        {p.is_implemented ? '已实装' : '规划中'}
                      </Text>
                    </View>
                    <View
                      className='card-cta'
                      onClick={(e) => {
                        e.stopPropagation()
                        handleOpenChat(p)
                      }}
                    >
                      <Text className='cta-text'>开始对话 →</Text>
                    </View>
                  </View>
                ))}
              </View>
            </View>
          ))
        )}
        <View className='page-footer'>
          <Text className='footer-text'>共 {personas.length} 个智能体 · 长按卡片查看更多</Text>
        </View>
      </ScrollView>
    </View>
  )
}
