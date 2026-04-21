import { useCallback, useEffect, useState } from 'react'
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { api } from '@/services/api'
import { useStackHeaderOptions, useTheme } from '@/lib/theme'

/**
 * 找律师 —— 接入 `/lawyer/lawyers` 真实 API（支持按领域智能匹配）。
 *
 * 支持：领域筛选、下拉刷新、分页、loading/error/empty 三态。
 */

interface LawyerProfile {
  id: string
  real_name: string
  law_firm?: string | null
  years_of_practice?: number | null
  city?: string | null
  specializations: string[]
  bio?: string | null
  avatar_url?: string | null
  rating?: number | null
  total_cases?: number | null
  hourly_rate_min?: number | null
  hourly_rate_max?: number | null
}

interface LawyerListResponse {
  items: LawyerProfile[]
  total: number
}

const DOMAINS = [
  { key: '', label: '全部' },
  { key: '合同纠纷', label: '合同纠纷' },
  { key: '劳动争议', label: '劳动争议' },
  { key: '知识产权', label: '知识产权' },
  { key: '公司法务', label: '公司法务' },
  { key: '婚姻家事', label: '婚姻家事' },
  { key: '刑事辩护', label: '刑事辩护' },
] as const

const PAGE_SIZE = 20

export default function FindLawyerScreen() {
  const [activeDomain, setActiveDomain] = useState<string>('')
  const [city, setCity] = useState('')
  const [lawyers, setLawyers] = useState<LawyerProfile[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const headerOptions = useStackHeaderOptions({ title: '找律师' })
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
        if (activeDomain) qs.set('domain', activeDomain)
        if (city.trim()) qs.set('city', city.trim())
        const result = await api.get<LawyerListResponse>(`/lawyer/lawyers?${qs.toString()}`)
        setTotal(result.total)
        setLawyers((prev) => (replace ? result.items : [...prev, ...result.items]))
        setPage(targetPage)
      } catch (err: any) {
        setError(err?.message || '加载律师列表失败')
        if (replace) setLawyers([])
      } finally {
        setLoading(false)
        setLoadingMore(false)
        setRefreshing(false)
      }
    },
    [activeDomain, city, refreshing],
  )

  useEffect(() => {
    loadPage(1, true)
  }, [activeDomain])  // eslint-disable-line react-hooks/exhaustive-deps

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadPage(1, true)
  }, [loadPage])

  const onEndReached = useCallback(() => {
    if (loadingMore || lawyers.length >= total) return
    setLoadingMore(true)
    loadPage(page + 1, false)
  }, [lawyers.length, total, page, loadingMore, loadPage])

  const onSearch = useCallback(() => {
    loadPage(1, true)
  }, [loadPage])

  const renderLawyer = ({ item }: { item: LawyerProfile }) => (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.7}
      onPress={() => router.push(`/lawyer/${item.id}` as any)}
    >
      <View style={styles.avatarBox}>
        <View style={styles.avatarPlaceholder}>
          <Text style={styles.avatarLetter}>
            {item.real_name?.charAt(0) || '律'}
          </Text>
        </View>
      </View>
      <View style={styles.cardMain}>
        <View style={styles.nameRow}>
          <Text style={styles.name}>{item.real_name}</Text>
          {item.rating !== null && item.rating !== undefined && item.rating > 0 && (
            <View style={styles.ratingBox}>
              <Ionicons name="star" size={12} color="#F59E0B" />
              <Text style={styles.rating}>{item.rating.toFixed(1)}</Text>
            </View>
          )}
        </View>
        {item.law_firm && <Text style={styles.firm}>{item.law_firm}</Text>}
        <View style={styles.tagsRow}>
          {item.specializations.slice(0, 3).map((s) => (
            <View key={s} style={styles.tag}>
              <Text style={styles.tagText}>{s}</Text>
            </View>
          ))}
        </View>
        <View style={styles.metaRow}>
          {item.years_of_practice && (
            <Text style={styles.meta}>执业 {item.years_of_practice} 年</Text>
          )}
          {item.total_cases !== null && item.total_cases !== undefined && (
            <Text style={styles.meta}> · 办理 {item.total_cases} 案</Text>
          )}
          {item.city && <Text style={styles.meta}> · {item.city}</Text>}
        </View>
      </View>
    </TouchableOpacity>
  )

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
        <Ionicons name="people-outline" size={64} color="#CCC" />
        <Text style={styles.emptyText}>暂无匹配律师</Text>
        <Text style={styles.emptySubText}>调整筛选条件再试试</Text>
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
          <Ionicons name="location-outline" size={16} color="#999" />
          <TextInput
            style={styles.searchInput}
            placeholder="输入城市（选填）"
            placeholderTextColor="#BBB"
            value={city}
            onChangeText={setCity}
            returnKeyType="search"
            onSubmitEditing={onSearch}
          />
          <TouchableOpacity style={styles.searchBtn} onPress={onSearch}>
            <Text style={styles.searchBtnText}>筛选</Text>
          </TouchableOpacity>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabScroll}>
          <View style={styles.tabRow}>
            {DOMAINS.map((d) => (
              <TouchableOpacity
                key={d.key || 'all'}
                style={[styles.tab, activeDomain === d.key && styles.tabActive]}
                onPress={() => setActiveDomain(d.key)}
              >
                <Text
                  style={[
                    styles.tabText,
                    activeDomain === d.key && styles.tabTextActive,
                  ]}
                >
                  {d.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>

        {loading && lawyers.length === 0 && !error ? (
          <View style={styles.centered}>
            <ActivityIndicator color="#D4A574" size="large" />
          </View>
        ) : (
          <FlatList
            data={lawyers}
            keyExtractor={(item) => item.id}
            renderItem={renderLawyer}
            ListEmptyComponent={renderEmpty}
            ListFooterComponent={
              loadingMore ? (
                <View style={styles.footerLoading}>
                  <ActivityIndicator color="#D4A574" />
                </View>
              ) : null
            }
            contentContainerStyle={
              lawyers.length === 0 ? styles.emptyList : styles.listContent
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
  searchBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#D4A574',
    borderRadius: 8,
  },
  searchBtnText: { color: '#FFF', fontSize: 13, fontWeight: '500' },
  tabScroll: { marginTop: 12, maxHeight: 40 },
  tabRow: { flexDirection: 'row', paddingHorizontal: 16, gap: 8 },
  tab: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: '#FFF',
  },
  tabActive: { backgroundColor: '#D4A574' },
  tabText: { fontSize: 13, color: '#666' },
  tabTextActive: { color: '#FFF', fontWeight: '600' },
  listContent: { paddingHorizontal: 16, paddingVertical: 12 },
  card: {
    flexDirection: 'row',
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    gap: 12,
  },
  avatarBox: {},
  avatarPlaceholder: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: '#F5F0E6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarLetter: { fontSize: 20, fontWeight: '600', color: '#D4A574' },
  cardMain: { flex: 1 },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  name: { fontSize: 16, fontWeight: '600', color: '#333' },
  ratingBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  rating: { fontSize: 11, color: '#D97706', fontWeight: '600' },
  firm: { fontSize: 12, color: '#666', marginTop: 2 },
  tagsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6 },
  tag: {
    backgroundColor: '#F5F5F5',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  tagText: { fontSize: 11, color: '#666' },
  metaRow: { flexDirection: 'row', alignItems: 'center', marginTop: 6 },
  meta: { fontSize: 11, color: '#999' },
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
