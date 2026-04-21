import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { api } from '@/services/api'
import { useStackHeaderOptions, useTheme } from '@/lib/theme'

/**
 * 合同管理 —— 接入真实 `/contracts/` 后端 API。
 *
 * 支持：状态筛选、搜索、下拉刷新、无限滚动分页、loading/error/empty 三态。
 */

interface ContractItem {
  id: string
  title: string
  contract_number?: string | null
  contract_type: string
  status: string
  amount?: number | null
  risk_level?: string | null
  risk_score?: number | null
  created_at?: string
  updated_at?: string
}

interface ContractListResponse {
  items: ContractItem[]
  total: number
  page: number
  page_size: number
}

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  pending_review: '待审核',
  under_review: '审核中',
  approved: '已批准',
  signed: '已签署',
  active: '生效中',
  expired: '已过期',
  archived: '已归档',
}

const STATUS_COLORS: Record<string, string> = {
  draft: '#9E9E9E',
  pending_review: '#E8A317',
  under_review: '#3B82F6',
  approved: '#10B981',
  signed: '#4CAF50',
  active: '#10B981',
  expired: '#EF4444',
  archived: '#9E9E9E',
}

const FILTER_TABS = [
  { key: 'all', label: '全部' },
  { key: 'under_review', label: '审核中' },
  { key: 'signed', label: '已签署' },
  { key: 'archived', label: '已归档' },
] as const

const PAGE_SIZE = 20

export default function ContractsScreen() {
  const [searchText, setSearchText] = useState('')
  const [activeTab, setActiveTab] = useState<string>('all')
  const [contracts, setContracts] = useState<ContractItem[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const headerOptions = useStackHeaderOptions({ title: '合同管理' })
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
        const result = await api.get<ContractListResponse>(`/contracts/?${qs.toString()}`)
        setTotal(result.total)
        setContracts((prev) => (replace ? result.items : [...prev, ...result.items]))
        setPage(targetPage)
      } catch (err: any) {
        setError(err?.message || '加载合同列表失败')
        if (replace) setContracts([])
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
    if (loadingMore || contracts.length >= total) return
    setLoadingMore(true)
    loadPage(page + 1, false)
  }, [contracts.length, total, page, loadingMore, loadPage])

  // 搜索走本地过滤（后端支持 q 参数时可改为服务端搜索）
  const filteredContracts = useMemo(() => {
    const kw = searchText.trim().toLowerCase()
    if (!kw) return contracts
    return contracts.filter((c) =>
      [c.title, c.contract_number, c.contract_type]
        .filter(Boolean)
        .some((f) => f!.toLowerCase().includes(kw)),
    )
  }, [contracts, searchText])

  const renderContract = ({ item }: { item: ContractItem }) => {
    const statusLabel = STATUS_LABEL[item.status] ?? item.status
    const color = STATUS_COLORS[item.status] ?? '#9E9E9E'
    return (
      <TouchableOpacity style={styles.card} activeOpacity={0.7}>
        <View style={styles.cardMain}>
          <Text style={styles.title} numberOfLines={2}>
            {item.title}
          </Text>
          <View style={styles.row}>
            <Ionicons name="pricetag-outline" size={13} color="#999" />
            <Text style={styles.meta}>
              {item.contract_type}
              {item.amount ? ` · ¥${item.amount.toLocaleString()}` : ''}
            </Text>
          </View>
          <View style={styles.footer}>
            <View style={[styles.statusBadge, { backgroundColor: color + '20' }]}>
              <View style={[styles.statusDot, { backgroundColor: color }]} />
              <Text style={[styles.statusText, { color }]}>{statusLabel}</Text>
            </View>
            {item.created_at && (
              <Text style={styles.dateText}>
                {new Date(item.created_at).toLocaleDateString('zh-CN')}
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
        <Ionicons name="document-outline" size={64} color="#CCC" />
        <Text style={styles.emptyText}>暂无合同</Text>
        <Text style={styles.emptySubText}>
          {searchText ? '换个关键词再试试' : '您的合同将显示在这里'}
        </Text>
      </View>
    )

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: theme.surface }]}
      edges={['bottom']}
    >
      <Stack.Screen options={headerOptions} />

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={16} color="#999" />
          <TextInput
            style={styles.searchInput}
            placeholder="搜索合同标题/编号"
            placeholderTextColor="#BBB"
            value={searchText}
            onChangeText={setSearchText}
            returnKeyType="search"
          />
          {searchText.length > 0 && (
            <TouchableOpacity onPress={() => setSearchText('')}>
              <Ionicons name="close-circle" size={16} color="#CCC" />
            </TouchableOpacity>
          )}
        </View>

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

        {loading && contracts.length === 0 && !error ? (
          <View style={styles.centered}>
            <ActivityIndicator color="#D4A574" size="large" />
          </View>
        ) : (
          <FlatList
            data={filteredContracts}
            keyExtractor={(item) => item.id}
            renderItem={renderContract}
            ListEmptyComponent={renderEmpty}
            ListFooterComponent={
              loadingMore ? (
                <View style={styles.footerLoading}>
                  <ActivityIndicator color="#D4A574" />
                </View>
              ) : null
            }
            contentContainerStyle={
              filteredContracts.length === 0 ? styles.emptyList : styles.listContent
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
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  flex: { flex: 1 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    gap: 8,
  },
  searchInput: { flex: 1, fontSize: 14, color: '#333', padding: 0 },
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
  title: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 6 },
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  meta: { fontSize: 12, color: '#999', marginLeft: 4 },
  footer: {
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
  footerLoading: { paddingVertical: 16 },
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
