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
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { api } from '@/services/api'
import { useStackHeaderOptions, useTheme } from '@/lib/theme'
import { DomainStripe } from '@/components/DomainBadge'

/**
 * 找律师 —— 移动端匿名咨询转化链路。
 *
 * 保持 `/lawyer/lawyers` 真实列表能力，同时补齐移动端核心闭环：
 * 描述问题 -> 后端生成匿名摘要 -> 推荐律师 -> 创建匿名咨询室 / 尝试委托。
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
  success_cases?: number | null
  hourly_rate_min?: number | null
  hourly_rate_max?: number | null
  is_online?: boolean
  is_verified?: boolean
  match_score?: number
  match_reason?: string
}

interface LawyerListResponse {
  items: LawyerProfile[]
  total: number
}

interface ConsultationResult {
  consultation_id: string
  status: string
  anonymous_summary: string
  legal_domain?: string | null
  domain_label?: string | null
  domain_confidence?: number | null
  risk_level?: 'low' | 'medium' | 'high' | string | null
  message?: string
}

interface AnonymousRoomResult {
  room_id: string
  message?: string
}

interface DelegationResult {
  delegation_id: string
  status: string
  message?: string
}

const DOMAINS = [
  { key: '', label: '全部' },
  { key: 'contract', label: '合同纠纷' },
  { key: 'labor', label: '劳动争议' },
  { key: 'ip', label: '知识产权' },
  { key: 'corporate', label: '公司治理' },
  { key: 'litigation', label: '民事诉讼' },
  { key: 'compliance', label: '合规审查' },
  { key: 'criminal', label: '刑事案件' },
] as const

const URGENCY_OPTIONS = [
  { key: 'low', label: '一般', desc: '先了解' },
  { key: 'medium', label: '尽快', desc: '近期处理' },
  { key: 'high', label: '紧急', desc: '优先响应' },
  { key: 'urgent', label: '很急', desc: '即时匹配' },
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
  const [description, setDescription] = useState('')
  const [urgency, setUrgency] = useState('medium')
  const [consultation, setConsultation] = useState<ConsultationResult | null>(null)
  const [consultationError, setConsultationError] = useState<string | null>(null)
  const [submittingConsultation, setSubmittingConsultation] = useState(false)
  const [selectedLawyerId, setSelectedLawyerId] = useState<string | null>(null)
  const [creatingRoom, setCreatingRoom] = useState(false)
  const [delegating, setDelegating] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const headerOptions = useStackHeaderOptions({ title: '找律师' })
  const theme = useTheme()

  const selectedLawyer = useMemo(
    () => lawyers.find((lawyer) => lawyer.id === selectedLawyerId) ?? null,
    [lawyers, selectedLawyerId],
  )

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
  }, [activeDomain]) // eslint-disable-line react-hooks/exhaustive-deps

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    loadPage(1, true)
  }, [loadPage])

  const onEndReached = useCallback(() => {
    if (loadingMore || loading || lawyers.length >= total) return
    setLoadingMore(true)
    loadPage(page + 1, false)
  }, [lawyers.length, total, page, loadingMore, loading, loadPage])

  const onSearch = useCallback(() => {
    loadPage(1, true)
  }, [loadPage])

  const handleCreateConsultation = useCallback(async () => {
    const trimmed = description.trim()
    if (trimmed.length < 10 || submittingConsultation) {
      setConsultationError('请至少用 10 个字描述问题，方便 AI 生成可脱敏摘要')
      return
    }

    try {
      setSubmittingConsultation(true)
      setConsultationError(null)
      setActionError(null)
      setActionMessage(null)
      const result = await api.post<ConsultationResult>('/lawyer/consultations', {
        description: trimmed,
        legal_domain: activeDomain || undefined,
        urgency,
      })
      setConsultation(result)
      setSelectedLawyerId(null)
      const nextDomain = result.legal_domain && result.legal_domain !== 'other' ? result.legal_domain : activeDomain
      if (nextDomain && nextDomain !== activeDomain) {
        setActiveDomain(nextDomain)
      } else {
        loadPage(1, true)
      }
    } catch (err: any) {
      setConsultationError(err?.message || '匿名咨询创建失败，请稍后重试')
    } finally {
      setSubmittingConsultation(false)
    }
  }, [activeDomain, description, loadPage, submittingConsultation, urgency])

  const handleCreateAnonymousRoom = useCallback(async () => {
    if (!consultation || !selectedLawyer || creatingRoom) return

    try {
      setCreatingRoom(true)
      setActionError(null)
      const result = await api.post<AnonymousRoomResult>('/anonymous-chat/rooms', {
        consultation_id: consultation.consultation_id,
        lawyer_name: selectedLawyer.real_name,
      })
      setActionMessage(
        result.message ||
          `匿名咨询室已创建（${result.room_id}）。你可以继续选择委托，或等待后续消息中心承接会话。`,
      )
    } catch (err: any) {
      setActionError(err?.message || '匿名咨询室创建失败，请稍后重试')
    } finally {
      setCreatingRoom(false)
    }
  }, [consultation, creatingRoom, selectedLawyer])

  const handleCreateDelegation = useCallback(async () => {
    if (!consultation || !selectedLawyer || delegating) return

    try {
      setDelegating(true)
      setActionError(null)
      const result = await api.post<DelegationResult>(
        `/lawyer/consultations/${consultation.consultation_id}/delegate`,
        {
          title: `${selectedLawyer.real_name} 委托申请`,
          description: consultation.anonymous_summary || description.trim(),
          service_type: 'instant',
        },
      )
      setActionMessage(result.message || `委托已创建，状态：${result.status}`)
    } catch (err: any) {
      setActionError(err?.message || '当前需要律师先接单，接单后才能正式委托')
    } finally {
      setDelegating(false)
    }
  }, [consultation, delegating, description, selectedLawyer])

  const renderConsultationHeader = () => (
    <View>
      <View style={styles.searchContainer}>
        <Ionicons name="location-outline" size={16} color={Colors.textSecondary} />
        <TextInput
          style={styles.searchInput}
          placeholder="输入城市（选填）"
          placeholderTextColor={Colors.textMuted}
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
          {DOMAINS.map((domain) => (
            <TouchableOpacity
              key={domain.key || 'all'}
              style={[styles.tab, activeDomain === domain.key && styles.tabActive]}
              onPress={() => setActiveDomain(domain.key)}
            >
              <Text
                style={[
                  styles.tabText,
                  activeDomain === domain.key && styles.tabTextActive,
                ]}
              >
                {domain.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>

      <View style={styles.flowPanel}>
        <View style={styles.flowHeader}>
          <View style={styles.flowIcon}>
            <Ionicons name="shield-checkmark-outline" size={22} color={Colors.primary} />
          </View>
          <View style={styles.flowHeaderText}>
            <Text style={styles.flowTitle}>匿名咨询匹配</Text>
            <Text style={styles.flowSubtitle}>先让 AI 脱敏整理案情，再选择律师沟通</Text>
          </View>
        </View>

        <TextInput
          style={styles.descriptionInput}
          placeholder="请描述企业或个人遇到的问题，例如合同违约、员工离职争议、税务处罚、股权纠纷等..."
          placeholderTextColor={Colors.textMuted}
          value={description}
          onChangeText={setDescription}
          multiline
          textAlignVertical="top"
          maxLength={5000}
        />

        <View style={styles.urgencyRow}>
          {URGENCY_OPTIONS.map((item) => {
            const selected = urgency === item.key
            return (
              <TouchableOpacity
                key={item.key}
                style={[styles.urgencyChip, selected && styles.urgencyChipActive]}
                onPress={() => setUrgency(item.key)}
              >
                <Text style={[styles.urgencyLabel, selected && styles.urgencyLabelActive]}>
                  {item.label}
                </Text>
                <Text style={[styles.urgencyDesc, selected && styles.urgencyDescActive]}>
                  {item.desc}
                </Text>
              </TouchableOpacity>
            )
          })}
        </View>

        {consultationError && (
          <View style={styles.errorBanner}>
            <Ionicons name="warning-outline" size={16} color={Colors.error} />
            <Text style={styles.errorText}>{consultationError}</Text>
          </View>
        )}

        <TouchableOpacity
          style={[
            styles.primaryButton,
            (description.trim().length < 10 || submittingConsultation) && styles.primaryButtonDisabled,
          ]}
          disabled={description.trim().length < 10 || submittingConsultation}
          onPress={handleCreateConsultation}
        >
          {submittingConsultation ? (
            <ActivityIndicator size="small" color={Colors.white} />
          ) : (
            <Ionicons name="sparkles-outline" size={16} color={Colors.white} />
          )}
          <Text style={styles.primaryButtonText}>
            {submittingConsultation ? 'AI 分析中...' : '生成匿名摘要并匹配'}
          </Text>
        </TouchableOpacity>

        {consultation && (
          <View style={styles.anonymousSummaryCard}>
            <View style={styles.summaryHeader}>
              <Ionicons name="document-text-outline" size={18} color={Colors.primary} />
              <Text style={styles.summaryTitle}>AI 匿名摘要</Text>
            </View>
            <Text style={styles.summaryBody}>{consultation.anonymous_summary}</Text>
            <View style={styles.summaryChips}>
              <Text style={styles.summaryChip}>{consultation.domain_label || getDomainLabel(consultation.legal_domain)}</Text>
              <Text style={styles.summaryChip}>风险：{riskLabel(consultation.risk_level)}</Text>
              <Text style={styles.summaryChip}>状态：{consultation.status}</Text>
            </View>
          </View>
        )}

        {selectedLawyer && (
          <View style={styles.selectedPanel}>
            <Text style={styles.selectedTitle}>已选择 {selectedLawyer.real_name}</Text>
            <Text style={styles.selectedMeta}>
              {selectedLawyer.law_firm || '独立执业'} · {selectedLawyer.specializations?.[0] || '综合法务'}
            </Text>
            <View style={styles.actionRow}>
              <TouchableOpacity
                style={[
                  styles.secondaryActionButton,
                  (!consultation || creatingRoom) && styles.actionDisabled,
                ]}
                disabled={!consultation || creatingRoom}
                onPress={handleCreateAnonymousRoom}
              >
                {creatingRoom ? (
                  <ActivityIndicator size="small" color={Colors.text} />
                ) : (
                  <Ionicons name="chatbubbles-outline" size={16} color={Colors.text} />
                )}
                <Text style={styles.secondaryActionText}>匿名咨询</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.primaryActionButton,
                  (!consultation || delegating) && styles.actionDisabled,
                ]}
                disabled={!consultation || delegating}
                onPress={handleCreateDelegation}
              >
                {delegating ? (
                  <ActivityIndicator size="small" color={Colors.white} />
                ) : (
                  <Ionicons name="checkmark-circle-outline" size={16} color={Colors.white} />
                )}
                <Text style={styles.primaryActionText}>尝试委托</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {actionMessage && (
          <View style={styles.successBanner}>
            <Ionicons name="checkmark-circle-outline" size={16} color={Colors.success} />
            <Text style={styles.successText}>{actionMessage}</Text>
          </View>
        )}

        {actionError && (
          <View style={styles.errorBanner}>
            <Ionicons name="information-circle-outline" size={16} color={Colors.error} />
            <Text style={styles.errorText}>{actionError}</Text>
          </View>
        )}
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>推荐律师</Text>
        <Text style={styles.sectionMeta}>{total} 位可选</Text>
      </View>
    </View>
  )

  const renderLawyer = ({ item }: { item: LawyerProfile }) => {
    const selected = selectedLawyerId === item.id
    return (
      <TouchableOpacity
        style={[styles.card, selected && styles.cardSelected]}
        activeOpacity={0.75}
        onPress={() => setSelectedLawyerId(selected ? null : item.id)}
      >
        <View style={styles.avatarBox}>
          <View style={styles.avatarPlaceholder}>
            <Text style={styles.avatarLetter}>
              {item.real_name?.charAt(0) || '律'}
            </Text>
          </View>
          {item.is_online && <View style={styles.onlineDot} />}
        </View>
        <View style={styles.cardMain}>
          <View style={styles.nameRow}>
            <Text style={styles.name}>{item.real_name}</Text>
            {selected && (
              <View style={styles.selectedBadge}>
                <Ionicons name="checkmark" size={11} color={Colors.white} />
                <Text style={styles.selectedBadgeText}>已选</Text>
              </View>
            )}
            {item.rating !== null && item.rating !== undefined && item.rating > 0 && (
              <View style={styles.ratingBox}>
                <Ionicons name="star" size={12} color={Colors.warning} />
                <Text style={styles.rating}>{item.rating.toFixed(1)}</Text>
              </View>
            )}
          </View>
          {item.law_firm && <Text style={styles.firm}>{item.law_firm}</Text>}
          <View style={styles.tagsRow}>
            {item.specializations.slice(0, 3).map((specialization) => (
              <View key={specialization} style={styles.tag}>
                <Text style={styles.tagText}>{specialization}</Text>
              </View>
            ))}
          </View>
          <View style={styles.metaRow}>
            {item.years_of_practice !== null && item.years_of_practice !== undefined && (
              <Text style={styles.meta}>执业 {item.years_of_practice} 年</Text>
            )}
            {item.total_cases !== null && item.total_cases !== undefined && (
              <Text style={styles.meta}> · 办理 {item.total_cases} 案</Text>
            )}
            {item.city && <Text style={styles.meta}> · {item.city}</Text>}
          </View>
          <View style={styles.bottomRow}>
            <Text style={styles.priceText}>{priceLabel(item)}</Text>
            {item.match_score !== undefined && (
              <Text style={styles.matchText}>{item.match_reason || '综合推荐'} · {item.match_score} 分</Text>
            )}
          </View>
        </View>
      </TouchableOpacity>
    )
  }

  const renderEmpty = () =>
    loading && lawyers.length === 0 ? (
      <View style={styles.centered}>
        <ActivityIndicator color={Colors.primary} size="large" />
      </View>
    ) : error ? (
      <View style={styles.emptyContainer}>
        <Ionicons name="cloud-offline-outline" size={56} color={Colors.error} />
        <Text style={[styles.emptyText, { color: Colors.error }]}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={() => loadPage(1, true)}>
          <Text style={styles.retryBtnText}>点击重试</Text>
        </TouchableOpacity>
      </View>
    ) : (
      <View style={styles.emptyContainer}>
        <Ionicons name="people-outline" size={56} color={Colors.textMuted} />
        <Text style={styles.emptyText}>暂无匹配律师</Text>
        <Text style={styles.emptySubText}>可以调整领域、城市，或先提交匿名咨询等待平台接单</Text>
      </View>
    )

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: theme.surface }]}
      edges={['bottom']}
    >
      <Stack.Screen options={headerOptions} />
      {/* V3 法务域视觉锚点 — 4pt 高彩条 */}
      <DomainStripe domain="legal" />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <FlatList
          data={lawyers}
          keyExtractor={(item) => item.id}
          renderItem={renderLawyer}
          ListHeaderComponent={renderConsultationHeader}
          ListEmptyComponent={renderEmpty}
          ListFooterComponent={
            loadingMore ? (
              <View style={styles.footerLoading}>
                <ActivityIndicator color={Colors.primary} />
              </View>
            ) : null
          }
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={Colors.primary}
            />
          }
          onEndReached={onEndReached}
          onEndReachedThreshold={0.3}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

function getDomainLabel(domain?: string | null) {
  return DOMAINS.find((item) => item.key === domain)?.label || '综合法务'
}

function riskLabel(risk?: string | null) {
  if (risk === 'high') return '高'
  if (risk === 'medium') return '中'
  if (risk === 'low') return '低'
  return risk || '待评估'
}

function priceLabel(lawyer: LawyerProfile) {
  if (lawyer.hourly_rate_min && lawyer.hourly_rate_max) {
    return `¥${lawyer.hourly_rate_min}-${lawyer.hourly_rate_max}/小时`
  }
  if (lawyer.hourly_rate_min) return `¥${lawyer.hourly_rate_min} 起/小时`
  return '价格面议'
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  flex: { flex: 1 },
  centered: {
    minHeight: 180,
    alignItems: 'center',
    justifyContent: 'center',
  },
  listContent: {
    paddingHorizontal: Layout.spacing.md,
    paddingBottom: Layout.spacing.xl,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.background,
    marginTop: Layout.spacing.md,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.sm + 2,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    gap: Layout.spacing.sm,
  },
  searchInput: { flex: 1, fontSize: Layout.fontSize.sm, color: Colors.text, padding: 0 },
  searchBtn: {
    minHeight: Layout.touchTarget.min,
    justifyContent: 'center',
    paddingHorizontal: Layout.spacing.md,
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.sm,
  },
  searchBtnText: { color: Colors.white, fontSize: Layout.fontSize.sm, fontWeight: '600' },
  tabScroll: { marginTop: Layout.spacing.md, maxHeight: 44 },
  tabRow: { flexDirection: 'row', gap: Layout.spacing.sm },
  tab: {
    minHeight: Layout.touchTarget.min,
    justifyContent: 'center',
    paddingHorizontal: Layout.spacing.md,
    borderRadius: Layout.borderRadius.full,
    backgroundColor: Colors.background,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  tabActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  tabText: { fontSize: Layout.fontSize.sm, color: Colors.textSecondary },
  tabTextActive: { color: Colors.white, fontWeight: '700' },
  flowPanel: {
    backgroundColor: Colors.background,
    borderRadius: Layout.borderRadius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: Layout.spacing.md,
    marginTop: Layout.spacing.md,
    gap: Layout.spacing.md,
  },
  flowHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
  },
  flowIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: Colors.primary + '18',
    alignItems: 'center',
    justifyContent: 'center',
  },
  flowHeaderText: { flex: 1 },
  flowTitle: { fontSize: Layout.fontSize.lg, fontWeight: '700', color: Colors.text },
  flowSubtitle: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  descriptionInput: {
    minHeight: 128,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    backgroundColor: Colors.surface,
    padding: Layout.spacing.md,
    color: Colors.text,
    fontSize: Layout.fontSize.sm,
    lineHeight: 20,
  },
  urgencyRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Layout.spacing.sm,
  },
  urgencyChip: {
    flexGrow: 1,
    minWidth: 72,
    minHeight: Layout.touchTarget.min,
    justifyContent: 'center',
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: Layout.spacing.sm,
    backgroundColor: Colors.surface,
  },
  urgencyChipActive: { borderColor: Colors.primary, backgroundColor: Colors.primary + '12' },
  urgencyLabel: { fontSize: Layout.fontSize.sm, color: Colors.text, fontWeight: '700' },
  urgencyLabelActive: { color: Colors.primaryDark },
  urgencyDesc: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  urgencyDescActive: { color: Colors.primaryDark },
  primaryButton: {
    minHeight: Layout.touchTarget.min,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Layout.spacing.sm,
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.md,
    paddingVertical: Layout.spacing.md,
  },
  primaryButtonDisabled: { opacity: 0.5 },
  primaryButtonText: { color: Colors.white, fontSize: Layout.fontSize.md, fontWeight: '700' },
  anonymousSummaryCard: {
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.primaryLight,
    backgroundColor: Colors.primary + '10',
    padding: Layout.spacing.md,
    gap: Layout.spacing.sm,
  },
  summaryHeader: { flexDirection: 'row', alignItems: 'center', gap: Layout.spacing.sm },
  summaryTitle: { fontSize: Layout.fontSize.sm, fontWeight: '700', color: Colors.text },
  summaryBody: { fontSize: Layout.fontSize.sm, color: Colors.text, lineHeight: 20 },
  summaryChips: { flexDirection: 'row', flexWrap: 'wrap', gap: Layout.spacing.sm },
  summaryChip: {
    minHeight: 32,
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 6,
    borderRadius: Layout.borderRadius.full,
    backgroundColor: Colors.background,
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.xs,
    overflow: 'hidden',
  },
  selectedPanel: {
    borderRadius: Layout.borderRadius.md,
    backgroundColor: Colors.surface,
    padding: Layout.spacing.md,
    gap: Layout.spacing.sm,
  },
  selectedTitle: { fontSize: Layout.fontSize.md, fontWeight: '700', color: Colors.text },
  selectedMeta: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary },
  actionRow: { flexDirection: 'row', gap: Layout.spacing.sm },
  secondaryActionButton: {
    flex: 1,
    minHeight: Layout.touchTarget.min,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Layout.spacing.xs,
    borderRadius: Layout.borderRadius.md,
    backgroundColor: Colors.background,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  primaryActionButton: {
    flex: 1,
    minHeight: Layout.touchTarget.min,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Layout.spacing.xs,
    borderRadius: Layout.borderRadius.md,
    backgroundColor: Colors.primary,
  },
  actionDisabled: { opacity: 0.45 },
  secondaryActionText: { fontSize: Layout.fontSize.sm, fontWeight: '700', color: Colors.text },
  primaryActionText: { fontSize: Layout.fontSize.sm, fontWeight: '700', color: Colors.white },
  errorBanner: {
    minHeight: Layout.touchTarget.min,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    backgroundColor: Colors.error + '12',
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
  },
  errorText: { flex: 1, color: Colors.error, fontSize: Layout.fontSize.sm, lineHeight: 20 },
  successBanner: {
    minHeight: Layout.touchTarget.min,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    backgroundColor: Colors.success + '12',
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
  },
  successText: { flex: 1, color: Colors.text, fontSize: Layout.fontSize.sm, lineHeight: 20 },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: Layout.spacing.lg,
    marginBottom: Layout.spacing.sm,
  },
  sectionTitle: { fontSize: Layout.fontSize.sm, color: Colors.textSecondary, fontWeight: '700' },
  sectionMeta: { fontSize: Layout.fontSize.xs, color: Colors.textMuted },
  card: {
    flexDirection: 'row',
    backgroundColor: Colors.background,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
    gap: Layout.spacing.md,
  },
  cardSelected: { borderColor: Colors.primary, backgroundColor: Colors.primary + '08' },
  avatarBox: { position: 'relative' },
  avatarPlaceholder: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: Colors.primary + '18',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarLetter: { fontSize: Layout.fontSize.xl, fontWeight: '700', color: Colors.primaryDark },
  onlineDot: {
    position: 'absolute',
    right: 0,
    bottom: 2,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: Colors.success,
    borderWidth: 2,
    borderColor: Colors.background,
  },
  cardMain: { flex: 1, minWidth: 0 },
  nameRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: Layout.spacing.xs },
  name: { fontSize: Layout.fontSize.md, fontWeight: '700', color: Colors.text },
  selectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    backgroundColor: Colors.primary,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Layout.borderRadius.full,
  },
  selectedBadgeText: { fontSize: 11, color: Colors.white, fontWeight: '700' },
  ratingBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    backgroundColor: Colors.warning + '15',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Layout.borderRadius.full,
  },
  rating: { fontSize: 11, color: Colors.warning, fontWeight: '700' },
  firm: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  tagsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Layout.spacing.xs, marginTop: Layout.spacing.sm },
  tag: {
    backgroundColor: Colors.surface,
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 3,
    borderRadius: Layout.borderRadius.sm,
  },
  tagText: { fontSize: 11, color: Colors.textSecondary },
  metaRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', marginTop: Layout.spacing.sm },
  meta: { fontSize: 11, color: Colors.textMuted },
  bottomRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    marginTop: Layout.spacing.sm,
  },
  priceText: { flex: 1, fontSize: 11, color: Colors.textSecondary },
  matchText: { fontSize: 11, color: Colors.primaryDark, fontWeight: '600' },
  footerLoading: { paddingVertical: Layout.spacing.md },
  emptyContainer: {
    minHeight: 220,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Layout.spacing.lg,
  },
  emptyText: { fontSize: Layout.fontSize.md, color: Colors.textSecondary, marginTop: Layout.spacing.md },
  emptySubText: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textMuted,
    marginTop: Layout.spacing.xs,
    textAlign: 'center',
    lineHeight: 20,
  },
  retryBtn: {
    minHeight: Layout.touchTarget.min,
    justifyContent: 'center',
    marginTop: Layout.spacing.md,
    paddingHorizontal: Layout.spacing.lg,
    backgroundColor: Colors.primary,
    borderRadius: Layout.borderRadius.md,
  },
  retryBtnText: { color: Colors.white, fontSize: Layout.fontSize.sm, fontWeight: '700' },
})
