/**
 * TaskStatusBadge — 8 状态徽标，running 状态带 Animated 脉冲
 *
 * 8 状态：queued / provisioning / running / reporting /
 *         done / failed / needs_approval / cancelled
 */
import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, Text, View } from 'react-native'

import type { AgentTaskStatus } from '@/lib/api/agentTasks'

const STATUS_META: Record<
  AgentTaskStatus,
  { label: string; bg: string; fg: string; pulse?: boolean }
> = {
  queued: { label: '排队中', bg: '#E5E5EA', fg: '#3C3C43' },
  provisioning: { label: '准备中', bg: '#D1E9FF', fg: '#0A66C2' },
  running: { label: '执行中', bg: '#D4EFDF', fg: '#1E8449', pulse: true },
  reporting: { label: '生成报告', bg: '#FCF3CF', fg: '#7D6608' },
  needs_approval: { label: '待审批', bg: '#FDEBD0', fg: '#9C640C' },
  done: { label: '已完成', bg: '#D5F5E3', fg: '#196F3D' },
  failed: { label: '失败', bg: '#FADBD8', fg: '#922B21' },
  cancelled: { label: '已取消', bg: '#EBDEF0', fg: '#6C3483' },
}

interface Props {
  status: AgentTaskStatus
  size?: 'sm' | 'md'
}

export function TaskStatusBadge({ status, size = 'md' }: Props) {
  const meta = STATUS_META[status] ?? STATUS_META.queued
  const pulse = useRef(new Animated.Value(0.4)).current

  useEffect(() => {
    if (!meta.pulse) return
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 700,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0.4,
          duration: 700,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    )
    loop.start()
    return () => {
      loop.stop()
    }
  }, [meta.pulse, pulse])

  const dot = meta.pulse ? (
    <Animated.View
      style={[
        styles.dot,
        { backgroundColor: meta.fg, opacity: pulse },
        size === 'sm' && styles.dotSm,
      ]}
    />
  ) : null

  return (
    <View
      style={[
        styles.badge,
        { backgroundColor: meta.bg },
        size === 'sm' && styles.badgeSm,
      ]}
    >
      {dot}
      <Text
        style={[
          styles.text,
          { color: meta.fg },
          size === 'sm' && styles.textSm,
        ]}
      >
        {meta.label}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    alignSelf: 'flex-start',
  },
  badgeSm: {
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 6,
  },
  dotSm: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    marginRight: 4,
  },
  text: {
    fontSize: 12,
    fontWeight: '600',
  },
  textSm: {
    fontSize: 11,
  },
})
