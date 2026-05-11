// -*- coding: utf-8 -*-
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'

/**
 * CapabilityCategoryCard — 能力中心入口卡片(列表行样式)
 *
 * 移动端 vs Web:
 *   - Web 是 4 列网格;移动端只用单列 list,降低误触并提升单手可达性
 *   - 通过 right chevron + 数字角标暗示可点击
 */

interface Props {
  icon: keyof typeof Ionicons.glyphMap
  title: string
  description: string
  badge?: number | string
  badgeTone?: 'primary' | 'success' | 'warning'
  onPress: () => void
}

export function CapabilityCategoryCard({
  icon,
  title,
  description,
  badge,
  badgeTone = 'primary',
  onPress,
}: Props) {
  const tone = badgeTone === 'warning'
    ? Colors.warning
    : badgeTone === 'success'
      ? Colors.success
      : Colors.primary

  return (
    <TouchableOpacity style={styles.row} activeOpacity={0.7} onPress={onPress}>
      <View style={[styles.iconWrap, { backgroundColor: Colors.primary + '15' }]}>
        <Ionicons name={icon} size={22} color={Colors.primary} />
      </View>
      <View style={styles.body}>
        <View style={styles.titleRow}>
          <Text style={styles.title}>{title}</Text>
          {badge !== undefined && badge !== 0 && (
            <View style={[styles.badge, { backgroundColor: tone + '20' }]}>
              <Text style={[styles.badgeText, { color: tone }]}>{String(badge)}</Text>
            </View>
          )}
        </View>
        <Text style={styles.desc} numberOfLines={2}>
          {description}
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  row: {
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
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  title: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  desc: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 999,
  },
  badgeText: { fontSize: 11, fontWeight: '600' },
})
