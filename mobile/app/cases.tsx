import { useCallback, useEffect, useState } from 'react'
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { api } from '@/services/api'
import { useStackHeaderOptions, useTheme } from '@/lib/theme'
import { DomainStripe } from '@/components/DomainBadge'

/**
 * 我的案件 —— 接入真实 `/cases/` 后端 API。
 *
 * 支持：状态筛选、下拉刷新、无限滚动分页、loading/error/empty 三态。
 */

interface CaseItem {
  id: string
  case_number: string | null
  title: string
  case_type: string
  status: string
  priority: string
  description?: string | null
  assignee_id?: string | null
  risk_score?: number | null
  updated_at?: string
  created_at?: string
}

interface CaseListResponse {
  items: CaseItem[]
  total: number
  page: number
  page_size: number
}

const STATUS_LABEL: Record<string, string> = {
  pending: '待处理',
  in_progress: '进行中',
  under_review: '审核中',
  completed: '已完成',
  archived: '已归档',
  closed: '已结案',
  cancelled: '已取消',
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#FF9800',
  in_progress: '#2196F3',
  under_review: '#3B82F6',
  completed: '#10B981',
  archived: '#9E9E9E',
  closed: '#9E9E9E',
  cancelled: '#EF4444',
}

const FILTER_TABS = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待处理' },
  { key: 'in_progress', label: '进行中' },
  { key: 'closed', label: '已结案' },
] as const

const PAGE_SIZE = 20

export default function CasesScreen() {
  const [activeTab, setActiveTab] = useState<string>('all')
  const [cases, setCases] = useState<CaseItem[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const headerOptions = useStackHeaderOptions({ title: '我的案件' })
  const theme = useTheme()

  const loadPage = useCallback(
    async (targetPage: number, replace: boolean) => {
      try {
        setError(null)
        if (replace && targetPage === 1 && !refreshing) setLoading(true)
        const qs = new URLSearchParams({
          page: String(targetPage),
          page_size: String(PAGE_SIZE),
        })
        if (activeTab !== 'all') qs.set('status', activeTab)
        const result = await api.get<CaseListResponse>(`/cases/?${qs.toString()}`)
        setTotal(result.total)
        setCases((prev) => (replace ? result.items : [...prev, ...result.items]))
        setPage(targetPage)
      } catch (err: any) {
        setError(err?.message || '加载案件列表失败')
        if (replace) setCases([])
      } finally {
        setLoading(false)
        setLoadingMore(false)
        setRefreshing(false)
      }
    },
    [activeTab, refreshing],
  )

  useEffect(() => {
    loadPage(1, true)
  }, [activeTab])  // eslint-disable-line react-hooks/exhaustive-deps

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadPage(1, true)
  }, [loadPage])

  const onEndReached = useCallback(() => {
    if (loadingMore || cases.length >= total) return
    setLoadingMore(true)
    loadPage(page + 1, false)
  }, [cases.length, total, page, loadingMore, loadPage])

  const renderCase = ({ item }: { item: CaseItem }) => {
    const statusLabel = STATUS_LABEL[item.status] ?? item.status
    const color = STATUS_COLORS[item.status] ?? '#9E9E9E'
    return (
      <TouchableOpacity
        style={styles.card}
        activeOpacity={0.7}
        onPress={() => router.push(`/cases/${item.id}` as any)}
      >
        <View style={styles.cardMain}>
          <Text style={styles.caseName} numberOfLines={2}>
            {item.title}
          </Text>
          {item.case_number && (
            <View style={styles.caseNumberRow}>
              <Ionicons name="document-outline" size={13} color="#999" />
              <Text style={styles.caseNumber}>{item.case_number}</Text>
            </View>
          )}
          <View style={styles.cardFooter}>
            <View style={[styles.statusBadge, { backgroundColor: color + '20' }]}>
              <View style={[styles.statusDot, { backgroundColor: color }]} />
              <Text style={[styles.statusText, { color }]}>{statusLabel}</Text>
            </View>
            {item.updated_at && (
              <Text style={styles.dateText}>
                更新于 {new Date(item.updated_at).toLocaleDateString('zh-CN')}
              </Text>
            )}
          </View>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#CCC" />
      </TouchableOpacity>
    )
  }

  const renderEmpty = () =>
    error ? (
      <View style={styles.emptyContainer}>
        <Ionicons name="cloud-offline-outline" size={64} color="#DC2626" />
        <Text style={[styles.emptyText, { color: '#DC2626' }]}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={() => loadPage(1, true)}>
          <Text style={styles.retryBtnText}>点击重试</Text>
        </TouchableOpacity>
      </View>
    ) : (
      <View style={styles.emptyContainer}>
        <Ionicons name="briefcase-outline" size={64} color="#CCC" />
        <Text style={styles.emptyText}>暂无案件</Text>
        <Text style={styles.emptySubText}>您的案件将显示在这里</Text>
      </View>
    )

  const renderFooter = () =>
    loadingMore ? (
      <View style={styles.footer}>
        <ActivityIndicator color="#D4A574" />
      </View>
    ) : null

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: theme.surface }]}
      edges={['bottom']}
    >
      <Stack.Screen options={headerOptions} />
      {/* V3 法务域视觉锚点 */}
      <DomainStripe domain="legal" />

      <View style={styles.tabContainer}>
        {FILTER_TABS.map((t) => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tab, activeTab === t.key && styles.tabActive]}
            onPress={() => setActiveTab(t.key)}
          >
            <Text style={[styles.tabText, activeTab === t.key && styles.tabTextActive]}>
              {t.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading && cases.length === 0 && !error ? (
        <View style={styles.centered}>
          <ActivityIndicator color="#D4A574" size="large" />
        </View>
      ) : (
        <FlatList
          data={cases}
          keyExtractor={(item) => item.id}
          renderItem={renderCase}
          ListEmptyComponent={renderEmpty}
          ListFooterComponent={renderFooter}
          contentContainerStyle={
            cases.length === 0 ? styles.emptyList : styles.listContent
          }
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor="#D4A574"
            />
          }
          onEndReached={onEndReached}
          onEndReachedThreshold={0.3}
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginTop: 12,
    marginBottom: 8,
  },
  tab: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: '#FFF',
    marginRight: 8,
  },
  tabActive: { backgroundColor: '#D4A574' },
  tabText: { fontSize: 13, color: '#666' },
  tabTextActive: { color: '#FFF', fontWeight: '600' },
  listContent: { paddingHorizontal: 16, paddingBottom: 20 },
  card: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardMain: { flex: 1 },
  caseName: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 6 },
  caseNumberRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  caseNumber: { fontSize: 12, color: '#999', marginLeft: 4 },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  statusDot: { width: 6, height: 6, borderRadius: 3, marginRight: 4 },
  statusText: { fontSize: 12, fontWeight: '500' },
  dateText: { fontSize: 11, color: '#BBB' },
  footer: { paddingVertical: 16 },
  emptyList: { flex: 1 },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 80,
  },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
  emptySubText: { fontSize: 13, color: '#CCC', marginTop: 4 },
  retryBtn: {
    marginTop: 16,
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#D4A574',
    borderRadius: 8,
  },
  retryBtnText: { color: '#FFF', fontSize: 14, fontWeight: '500' },
})
