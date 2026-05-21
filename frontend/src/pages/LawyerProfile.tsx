/**
 * LawyerProfile · 律师公开主页（Editorial Luxury 改造 · Phase 2.3）
 *
 * 旧版：cardStyle.base 圆角卡 + bg-primary/5 标签 + statusBadge 色块 + 圆角主咨询按钮。
 * 新版：DetailPageTemplate + PanelSection（hairline）+ tone-only chip + 1px 评分细线 + serif 数字。
 */
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import {
  User, ShieldCheck, AlertTriangle, Star,
} from 'lucide-react'

import { DetailPageTemplate, PanelSection } from '@/components/ui/PageTemplates'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { expertsApi } from '@/lib/api'
import { cn } from '@/components/ui/utils'

interface LawyerProfileData {
  id: string
  real_name: string
  avatar_url: string | null
  law_firm: string
  years_of_practice: number
  city: string
  province: string
  specializations: string[]
  bio: string
  hourly_rate_min: number
  hourly_rate_max: number
  rating: number
  total_cases: number
  success_cases: number
  total_reviews: number
  is_verified: boolean
  is_online: boolean
}

interface ReviewStats {
  average_rating: number
  total_reviews: number
  rating_distribution: Record<number, number>
  top_tags: { tag: string; count: number }[]
}

interface Review {
  id: string
  rating: number
  content: string | null
  tags: string[]
  is_anonymous: boolean
  reviewer_id: string | null
  reviewer_name: string | null
  reply_content: string | null
  replied_at: string | null
  created_at: string
}

function StarRating({ rating, size = 'sm' }: { rating: number; size?: 'sm' | 'md' }) {
  const sizeClass = size === 'md' ? 'w-4 h-4' : 'w-3.5 h-3.5'
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={cn(
            sizeClass, 'stroke-[1.5]',
            i <= Math.round(rating) ? 'text-warning fill-current' : 'text-foreground/15',
          )}
        />
      ))}
    </div>
  )
}

function formatDate(isoString: string): string {
  if (!isoString) return ''
  const d = new Date(isoString)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function LawyerProfile() {
  const { profileId } = useParams<{ profileId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [profile, setProfile] = useState<LawyerProfileData | null>(null)
  const [stats, setStats] = useState<ReviewStats>({ average_rating: 0, total_reviews: 0, rating_distribution: {}, top_tags: [] })
  const [reviews, setReviews] = useState<Review[]>([])

  useEffect(() => {
    if (!profileId) return
    let cancelled = false
    async function fetchProfile() {
      try {
        setLoading(true)
        setError(null)
        const data: any = await expertsApi.get(profileId!)
        if (cancelled) return
        setProfile({
          id: data.id,
          real_name: data.name ?? data.real_name ?? '',
          avatar_url: data.avatar_url ?? data.avatar ?? null,
          law_firm: data.law_firm ?? data.firm ?? '',
          years_of_practice: data.years_of_practice ?? data.experience ?? 0,
          city: data.city ?? '',
          province: data.province ?? '',
          specializations: data.specializations ?? data.specialties ?? [],
          bio: data.bio ?? data.description ?? '',
          hourly_rate_min: data.hourly_rate_min ?? data.rate_min ?? 0,
          hourly_rate_max: data.hourly_rate_max ?? data.rate_max ?? 0,
          rating: data.rating ?? 0,
          total_cases: data.total_cases ?? data.casesHandled ?? 0,
          success_cases: data.success_cases ?? 0,
          total_reviews: data.total_reviews ?? 0,
          is_verified: data.is_verified ?? data.verified ?? false,
          is_online: data.is_online ?? false,
        })
        if (data.review_stats || data.stats) {
          const s = data.review_stats ?? data.stats
          setStats({
            average_rating: s.average_rating ?? data.rating ?? 0,
            total_reviews: s.total_reviews ?? data.total_reviews ?? 0,
            rating_distribution: s.rating_distribution ?? {},
            top_tags: s.top_tags ?? [],
          })
        } else {
          setStats({
            average_rating: data.rating ?? 0,
            total_reviews: data.total_reviews ?? 0,
            rating_distribution: {},
            top_tags: [],
          })
        }
        if (data.reviews) {
          setReviews(data.reviews.map((r: any) => ({
            id: r.id,
            rating: r.rating ?? 0,
            content: r.content ?? null,
            tags: r.tags ?? [],
            is_anonymous: r.is_anonymous ?? false,
            reviewer_id: r.reviewer_id ?? null,
            reviewer_name: r.reviewer_name ?? null,
            reply_content: r.reply_content ?? null,
            replied_at: r.replied_at ?? null,
            created_at: r.created_at ?? '',
          })))
        } else {
          setReviews([])
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message || '加载律师信息失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchProfile()
    return () => { cancelled = true }
  }, [profileId])

  if (!profileId) {
    return (
      <FallbackShell
        tracker="Lawyer · 404"
        title="未找到律师信息"
        description="该律师页面不存在或已被移除。"
        icon={User}
        actionLabel="返回律师列表"
        onAction={() => navigate('/find-lawyer')}
      />
    )
  }

  if (loading) {
    return (
      <DetailPageTemplate
        tracker={['Network', '律师']}
        title="加载中…"
      >
        <div className="space-y-6">
          <div className="border border-border bg-card p-6">
            <div className="flex gap-5">
              <Skeleton className="w-20 h-20 rounded-full shrink-0" />
              <div className="flex-1 space-y-3">
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-4 w-1/4" />
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border border-t border-l border-border">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-card border-r border-b border-border p-5">
                <Skeleton className="h-4 w-16 mb-3" />
                <Skeleton className="h-8 w-12" />
              </div>
            ))}
          </div>
        </div>
      </DetailPageTemplate>
    )
  }

  if (error) {
    return (
      <FallbackShell
        tracker="Lawyer · 错误"
        title="加载失败"
        description={error}
        icon={AlertTriangle}
        actionLabel="重新加载"
        onAction={() => { setError(null); setLoading(true) }}
      />
    )
  }

  if (!profile) {
    return (
      <FallbackShell
        tracker="Lawyer · 空状态"
        title="暂无律师数据"
        icon={User}
        actionLabel="返回律师列表"
        onAction={() => navigate('/find-lawyer')}
      />
    )
  }

  const pageSize = 5
  const totalPages = Math.ceil(reviews.length / pageSize)
  const displayedReviews = reviews.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  const ratingChartData = [5, 4, 3, 2, 1].map((r) => ({
    name: `${r} 星`,
    count: stats.rating_distribution[r] || 0,
  }))

  const successRate = profile.total_cases > 0
    ? Math.round((profile.success_cases / profile.total_cases) * 100)
    : 0

  return (
    <DetailPageTemplate
      tracker={['Network', '律师主页', profile.real_name]}
      title={profile.real_name}
      description={`${profile.law_firm} · 执业 ${profile.years_of_practice} 年 · ${profile.city}`}
      actions={
        <div className="flex items-center gap-3">
          {profile.is_online && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em] text-success">
              <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
              <span>Online</span>
            </span>
          )}
          {profile.is_verified && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em] text-primary">
              <ShieldCheck className="w-3 h-3 stroke-[1.5]" />
              <span>Verified · 已认证</span>
            </span>
          )}
        </div>
      }
      aside={
        <PanelSection tracker="Action · 操作" title="立即委托">
          <p className="text-[13px] text-muted-foreground leading-relaxed mb-4">
            点击下方按钮发起匿名咨询，匹配确认后即可开始委托流程。
          </p>
          <button
            type="button"
            onClick={() => navigate('/find-lawyer')}
            className="w-full bg-primary hover:bg-primary-700 text-primary-foreground py-2.5 text-[14px] font-medium transition-colors"
          >
            立即咨询
          </button>
        </PanelSection>
      }
    >
      {/* 头像 + 评分概况 */}
      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr] gap-6 mb-10">
        <div className="w-20 h-20 border border-border bg-card flex items-center justify-center font-serif text-[36px] text-primary">
          {profile.real_name.charAt(0)}
        </div>
        <div className="space-y-3">
          <div className="inline-flex items-center gap-3">
            <StarRating rating={profile.rating} size="md" />
            <span className="font-serif text-[18px] text-foreground tabular-nums">{profile.rating}</span>
            <span className="text-[12px] text-muted-foreground tabular-nums">
              ({profile.total_reviews} 条评价)
            </span>
          </div>
          <p className="text-[14px] leading-relaxed text-foreground/85 max-w-[60ch]">{profile.bio || '该律师暂未填写简介。'}</p>
        </div>
      </div>

      {/* KPI hairline 网格 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border border-t border-l border-border mb-10">
        <StatsCell tracker="Rate"    label="收费标准"  value={`${profile.hourly_rate_min}-${profile.hourly_rate_max}`} unit="元/小时" />
        <StatsCell tracker="Cases"   label="办理案件"  value={String(profile.total_cases)} unit="件" />
        <StatsCell tracker="Success" label="成功案例"  value={String(profile.success_cases)} unit="件" />
        <StatsCell tracker="Win%"    label="成功率"    value={`${successRate}%`} unit="胜诉/调解" tone="success" />
      </div>

      <PanelSection tracker="Areas · 专业领域" title="专业领域">
        <div className="flex flex-wrap gap-2">
          {profile.specializations.map((spec) => (
            <span key={spec} className="text-[13px] text-foreground/85 border border-border px-3 py-1">
              {spec}
            </span>
          ))}
        </div>
      </PanelSection>

      {/* 评价统计 */}
      <PanelSection tracker="Reviews · 评价" title="评价统计">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <div className="flex items-end gap-3 mb-4">
              <span className="font-serif text-[40px] leading-none text-foreground tabular-nums">{stats.average_rating}</span>
              <div className="mb-1">
                <StarRating rating={stats.average_rating} size="md" />
                <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mt-0.5 tabular-nums">
                  {stats.total_reviews} reviews
                </p>
              </div>
            </div>
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ratingChartData} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={40} tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    formatter={(value: number) => [`${value} 条`, '数量']}
                    contentStyle={{ border: '1px solid var(--border)', background: 'var(--card)', borderRadius: 0, fontSize: 12 }}
                  />
                  <Bar dataKey="count" fill="var(--primary)" radius={[0, 0, 0, 0]} maxBarSize={12} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div>
            <h4 className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-3">
              Tags · 用户评价标签
            </h4>
            <div className="flex flex-wrap gap-2">
              {stats.top_tags.map((t) => (
                <span key={t.tag} className="inline-flex items-center gap-1.5 text-[13px] text-foreground/85 border border-border px-3 py-1">
                  {t.tag}
                  <span className="text-[11px] text-muted-foreground tabular-nums">({t.count})</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </PanelSection>

      {/* 评价列表 */}
      <PanelSection tracker="Reviews · 用户评价" title="用户评价">
        <ol className="space-y-px">
          {displayedReviews.map((review, i) => (
            <li key={review.id} className="py-4 border-b border-border/60 last:border-b-0">
              <div className="flex items-start gap-4">
                <span className="font-serif text-[12px] text-muted-foreground w-8 shrink-0 tabular-nums pt-1.5">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div className="w-8 h-8 border border-border flex items-center justify-center text-[12px] font-medium text-muted-foreground shrink-0">
                  {review.is_anonymous ? '匿' : (review.reviewer_name?.charAt(0) || '?')}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-3 mb-1">
                    <div>
                      <span className="text-[14px] font-medium text-foreground">
                        {review.is_anonymous ? '匿名用户' : review.reviewer_name}
                      </span>
                      <span className="text-[11px] text-muted-foreground ml-2 tabular-nums">
                        {formatDate(review.created_at)}
                      </span>
                    </div>
                    <StarRating rating={review.rating} />
                  </div>
                  {review.content && (
                    <p className="text-[13px] text-foreground/80 leading-relaxed">{review.content}</p>
                  )}
                  {review.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {review.tags.map((tag) => (
                        <span key={tag} className="text-[11px] text-foreground/70 border border-border px-2 py-0.5">{tag}</span>
                      ))}
                    </div>
                  )}
                  {review.reply_content && (
                    <aside className="mt-3 border-l-2 border-primary/40 pl-3 py-1">
                      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-primary mb-1">
                        Reply · 律师回复
                      </div>
                      <p className="text-[13px] text-foreground/80">{review.reply_content}</p>
                      {review.replied_at && (
                        <p className="text-[11px] text-muted-foreground mt-1 tabular-nums">{formatDate(review.replied_at)}</p>
                      )}
                    </aside>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>

        {totalPages > 1 && (
          <footer className="flex items-center justify-center gap-4 mt-6 pt-4 border-t border-border">
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-4 py-1.5 text-[12px] border border-border bg-card hover:bg-surface-2 disabled:opacity-40 transition-colors"
            >
              上一页
            </button>
            <span className="text-[12px] text-muted-foreground tabular-nums">{currentPage} / {totalPages}</span>
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-4 py-1.5 text-[12px] border border-border bg-card hover:bg-surface-2 disabled:opacity-40 transition-colors"
            >
              下一页
            </button>
          </footer>
        )}
      </PanelSection>
    </DetailPageTemplate>
  )
}

function StatsCell({
  tracker, label, value, unit, tone = 'normal',
}: {
  tracker: string
  label: string
  value: string
  unit?: string
  tone?: 'normal' | 'success' | 'warning' | 'error'
}) {
  const toneClass = {
    normal:  'text-foreground',
    success: 'text-success',
    warning: 'text-warning',
    error:   'text-destructive',
  }[tone]
  return (
    <div className="bg-card border-r border-b border-border px-5 py-4">
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {tracker}
        <span className="text-foreground/30 mx-1.5" aria-hidden>·</span>
        <span className="text-foreground/70 normal-case tracking-normal">{label}</span>
      </div>
      <div className={cn('font-serif text-[24px] leading-tight mt-2 tabular-nums', toneClass)}>{value}</div>
      {unit && <div className="text-[11px] text-muted-foreground mt-0.5">{unit}</div>}
    </div>
  )
}

function FallbackShell({
  tracker, title, description, icon: Icon, actionLabel, onAction,
}: {
  tracker: string
  title: string
  description?: string
  icon: typeof User
  actionLabel?: string
  onAction?: () => void
}) {
  return (
    <DetailPageTemplate tracker={['Network', '律师']} title={title}>
      <div className="text-center py-20">
        <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
          {tracker}
        </div>
        <Icon className="w-12 h-12 stroke-[1] text-foreground/20 mx-auto mb-5" />
        <p className="font-serif text-[22px] text-foreground">{title}</p>
        {description && <p className="text-[13px] text-muted-foreground mt-2 max-w-md mx-auto">{description}</p>}
        {actionLabel && onAction && (
          <Button variant="outline" className="mt-6" onClick={onAction}>
            {actionLabel}
          </Button>
        )}
      </div>
    </DetailPageTemplate>
  )
}
