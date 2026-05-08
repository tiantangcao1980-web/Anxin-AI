import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Stack, router } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import {
  buildDesktopControlGate,
  getDesktopControlLoadErrorMessage,
  type RemoteControlStatusResponse,
} from '@/features/desktop-control/model'
import { usePrivacy } from '@/lib/privacy-context'
import { desktopControlApi } from '@/services/api'

export default function DesktopControlScreen() {
  const { mode: privacyMode } = usePrivacy()
  const [status, setStatus] = useState<RemoteControlStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadStatus = useCallback(async () => {
    if (privacyMode === 'local') {
      setStatus(null)
      setError(null)
      setLoading(false)
      setRefreshing(false)
      return
    }

    try {
      setError(null)
      const nextStatus = await desktopControlApi.getStatus()
      setStatus(nextStatus)
    } catch (err) {
      setStatus(null)
      setError(getDesktopControlLoadErrorMessage(err))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [privacyMode])

  useEffect(() => {
    setLoading(true)
    loadStatus()
  }, [loadStatus])

  const gate = useMemo(
    () => buildDesktopControlGate({ privacyMode, status, errorMessage: error }),
    [privacyMode, status, error],
  )

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadStatus()
  }, [loadStatus])

  return (
    <SafeAreaView style={styles.safeArea} edges={['bottom']}>
      <Stack.Screen options={{ title: '桌面控制' }} />
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
        }
      >
        <View style={styles.header}>
          <View style={styles.headerIcon}>
            <Ionicons name="desktop-outline" size={24} color={Colors.primary} />
          </View>
          <View style={styles.headerText}>
            <Text style={styles.eyebrow}>桌面工作站</Text>
            <Text style={styles.title}>移动端远程控制</Text>
          </View>
        </View>

        <View style={styles.statusPanel}>
          <View style={styles.statusHeader}>
            <View style={[
              styles.statusIcon,
              gate.state === 'ready'
                ? styles.statusIcon_ready
                : gate.state === 'blocked'
                  ? styles.statusIcon_blocked
                  : gate.state === 'error'
                    ? styles.statusIcon_error
                    : styles.statusIcon_not_configured,
            ]}>
              <Ionicons name={gate.icon} size={22} color={getStatusColor(gate.state)} />
            </View>
            <View style={styles.statusText}>
              <Text style={styles.statusTitle}>{loading ? '正在检查桌面控制状态' : gate.title}</Text>
              <Text style={styles.statusDescription}>
                {loading ? '正在读取后端远控安全闸。' : gate.description}
              </Text>
            </View>
          </View>

          {!loading && gate.requiredControls.length > 0 && (
            <View style={styles.controlGrid}>
              {gate.requiredControls.map((control) => (
                <View key={control} style={styles.controlPill}>
                  <Ionicons name="ellipse" size={6} color={Colors.warning} />
                  <Text style={styles.controlText}>{control}</Text>
                </View>
              ))}
            </View>
          )}
        </View>

        <View style={styles.guardPanel}>
          <Text style={styles.sectionTitle}>安全边界</Text>
          <GuardRow icon="phone-portrait-outline" text="移动端只展示远控状态，不会绕过桌面端确认。" />
          <GuardRow icon="key-outline" text="命令必须具备短期能力路由 token。" />
          <GuardRow icon="time-outline" text="后续命令需要可过期、可撤销并写入审计。" />
        </View>

        <View style={styles.actions}>
          {privacyMode === 'local' ? (
            <TouchableOpacity
              style={styles.secondaryButton}
              activeOpacity={0.75}
              onPress={() => router.push('/(tabs)/profile' as any)}
            >
              <Ionicons name="shield-half" size={18} color={Colors.primary} />
              <Text style={styles.secondaryButtonText}>查看运行模式</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={styles.secondaryButton}
              activeOpacity={0.75}
              onPress={onRefresh}
            >
              <Ionicons name="refresh-outline" size={18} color={Colors.primary} />
              <Text style={styles.secondaryButtonText}>重新检查</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

function GuardRow({ icon, text }: { icon: keyof typeof Ionicons.glyphMap; text: string }) {
  return (
    <View style={styles.guardRow}>
      <Ionicons name={icon} size={18} color={Colors.textSecondary} />
      <Text style={styles.guardText}>{text}</Text>
    </View>
  )
}

function getStatusColor(state: string) {
  if (state === 'ready') return Colors.success
  if (state === 'blocked') return Colors.error
  if (state === 'error') return Colors.error
  return Colors.warning
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.background },
  container: { flex: 1 },
  content: {
    padding: Layout.spacing.md,
    paddingBottom: Layout.spacing.xl,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.md,
    marginTop: Layout.spacing.sm,
    marginBottom: Layout.spacing.md,
  },
  headerIcon: {
    width: 48,
    height: 48,
    borderRadius: Layout.borderRadius.md,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerText: { flex: 1 },
  eyebrow: {
    color: Colors.primary,
    fontSize: Layout.fontSize.xs,
    fontWeight: '600',
    marginBottom: 2,
  },
  title: {
    color: Colors.text,
    fontSize: Layout.fontSize.xxl,
    fontWeight: '700',
  },
  statusPanel: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.lg,
    padding: Layout.spacing.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  statusHeader: {
    flexDirection: 'row',
    gap: Layout.spacing.md,
  },
  statusIcon: {
    width: 44,
    height: 44,
    borderRadius: Layout.borderRadius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusIcon_ready: { backgroundColor: Colors.success + '15' },
  statusIcon_blocked: { backgroundColor: Colors.error + '12' },
  statusIcon_not_configured: { backgroundColor: Colors.warning + '14' },
  statusIcon_error: { backgroundColor: Colors.error + '12' },
  statusText: { flex: 1 },
  statusTitle: {
    color: Colors.text,
    fontSize: Layout.fontSize.lg,
    fontWeight: '700',
  },
  statusDescription: {
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    lineHeight: 20,
    marginTop: Layout.spacing.xs,
  },
  controlGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Layout.spacing.sm,
    marginTop: Layout.spacing.md,
  },
  controlPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.xs,
    backgroundColor: Colors.background,
    borderRadius: Layout.borderRadius.full,
    minHeight: Layout.touchTarget.min,
    paddingHorizontal: Layout.spacing.md,
  },
  controlText: {
    color: Colors.text,
    fontSize: Layout.fontSize.sm,
  },
  guardPanel: {
    marginTop: Layout.spacing.md,
    backgroundColor: Colors.background,
  },
  sectionTitle: {
    color: Colors.text,
    fontSize: Layout.fontSize.md,
    fontWeight: '700',
    marginBottom: Layout.spacing.sm,
  },
  guardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    minHeight: Layout.touchTarget.min,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  guardText: {
    flex: 1,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.sm,
    lineHeight: 20,
  },
  actions: {
    marginTop: Layout.spacing.lg,
  },
  secondaryButton: {
    minHeight: Layout.touchTarget.min,
    borderRadius: Layout.borderRadius.full,
    borderWidth: 1,
    borderColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: Layout.spacing.sm,
    paddingHorizontal: Layout.spacing.lg,
  },
  secondaryButtonText: {
    color: Colors.primary,
    fontSize: Layout.fontSize.md,
    fontWeight: '700',
  },
})
