/**
 * PersonaHeader（移动端详情页头部）
 *
 * 顶部：emoji + 名称 + 状态 badge
 * 底部：tab 切换（工作台 / chat / 能力）
 */

import React from 'react'
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native'
import { Colors } from '../../../constants/colors'
import { Layout } from '../../../constants/layout'
import { DOMAIN_COLOR, type PersonaMeta } from '../../../lib/personas/registry'

export type PersonaTabKey = 'home' | 'chat' | 'capabilities'

interface TabSpec {
  key: PersonaTabKey
  label: string
}

const TABS: TabSpec[] = [
  { key: 'home', label: '工作台' },
  { key: 'chat', label: '对话' },
  { key: 'capabilities', label: '能力' },
]

interface PersonaHeaderProps {
  persona: PersonaMeta
  active: PersonaTabKey
  onChangeTab: (next: PersonaTabKey) => void
}

export function PersonaHeader({ persona, active, onChangeTab }: PersonaHeaderProps) {
  const domainColor = DOMAIN_COLOR[persona.domain]
  return (
    <View style={styles.container}>
      <View style={styles.titleRow}>
        <Text style={styles.emoji}>{persona.emoji}</Text>
        <View style={styles.titleCol}>
          <View style={styles.nameRow}>
            <Text style={styles.name} numberOfLines={1}>
              {persona.display_name}
            </Text>
            <View
              style={[
                styles.statusBadge,
                { backgroundColor: persona.is_implemented ? '#DCFCE7' : '#FEF3C7' },
              ]}
            >
              <Text
                style={[
                  styles.statusText,
                  { color: persona.is_implemented ? '#15803D' : '#B45309' },
                ]}
              >
                {persona.is_implemented ? '已实装' : '规划中'}
              </Text>
            </View>
          </View>
          <Text style={styles.tagline} numberOfLines={2}>
            {persona.tagline}
          </Text>
          <View style={[styles.domainChip, { backgroundColor: `${domainColor}1A`, borderColor: `${domainColor}40` }]}>
            <Text style={[styles.domainText, { color: domainColor }]}>{persona.domain}</Text>
          </View>
        </View>
      </View>

      <View style={styles.tabsRow}>
        {TABS.map((tab) => {
          const focused = tab.key === active
          return (
            <TouchableOpacity
              key={tab.key}
              style={[styles.tabBtn, focused && styles.tabBtnActive]}
              onPress={() => onChangeTab(tab.key)}
              activeOpacity={0.7}
              accessibilityRole="tab"
              accessibilityState={{ selected: focused }}
            >
              <Text style={[styles.tabText, focused && styles.tabTextActive]}>{tab.label}</Text>
            </TouchableOpacity>
          )
        })}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.background,
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  titleRow: {
    flexDirection: 'row',
    gap: Layout.spacing.md,
    alignItems: 'flex-start',
  },
  emoji: {
    fontSize: 40,
    lineHeight: 48,
  },
  titleCol: {
    flex: 1,
    minWidth: 0,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
  },
  name: {
    fontSize: Layout.fontSize.lg,
    fontWeight: '700',
    color: Colors.text,
    maxWidth: '70%',
  },
  statusBadge: {
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 2,
    borderRadius: Layout.borderRadius.sm,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '600',
  },
  tagline: {
    marginTop: 4,
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    lineHeight: 20,
  },
  domainChip: {
    alignSelf: 'flex-start',
    marginTop: 6,
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 2,
    borderRadius: Layout.borderRadius.sm,
    borderWidth: StyleSheet.hairlineWidth,
  },
  domainText: {
    fontSize: 10,
    fontWeight: '600',
  },
  tabsRow: {
    flexDirection: 'row',
    marginTop: Layout.spacing.md,
    gap: Layout.spacing.lg,
  },
  tabBtn: {
    paddingVertical: Layout.spacing.sm,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabBtnActive: {
    borderBottomColor: Colors.primary,
  },
  tabText: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
  },
  tabTextActive: {
    color: Colors.primary,
    fontWeight: '600',
  },
})
