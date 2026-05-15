import { useCallback, useEffect, useState } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'
import { DomainStripe } from '@/components/DomainBadge'

/**
 * 智能调查 Tab —— 企业 / 主体 / 关联方全维度尽职调查。
 *
 * 首版包含：搜索入口、最近调查、热点推荐。
 * 深度报告、关系图谱、风险推演依赖 SSE 流式后端（已在 Web 端实现），
 * 后续接入 `dueDiligenceApi.streamInvestigate`。
 */

interface RecentItem {
  id: string
  company_name: string
  started_at: string
  status: 'pending' | 'running' | 'completed' | 'failed'
}

interface HotTopic {
  id: string
  name: string
  reason: string
}

interface InvestigationResult {
  company_name: string
  started_at: string
  status: RecentItem['status']
  risk_level?: string
  risk_score?: number
  summary?: string
  report_id?: string
}

export default function InvestigationScreen() {
  const [query, setQuery] = useState('')
  const [recent, setRecent] = useState<RecentItem[]>([])
  const [topics, setTopics] = useState<HotTopic[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [latestResult, setLatestResult] = useState<InvestigationResult | null>(null)

  const loadData = useCallback(async () => {
    try {
      setError(null)
      const results = await Promise.allSettled([
        api.get<RecentItem[]>('/due-diligence/recent'),
        api.get<HotTopic[]>('/due-diligence/hot-topics'),
      ])
      setRecent(results[0].status === 'fulfilled' ? results[0].value : [])
      setTopics(results[1].status === 'fulfilled' ? results[1].value : [])
    } catch (err: any) {
      setError(err?.message || '加载调查入口失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadData()
  }, [loadData])

  const onSubmit = useCallback(async () => {
    const companyName = query.trim()
    if (!companyName || submitting) return

    try {
      setSubmitting(true)
      setError(null)
      const result = await api.post<{
        company_name: string
        timestamp?: string
        status?: RecentItem['status']
        risk_level?: string
        risk_score?: number
        summary?: string
        report_id?: string
      }>('/due-diligence/company', {
        company_name: companyName,
        investigation_type: 'comprehensive',
      })
      const startedAt = result.timestamp ?? new Date().toISOString()
      const completedResult = {
        company_name: result.company_name || companyName,
        started_at: startedAt,
        status: result.status ?? 'completed',
        risk_level: result.risk_level,
        risk_score: result.risk_score,
        summary: result.summary,
        report_id: result.report_id,
      }
      setRecent((items) => [
        {
          id: `${companyName}-${startedAt}`,
          company_name: completedResult.company_name,
          started_at: startedAt,
          status: completedResult.status,
        },
        ...items.filter((item) => item.company_name !== companyName),
      ])
      setLatestResult(completedResult)
    } catch (err: any) {
      setError(err?.message || '启动调查失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }, [query, submitting])

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      {/* V3 调研获客域视觉锚点 — 4pt 高青色彩条 */}
      <DomainStripe domain="growth" />
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
        }
      >
        <Text style={styles.heading}>智能调查</Text>
        <Text style={styles.subheading}>输入企业名称，AI 自动爬取生成全维度尽调报告</Text>

        <View style={styles.searchBox}>
          <Ionicons name="search" size={18} color={Colors.textSecondary} />
          <TextInput
            style={styles.searchInput}
            placeholder="输入企业名称、统一社会信用代码..."
            placeholderTextColor={Colors.textMuted}
            value={query}
            onChangeText={setQuery}
            returnKeyType="search"
            onSubmitEditing={onSubmit}
          />
          {query.length > 0 && (
            <TouchableOpacity onPress={() => setQuery('')}>
              <Ionicons name="close-circle" size={18} color={Colors.textMuted} />
            </TouchableOpacity>
          )}
        </View>

          <TouchableOpacity
          style={[styles.primaryButton, (!query.trim() || submitting) && styles.primaryButtonDisabled]}
          disabled={!query.trim() || submitting}
          onPress={onSubmit}
        >
          {submitting ? (
            <ActivityIndicator size="small" color={Colors.white} />
          ) : (
            <Ionicons name="flash" size={16} color={Colors.white} />
          )}
          <Text style={styles.primaryButtonText}>{submitting ? '调查中...' : '开始调查'}</Text>
        </TouchableOpacity>

        {latestResult && (
          <View style={styles.resultCard}>
            <View style={styles.resultHeader}>
              <View style={styles.resultIcon}>
                <Ionicons name="checkmark-circle" size={20} color={Colors.success} />
              </View>
              <View style={styles.resultHeaderText}>
                <Text style={styles.resultTitle}>{latestResult.company_name}</Text>
                <Text style={styles.resultMeta}>
                  {new Date(latestResult.started_at).toLocaleString('zh-CN')} · {statusLabel(latestResult.status)}
                </Text>
              </View>
            </View>
            <Text style={styles.resultBody}>
              {latestResult.summary ||
                '调查结果已生成并加入最近调查。请先核对企业主体、关联方和风险项；重大事项建议转交专业律师复核。'}
            </Text>
            <View style={styles.resultChips}>
              <Text style={styles.resultChip}>
                风险等级：{latestResult.risk_level || '待复核'}
              </Text>
              <Text style={styles.resultChip}>
                报告编号：{latestResult.report_id || '本次会话'}
              </Text>
            </View>
          </View>
        )}

        {loading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator color={Colors.primary} />
          </View>
        ) : error ? (
          <View style={styles.errorBanner}>
            <Ionicons name="warning-outline" size={16} color="#DC2626" />
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity onPress={loadData}>
              <Text style={styles.retryText}>重试</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            {/* 最近调查 */}
            <Text style={styles.sectionTitle}>最近调查</Text>
            {recent.length === 0 ? (
              <View style={styles.emptyBox}>
                <Ionicons name="document-text-outline" size={28} color={Colors.textMuted} />
                <Text style={styles.emptyText}>暂无调查记录</Text>
              </View>
            ) : (
              recent.map((item) => (
                <View key={item.id} style={styles.listCard}>
                  <View style={styles.listCardIcon}>
                    <Ionicons name="business-outline" size={18} color={Colors.primary} />
                  </View>
                  <View style={styles.listCardBody}>
                    <Text style={styles.listCardTitle}>{item.company_name}</Text>
                    <Text style={styles.listCardMeta}>
                      {new Date(item.started_at).toLocaleDateString('zh-CN')} · {statusLabel(item.status)}
                    </Text>
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
                </View>
              ))
            )}

            {/* 热点推荐 */}
            <Text style={[styles.sectionTitle, { marginTop: Layout.spacing.lg }]}>热点推荐</Text>
            {topics.length === 0 ? (
              <View style={styles.emptyBox}>
                <Ionicons name="trending-up-outline" size={28} color={Colors.textMuted} />
                <Text style={styles.emptyText}>暂无热点推荐</Text>
              </View>
            ) : (
              topics.map((t) => (
                <TouchableOpacity
                  key={t.id}
                  style={styles.listCard}
                  onPress={() => setQuery(t.name)}
                >
                  <View style={[styles.listCardIcon, { backgroundColor: '#FEE2E2' }]}>
                    <Ionicons name="flame-outline" size={18} color="#DC2626" />
                  </View>
                  <View style={styles.listCardBody}>
                    <Text style={styles.listCardTitle}>{t.name}</Text>
                    <Text style={styles.listCardMeta}>{t.reason}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
                </TouchableOpacity>
              ))
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  )
}

function statusLabel(s: RecentItem['status']) {
  return { pending: '待开始', running: '进行中', completed: '已完成', failed: '失败' }[s] ?? s
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
  },
  searchInput: {
    flex: 1,
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    padding: 0,
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Layout.spacing.sm,
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.md,
    paddingVertical: Layout.spacing.md,
    marginTop: Layout.spacing.md,
  },
  primaryButtonDisabled: { opacity: 0.5 },
  primaryButtonText: {
    fontSize: Layout.fontSize.md,
    fontWeight: '600',
    color: Colors.white,
  },
  resultCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: Layout.spacing.md,
    marginTop: Layout.spacing.md,
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
    backgroundColor: Colors.success + '15',
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
  resultChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Layout.spacing.sm,
  },
  resultChip: {
    minHeight: Layout.touchTarget.min,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm,
    borderRadius: Layout.borderRadius.full,
    backgroundColor: Colors.background,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.xs,
    textAlignVertical: 'center',
  },
  sectionTitle: {
    fontSize: Layout.fontSize.sm,
    fontWeight: '600',
    color: Colors.textSecondary,
    marginTop: Layout.spacing.xl,
    marginBottom: Layout.spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
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
  loadingBox: { alignItems: 'center', padding: Layout.spacing.xl },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    backgroundColor: '#FEE2E2',
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginTop: Layout.spacing.md,
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
})
