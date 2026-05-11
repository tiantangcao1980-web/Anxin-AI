// -*- coding: utf-8 -*-
import { useEffect, useState, useRef } from 'react'
import {
  View,
  Text,
  StyleSheet,
  Animated,
  PanResponder,
  TouchableOpacity,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import type { PairingRequest } from '@/lib/api/__mocks__/capabilities.mock'

/**
 * PairingRequestCard — 配对请求卡 (含 swipe-to-action + 24h 倒计时)
 *
 * 移动端 vs Web:
 *   - Web 版用按钮 + 弹窗;移动端用 swipe 手势:
 *     - 左滑 (拖动 < -60px) → 显示「批准」操作,松手批准
 *     - 右滑 (拖动 > 60px) → 显示「拒绝」操作,松手拒绝
 *   - 倒计时倒着 24h 实时跳动,提醒人主动操作
 *   - 临近过期 (< 2h) 红色警示
 *
 * 实现说明:
 *   - 使用 RN 内置 PanResponder + Animated 而非 react-native-gesture-handler 的
 *     Swipeable,以零额外依赖跑通,且与 expo Tabs router 兼容更好
 */

interface Props {
  request: PairingRequest
  onApprove: (req: PairingRequest) => void
  onReject: (req: PairingRequest) => void
}

const SWIPE_THRESHOLD = 60
const ACTION_REVEAL = 90

export function PairingRequestCard({ request, onApprove, onReject }: Props) {
  const translateX = useRef(new Animated.Value(0)).current
  const remaining = useCountdown(request.expires_at)
  const urgent = remaining.hours < 2 && remaining.totalMs > 0
  const expired = remaining.totalMs <= 0

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 8,
      onPanResponderMove: (_, g) => {
        translateX.setValue(g.dx)
      },
      onPanResponderRelease: (_, g) => {
        if (g.dx <= -SWIPE_THRESHOLD) {
          // 左滑 → 批准
          Animated.timing(translateX, {
            toValue: -400,
            duration: 200,
            useNativeDriver: true,
          }).start(() => onApprove(request))
        } else if (g.dx >= SWIPE_THRESHOLD) {
          // 右滑 → 拒绝
          Animated.timing(translateX, {
            toValue: 400,
            duration: 200,
            useNativeDriver: true,
          }).start(() => onReject(request))
        } else {
          Animated.spring(translateX, {
            toValue: 0,
            useNativeDriver: true,
            friction: 6,
          }).start()
        }
      },
    }),
  ).current

  return (
    <View style={styles.wrap}>
      {/* 背景操作区 (左侧:拒绝;右侧:批准 — 与滑动方向相反) */}
      <View style={styles.bg} pointerEvents="none">
        <View
          style={[styles.bgAction, { backgroundColor: Colors.error, alignItems: 'flex-start' }]}
        >
          <Ionicons name="close-circle" size={20} color={Colors.white} />
          <Text style={styles.bgText}>拒绝</Text>
        </View>
        <View
          style={[styles.bgAction, { backgroundColor: Colors.success, alignItems: 'flex-end' }]}
        >
          <Ionicons name="checkmark-circle" size={20} color={Colors.white} />
          <Text style={styles.bgText}>批准</Text>
        </View>
      </View>

      <Animated.View
        style={[styles.card, { transform: [{ translateX }] }]}
        {...panResponder.panHandlers}
      >
        <View style={styles.avatar}>
          <Ionicons name="person" size={22} color={Colors.white} />
        </View>
        <View style={styles.body}>
          <View style={styles.titleRow}>
            <Text style={styles.name}>{request.external_user_name}</Text>
            <Text style={styles.channel}>· {request.channel_name}</Text>
          </View>
          {request.external_group_name && (
            <Text style={styles.group} numberOfLines={1}>
              在群「{request.external_group_name}」
            </Text>
          )}
          <View style={styles.countdownRow}>
            <Ionicons
              name={expired ? 'alert-circle' : 'time-outline'}
              size={12}
              color={expired ? Colors.error : urgent ? Colors.warning : Colors.textMuted}
            />
            <Text
              style={[
                styles.countdown,
                {
                  color: expired
                    ? Colors.error
                    : urgent
                      ? Colors.warning
                      : Colors.textSecondary,
                },
              ]}
            >
              {expired
                ? '已过期'
                : `剩余 ${remaining.hours}h ${remaining.minutes}m`}
            </Text>
          </View>
        </View>
        {/* fallback 按钮 (无障碍 + 不能 swipe 的设备) */}
        <View style={styles.actionsCol}>
          <TouchableOpacity
            style={[styles.smallBtn, { backgroundColor: Colors.success + '20' }]}
            onPress={() => onApprove(request)}
            accessibilityLabel="批准"
          >
            <Ionicons name="checkmark" size={18} color={Colors.success} />
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.smallBtn, { backgroundColor: Colors.error + '20' }]}
            onPress={() => onReject(request)}
            accessibilityLabel="拒绝"
          >
            <Ionicons name="close" size={18} color={Colors.error} />
          </TouchableOpacity>
        </View>
      </Animated.View>

      <Text style={styles.hint}>左滑批准 · 右滑拒绝</Text>
    </View>
  )
}

interface Remaining {
  totalMs: number
  hours: number
  minutes: number
}

function useCountdown(expiresAt: string): Remaining {
  const compute = (): Remaining => {
    const totalMs = new Date(expiresAt).getTime() - Date.now()
    if (totalMs <= 0) return { totalMs: 0, hours: 0, minutes: 0 }
    const hours = Math.floor(totalMs / 3600000)
    const minutes = Math.floor((totalMs % 3600000) / 60000)
    return { totalMs, hours, minutes }
  }
  const [val, setVal] = useState<Remaining>(compute)
  useEffect(() => {
    const id = setInterval(() => setVal(compute()), 30 * 1000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expiresAt])
  return val
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: Colors.background,
    paddingVertical: 4,
  },
  bg: {
    ...StyleSheet.absoluteFillObject,
    flexDirection: 'row',
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: 4,
  },
  bgAction: {
    flex: 1,
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Layout.spacing.md,
    borderRadius: Layout.borderRadius.md,
  },
  bgText: { color: Colors.white, fontSize: Layout.fontSize.sm, fontWeight: '600' },
  card: {
    marginHorizontal: Layout.spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center' },
  name: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  channel: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginLeft: 4 },
  group: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  countdownRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 6,
  },
  countdown: { fontSize: Layout.fontSize.xs, fontWeight: '500' },
  actionsCol: { flexDirection: 'row', gap: 6 },
  smallBtn: {
    width: 32,
    height: 32,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hint: {
    marginTop: 4,
    paddingHorizontal: Layout.spacing.md + 52,
    fontSize: 10,
    color: Colors.textMuted,
  },
})
