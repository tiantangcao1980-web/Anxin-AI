// -*- coding: utf-8 -*-
import { View, Text, StyleSheet, Switch } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import type { Skill } from '@/lib/api/skills'

/**
 * SkillToggleRow — 技能开关行 (按域分组的列表项)
 *
 * 移动端做法:
 *   - 单行 + Switch 直接生效 (Optimistic UI)
 *   - 触发词以 chip 折叠为单行,避免过载
 */

interface Props {
  skill: Skill
  onToggle: (skill: Skill, next: boolean) => void
}

export function SkillToggleRow({ skill, onToggle }: Props) {
  return (
    <View style={styles.row}>
      <View style={styles.icon}>
        <Ionicons name="sparkles-outline" size={18} color={Colors.primary} />
      </View>
      <View style={styles.body}>
        <Text style={styles.title} numberOfLines={1}>
          {skill.display_name}
        </Text>
        <Text style={styles.desc} numberOfLines={1}>
          {skill.description}
        </Text>
      </View>
      <Switch
        value={skill.enabled}
        onValueChange={(v) => onToggle(skill, v)}
        trackColor={{ false: Colors.border, true: Colors.primary + '60' }}
        thumbColor={skill.enabled ? Colors.primary : Colors.surface}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: 12,
    backgroundColor: Colors.background,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  icon: {
    width: 32,
    height: 32,
    borderRadius: 10,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1 },
  title: { fontSize: Layout.fontSize.md, fontWeight: '500', color: Colors.text },
  desc: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
})
