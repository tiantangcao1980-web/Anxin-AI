// -*- coding: utf-8 -*-
import { useEffect, useState, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { PairingRequestCard } from '@/components/v3/capabilities-mobile/PairingRequestCard'
import {
  pairingApi,
  type PairingRequest,
} from '@/lib/api/imPairing'

/**
 * 配对审批列表页 — 24h 倒计时 + swipe-to-action (P17-D)
 *
 * 移动端关键差异:
 *   - Web 用按钮 + 弹窗;移动端 swipe 左滑批准、右滑拒绝
 *   - 24h 倒计时实时更新,临近 2h 高亮
 *   - 操作完毕后立即从列表移除 (Optimistic UI)
 */

export default function PairingAuthorizationsScreen() {
  const [requests, setRequests] = useState<PairingRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await pairingApi.listPending()
      setRequests(data)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onRefresh = () => {
    setRefreshing(true)
    load()
  }

  const handleApprove = async (req: PairingRequest) => {
    setRequests((prev) => prev.filter((r) => r.id !== req.id))
    try {
      await pairingApi.approve(req.id)
    } catch (e) {
      // 回滚
      setRequests((prev) => [req, ...prev])
      Alert.alert('批准失败', e instanceof Error ? e.message : '未知错误')
    }
  }

  const handleReject = async (req: PairingRequest) => {
    setRequests((prev) => prev.filter((r) => r.id !== req.id))
    try {
      await pairingApi.reject(req.id, '管理员拒绝')
    } catch (e) {
      setRequests((prev) => [req, ...prev])
      Alert.alert('拒绝失败', e instanceof Error ? e.message : '未知错误')
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      {loading && requests.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          data={requests}
          keyExtractor={(r) => r.id}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
          }
          ListHeaderComponent={
            <View style={styles.header}>
              <Text style={styles.headerText}>
                {requests.length > 0
                  ? `${requests.length} 个用户等待绑定智能体`
                  : '当前没有待审批的配对请求'}
              </Text>
              <Text style={styles.hint}>
                左滑批准 · 右滑拒绝 · 24h 内必须处理
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <PairingRequestCard
              request={item}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="checkmark-done-circle" size={48} color={Colors.success} />
              <Text style={styles.emptyText}>没有待处理的配对请求</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    backgroundColor: Colors.background,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  headerText: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  hint: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 4 },
  empty: { alignItems: 'center', paddingVertical: 80, gap: 12 },
  emptyText: { color: Colors.textSecondary, fontSize: Layout.fontSize.sm },
})
