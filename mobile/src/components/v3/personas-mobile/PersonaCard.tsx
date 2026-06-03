/**
 * PersonaCard（移动端）
 *
 * 2 列网格里的单卡：emoji + display_name + 一句话 + 状态 badge + 域 chip。
 */

import React from 'react'
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native'
import { Colors } from '../../../constants/colors'
import { Layout } from '../../../constants/layout'
import { palette } from '../../../theme/colors'
import { DOMAIN_COLOR, type PersonaMeta } from '../../../lib/personas/registry'

interface PersonaCardProps {
  persona: PersonaMeta
  onPress: () => void
}

export function PersonaCard({ persona, onPress }: PersonaCardProps) {
  const domainColor = DOMAIN_COLOR[persona.domain]
  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityLabel={`${persona.display_name},${persona.tagline}`}
    >
      <View style={styles.headerRow}>
        <Text style={styles.emoji}>{persona.emoji}</Text>
        <View
          style={[
            styles.statusBadge,
            { backgroundColor: persona.is_implemented ? palette.successSoft : palette.warningSoft },
          ]}
        >
          <Text
            style={[
              styles.statusText,
              { color: persona.is_implemented ? palette.success : palette.warning },
            ]}
          >
            {persona.is_implemented ? '已实装' : '规划中'}
          </Text>
        </View>
      </View>

      <Text style={styles.name} numberOfLines={1}>
        {persona.display_name}
      </Text>
      <Text style={styles.tagline} numberOfLines={3}>
        {persona.tagline}
      </Text>

      <View style={styles.footerRow}>
        <View style={[styles.domainChip, { backgroundColor: `${domainColor}1A`, borderColor: `${domainColor}40` }]}>
          <Text style={[styles.domainText, { color: domainColor }]}>{persona.domain}</Text>
        </View>
        <Text style={styles.capCount}>{persona.capabilities.length} 能力</Text>
      </View>
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.lg,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
    minHeight: 168,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  emoji: {
    fontSize: 32,
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
  name: {
    marginTop: Layout.spacing.sm,
    fontSize: Layout.fontSize.md,
    fontWeight: '700',
    color: Colors.text,
  },
  tagline: {
    marginTop: 4,
    fontSize: Layout.fontSize.xs,
    color: Colors.textSecondary,
    lineHeight: 18,
  },
  footerRow: {
    marginTop: 'auto',
    paddingTop: Layout.spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  domainChip: {
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 2,
    borderRadius: Layout.borderRadius.sm,
    borderWidth: StyleSheet.hairlineWidth,
  },
  domainText: {
    fontSize: 10,
    fontWeight: '600',
  },
  capCount: {
    fontSize: 10,
    color: Colors.textMuted,
  },
})
