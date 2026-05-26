// -*- coding: utf-8 -*-
/**
 * 工作台 tab — 飞书风首页。
 *
 * 内容：
 *   - 顶部欢迎卡 + 业务域分组
 *   - 10 智能体入口（按业务域分组：综合协调 / 合规经营 / 增长获客 / 出海跨境）
 *   - 点击进入 persona 工作台（路由 /personas/[id]）
 *
 * 关联：docs/plans/2026-05-22-product-blueprint.md §3.2
 * 历史：原 personas.tsx（V3 P17-A 占位），2026-05-26 升级为飞书风 4 tab 中的"工作台"
 */

import React from 'react'
import { ScrollView, View, Text, TouchableOpacity, StyleSheet } from 'react-native'
import { useRouter } from 'expo-router'
import { useV3Theme } from '@/theme'

interface PersonaCard {
  id: string
  emoji: string
  name: string
  domain: '综合协调' | '合规经营' | '增长获客' | '出海跨境'
}

const PERSONAS: PersonaCard[] = [
  { id: 'anxin', emoji: '🎯', name: '安心助理', domain: '综合协调' },
  { id: 'process', emoji: '📋', name: '流程管家', domain: '综合协调' },
  { id: 'legal', emoji: '⚖️', name: '法律顾问', domain: '合规经营' },
  { id: 'contract', emoji: '📄', name: '合同管家', domain: '合规经营' },
  { id: 'dd', emoji: '🔍', name: '尽调专家', domain: '合规经营' },
  { id: 'finance', emoji: '💰', name: '财税顾问', domain: '合规经营' },
  { id: 'market', emoji: '📊', name: '市场研究员', domain: '增长获客' },
  { id: 'sales', emoji: '🎯', name: '获客猎手', domain: '增长获客' },
  { id: 'content', emoji: '✍️', name: '内容总监', domain: '增长获客' },
  { id: 'ecommerce', emoji: '🌍', name: '跨境电商助手', domain: '出海跨境' },
]

const DOMAIN_ORDER: PersonaCard['domain'][] = [
  '综合协调',
  '合规经营',
  '增长获客',
  '出海跨境',
]

export default function WorkbenchTabScreen() {
  const t = useV3Theme()
  const router = useRouter()

  const grouped = DOMAIN_ORDER.map((domain) => ({
    domain,
    items: PERSONAS.filter((p) => p.domain === domain),
  }))

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: t.colors.backgroundMuted }}
      contentContainerStyle={styles.scroll}
    >
      <View style={[styles.header, { backgroundColor: t.colors.surface, borderBottomColor: t.colors.divider }]}>
        <Text style={[styles.headerTitle, { color: t.colors.text }]}>工作台</Text>
        <Text style={[styles.headerSub, { color: t.colors.textSecondary }]}>
          10 个智能体随时待命，按业务域分组
        </Text>
      </View>

      {grouped.map(({ domain, items }) => (
        <View key={domain} style={styles.section}>
          <Text style={[styles.sectionTitle, { color: t.colors.textSecondary }]}>{domain}</Text>
          <View style={styles.grid}>
            {items.map((persona) => (
              <TouchableOpacity
                key={persona.id}
                style={[styles.card, { backgroundColor: t.colors.surface, borderColor: t.colors.border }]}
                onPress={() => router.push(`/personas/${persona.id}` as never)}
                activeOpacity={0.7}
              >
                <Text style={styles.emoji}>{persona.emoji}</Text>
                <Text style={[styles.cardTitle, { color: t.colors.text }]} numberOfLines={1}>
                  {persona.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      ))}

      <View style={styles.footer}>
        <Text style={[styles.footerText, { color: t.colors.textMuted }]}>
          长按智能体可设为快捷入口（待 P17-B 接入）
        </Text>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 32,
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 0.5,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '600',
  },
  headerSub: {
    fontSize: 13,
    marginTop: 4,
  },
  section: {
    paddingHorizontal: 16,
    paddingTop: 20,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '500',
    marginBottom: 10,
    letterSpacing: 0.5,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -4,
  },
  card: {
    width: '31%',
    marginHorizontal: '1.16%',
    marginBottom: 8,
    paddingVertical: 16,
    paddingHorizontal: 8,
    borderRadius: 12,
    borderWidth: 0.5,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 88,
  },
  emoji: {
    fontSize: 28,
    marginBottom: 6,
    textAlign: 'center',
  },
  cardTitle: {
    fontSize: 12,
    fontWeight: '500',
    textAlign: 'center',
  },
  footer: {
    padding: 16,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 11,
  },
})
