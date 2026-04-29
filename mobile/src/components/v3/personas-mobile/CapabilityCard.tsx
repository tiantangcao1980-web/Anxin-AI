/**
 * CapabilityCard（移动端）
 *
 * 列表项,点击触发 capability。
 * 显示 label + sample prompt 灰字。
 */

import React from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '../../../constants/colors'
import { Layout } from '../../../constants/layout'
import type { PersonaCapability } from '../../../lib/personas/registry'

interface CapabilityCardProps {
  capability: PersonaCapability
  pending?: boolean
  onTrigger: (capability: PersonaCapability) => void
}

export function CapabilityCard({ capability, pending, onTrigger }: CapabilityCardProps) {
  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => onTrigger(capability)}
      disabled={pending}
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityLabel={capability.label}
    >
      <View style={styles.iconWrap}>
        <Ionicons name="flash-outline" size={20} color={Colors.primary} />
      </View>
      <View style={styles.body}>
        <Text style={styles.label} numberOfLines={1}>
          {capability.label}
        </Text>
        <Text style={styles.prompt} numberOfLines={2}>
          {capability.prompt}
        </Text>
      </View>
      {pending ? (
        <ActivityIndicator size="small" color={Colors.primary} />
      ) : (
        <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
      )}
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: `${Colors.primary}1A`,
  },
  body: {
    flex: 1,
    minWidth: 0,
  },
  label: {
    fontSize: Layout.fontSize.md,
    fontWeight: '600',
    color: Colors.text,
  },
  prompt: {
    marginTop: 2,
    fontSize: Layout.fontSize.xs,
    color: Colors.textSecondary,
    lineHeight: 18,
  },
})
