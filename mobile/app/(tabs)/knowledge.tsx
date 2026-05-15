import { useEffect, useState, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'
import { DomainStripe } from '@/components/DomainBadge'

/**
 * 法律智库 Tab —— 法规 / 模板 / 判例三视图合一。
 *
 * 首版提供：
 * - 顶部全文检索入口（后端支持 /knowledge/search）
 * - 三大类别快速入口卡片
 * - 最近浏览法规列表
 *
 * 知识图谱（three.js）仍在 Web 端，移动端暂不内嵌，改为跳转 WebView 或占位引导。
 */

interface KnowledgeItem {
  id: string
  title: string
  category: string
  issued_at?: string
  source?: string
}

interface SearchSummary {
  keyword: string
  count: number
  searched_at: string
}

const CATEGORIES = [
  { key: 'regulation', label: '法规', icon: 'book-outline', color: '#3B82F6' },
  { key: 'case', label: '判例', icon: 'hammer-outline', color: '#EF4444' },
  { key: 'template', label: '文书模板', icon: 'document-outline', color: '#10B981' },
] as const

export default function KnowledgeScreen() {
  const [query, setQuery] = useState('')
  const [recent, setRecent] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [searching, setSearching] = useState(false)
  const [searchSummary, setSearchSummary] = useState<SearchSummary | null>(null)

  const loadRecent = useCallback(async () => {
    try {
      setError(null)
      const items = await api.get<KnowledgeItem[]>('/knowledge/recent?limit=10')
      setRecent(items ?? [])
    } catch (err: any) {
      setError(err?.message || '加载法规列表失败')
      setRecent([])
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadRecent()
  }, [loadRecent])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadRecent()
  }, [loadRecent])

  const onSearchSubmit = useCallback(async () => {
    const keyword = query.trim()
    if (!keyword || searching) return

    try {
      setSearching(true)
      setError(null)
      const results = await api.post<Array<KnowledgeItem & { content?: string; match_type?: string }>>('/knowledge/search', {
        query: keyword,
        top_k: 10,
        hybrid: true,
      })
      setRecent(
        (results ?? []).map((item) => ({
          id: item.id,
          title: item.title || item.content?.slice(0, 36) || keyword,
          category: item.category || item.match_type || '知识检索',
          source: item.source,
        })),
      )
      setSearchSummary({
        keyword,
        count: results?.length ?? 0,
        searched_at: new Date().toISOString(),
      })
    } catch (err: any) {
      setError(err?.message || '知识检索失败，请稍后重试')
    } finally {
      setSearching(false)
    }
  }, [query, searching])

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      {/* V3 法务域视觉锚点 — 4pt 高暖橄榄绿彩条 */}
      <DomainStripe domain="legal" />
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
        }
      >
        <Text style={styles.heading}>法律智库</Text>
        <Text style={styles.subheading}>法规 · 判例 · 文书模板 · AI 助读</Text>

        {/* 搜索 */}
        <View style={styles.searchBox}>
          <Ionicons name="search" size={18} color={Colors.textSecondary} />
          <TextInput
            style={styles.searchInput}
            placeholder="输入关键词，搜索法规、判例、模板"
            placeholderTextColor={Colors.textMuted}
            value={query}
            onChangeText={setQuery}
            returnKeyType="search"
            onSubmitEditing={onSearchSubmit}
            editable={!searching}
          />
          {searching && <ActivityIndicator size="small" color={Colors.primary} />}
        </View>

        {searchSummary && (
          <View style={styles.resultCard}>
            <View style={styles.resultHeader}>
              <View style={styles.resultIcon}>
                <Ionicons
                  name={searchSummary.count > 0 ? 'checkmark-circle' : 'information-circle-outline'}
                  size={20}
                  color={searchSummary.count > 0 ? Colors.success : Colors.info}
                />
              </View>
              <View style={styles.resultHeaderText}>
                <Text style={styles.resultTitle}>
                  {searchSummary.count > 0 ? '已生成检索结果' : '未找到匹配内容'}
                </Text>
                <Text style={styles.resultMeta}>
                  {searchSummary.keyword} · {new Date(searchSummary.searched_at).toLocaleString('zh-CN')}
                </Text>
              </View>
            </View>
            <Text style={styles.resultBody}>
              {searchSummary.count > 0
                ? `找到 ${searchSummary.count} 条可读内容。请优先查看来源、发布日期和适用范围，重大事项建议结合合同或案件材料继续咨询。`
                : '当前账号可访问的知识库中暂无匹配内容。可以换用更短关键词，或确认组织知识库是否已上传相关法规、模板和案例。'}
            </Text>
          </View>
        )}

        {/* 三大类别 */}
        <View style={styles.categoryRow}>
          {CATEGORIES.map((c) => (
            <TouchableOpacity key={c.key} style={styles.categoryCard} activeOpacity={0.8}>
              <View style={[styles.categoryIcon, { backgroundColor: c.color + '15' }]}>
                <Ionicons name={c.icon as any} size={22} color={c.color} />
              </View>
              <Text style={styles.categoryLabel}>{c.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* 最近浏览 */}
        <Text style={styles.sectionTitle}>最近更新</Text>
        {loading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator color={Colors.primary} />
          </View>
        ) : error ? (
          <View style={styles.errorBanner}>
            <Ionicons name="warning-outline" size={16} color="#DC2626" />
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity onPress={loadRecent}>
              <Text style={styles.retryText}>重试</Text>
            </TouchableOpacity>
          </View>
        ) : recent.length === 0 ? (
          <View style={styles.emptyBox}>
            <Ionicons name="book-outline" size={28} color={Colors.textMuted} />
            <Text style={styles.emptyText}>暂无可读内容</Text>
          </View>
        ) : (
          recent.map((item) => (
            <TouchableOpacity key={item.id} style={styles.listCard} activeOpacity={0.7}>
              <View style={styles.listCardIcon}>
                <Ionicons name="document-text-outline" size={18} color={Colors.primary} />
              </View>
              <View style={styles.listCardBody}>
                <Text style={styles.listCardTitle} numberOfLines={2}>
                  {item.title}
                </Text>
                <Text style={styles.listCardMeta}>
                  {item.category}
                  {item.issued_at ? ` · ${new Date(item.issued_at).toLocaleDateString('zh-CN')}` : ''}
                  {item.source ? ` · ${item.source}` : ''}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.background },
  container: { flex: 1 },
  content: { padding: Layout.spacing.lg, paddingBottom: Layout.spacing.xl * 2 },
  heading: { fontSize: 28, fontWeight: '700', color: Colors.text, marginBottom: 4 },
  subheading: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    marginBottom: Layout.spacing.lg,
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    marginBottom: Layout.spacing.lg,
  },
  searchInput: { flex: 1, fontSize: Layout.fontSize.md, color: Colors.text, padding: 0 },
  resultCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.lg,
    gap: Layout.spacing.sm,
  },
  resultHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
  },
  resultIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: Colors.info + '15',
    alignItems: 'center',
    justifyContent: 'center',
  },
  resultHeaderText: { flex: 1 },
  resultTitle: { fontSize: Layout.fontSize.md, fontWeight: '700', color: Colors.text },
  resultMeta: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  resultBody: {
    fontSize: Layout.fontSize.sm,
    lineHeight: 20,
    color: Colors.text,
  },
  categoryRow: {
    flexDirection: 'row',
    gap: Layout.spacing.md,
    marginBottom: Layout.spacing.lg,
  },
  categoryCard: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.lg,
    padding: Layout.spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  categoryIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Layout.spacing.sm,
  },
  categoryLabel: { fontSize: Layout.fontSize.sm, fontWeight: '600', color: Colors.text },
  sectionTitle: {
    fontSize: Layout.fontSize.sm,
    fontWeight: '600',
    color: Colors.textSecondary,
    marginBottom: Layout.spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  loadingBox: { alignItems: 'center', padding: Layout.spacing.xl },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    backgroundColor: '#FEE2E2',
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
  },
  errorText: { flex: 1, fontSize: Layout.fontSize.sm, color: '#DC2626' },
  retryText: { fontSize: Layout.fontSize.sm, color: '#DC2626', fontWeight: '600' },
  emptyBox: {
    alignItems: 'center',
    padding: Layout.spacing.xl,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    gap: Layout.spacing.sm,
  },
  emptyText: { fontSize: Layout.fontSize.sm, color: Colors.textMuted },
  listCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  listCardIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
  },
  listCardBody: { flex: 1 },
  listCardTitle: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  listCardMeta: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
})
