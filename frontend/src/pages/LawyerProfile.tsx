/**
 * LawyerProfile - 律师公开主页
 *
 * 展示律师的详细信息、评价统计和评价列表。
 * 当前使用 mock 数据，后续接入 API。
 */

import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cardStyle, heading, statusBadge, chartColors, iconSize } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { expertsApi } from '@/lib/api'

// ===== 类型定义 =====

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

// 数据从 API 加载

// ===== 辅助组件 =====

function StarRating({ rating, size = 'sm' }: { rating: number; size?: 'sm' | 'md' }) {
  const sizeClass = size === 'md' ? 'w-5 h-5' : 'w-4 h-4'
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <icons.Star
          key={i}
          className={`${sizeClass} ${
            i <= Math.round(rating)
              ? 'text-amber-400 fill-amber-400'
              : 'text-muted-foreground/30'
          }`}
        />
      ))}
    </div>
  )
}

function formatDate(isoString: string): string {
  const d = new Date(isoString)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// ===== 主组件 =====

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
        // 适配后端 ExpertItem 字段到 LawyerProfileData
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
        // 评价统计和评价列表作为详情的一部分返回
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
          setReviews(
            data.reviews.map((r: any) => ({
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
            }))
          )
        } else {
          setReviews([])
        }
      } catch (err: any) {
        if (!cancelled) setError(err.message || '加载律师信息失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchProfile()
    return () => { cancelled = true }
  }, [profileId])

  // profileId 不存在时渲染 404
  if (!profileId) {
    return (
      <PageContainer title="律师详情">
        <div className="flex flex-col items-center justify-center py-20">
          <icons.User className={`${iconSize['2xl']} text-muted-foreground/40 mb-4`} />
          <p className={heading.section}>未找到律师信息</p>
          <p className="text-sm text-muted-foreground mt-1">该律师页面不存在或已被移除</p>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/find-lawyer')}>
            返回律师列表
          </Button>
        </div>
      </PageContainer>
    )
  }

  // loading 骨架屏
  if (loading) {
    return (
      <PageContainer title="律师详情">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className={cardStyle.base}>
            <div className="flex gap-5">
              <Skeleton className="w-20 h-20 rounded-full shrink-0" />
              <div className="flex-1 space-y-3">
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-4 w-1/4" />
              </div>
            </div>
          </div>
          <div className={cardStyle.base}>
            <Skeleton className="h-5 w-24 mb-3" />
            <div className="flex gap-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-20 rounded-lg" />
              ))}
            </div>
          </div>
          <div className={cardStyle.base}>
            <Skeleton className="h-5 w-24 mb-3" />
            <Skeleton className="h-16 w-full" />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className={`${cardStyle.base} text-center`}>
                <Skeleton className="h-4 w-16 mx-auto mb-2" />
                <Skeleton className="h-7 w-12 mx-auto" />
              </div>
            ))}
          </div>
        </div>
      </PageContainer>
    )
  }

  // 错误状态
  if (error) {
    return (
      <PageContainer title="律师详情">
        <div className="flex flex-col items-center justify-center py-20">
          <icons.AlertTriangle className={`${iconSize['2xl']} text-destructive/60 mb-4`} />
          <p className={heading.section}>加载失败</p>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
          <Button variant="outline" className="mt-4" onClick={() => { setError(null); setLoading(true) }}>
            重新加载
          </Button>
        </div>
      </PageContainer>
    )
  }

  if (!profile) {
    return (
      <PageContainer title="律师详情">
        <div className="flex flex-col items-center justify-center py-20">
          <icons.User className={`${iconSize['2xl']} text-muted-foreground/40 mb-4`} />
          <p className={heading.section}>暂无律师数据</p>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/find-lawyer')}>
            返回律师列表
          </Button>
        </div>
      </PageContainer>
    )
  }

  const pageSize = 5
  const totalPages = Math.ceil(reviews.length / pageSize)
  const displayedReviews = reviews.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  // 评分分布图数据
  const ratingChartData = [5, 4, 3, 2, 1].map((r) => ({
    name: `${r} 星`,
    count: stats.rating_distribution[r] || 0,
  }))

  const successRate = profile.total_cases > 0
    ? Math.round((profile.success_cases / profile.total_cases) * 100)
    : 0

  return (
    <PageContainer title="律师详情">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 顶部信息卡 */}
        <div className={cardStyle.base}>
          <div className="flex flex-col sm:flex-row gap-5">
            {/* 头像 */}
            <div className="shrink-0 flex justify-center sm:justify-start">
              <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center text-primary text-2xl font-bold">
                {profile.real_name.charAt(0)}
              </div>
            </div>
            {/* 基本信息 */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-xl font-bold text-foreground">{profile.real_name}</h2>
                {profile.is_verified && (
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-md ${statusBadge.info}`}>
                    <icons.ShieldCheck className={iconSize.xs} />
                    已认证
                  </span>
                )}
                {profile.is_online && (
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-md ${statusBadge.success}`}>
                    在线
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {profile.law_firm} &middot; 执业 {profile.years_of_practice} 年 &middot; {profile.city}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <StarRating rating={profile.rating} size="md" />
                <span className="text-sm font-medium text-foreground">{profile.rating}</span>
                <span className="text-xs text-muted-foreground">({profile.total_reviews} 条评价)</span>
              </div>
            </div>
          </div>
        </div>

        {/* 专业领域 */}
        <div className={cardStyle.base}>
          <h3 className={heading.section}>专业领域</h3>
          <div className="flex flex-wrap gap-2 mt-3">
            {profile.specializations.map((spec) => (
              <span
                key={spec}
                className="px-3 py-1.5 text-sm rounded-lg bg-primary/5 text-primary border border-primary/10"
              >
                {spec}
              </span>
            ))}
          </div>
        </div>

        {/* 简介 */}
        <div className={cardStyle.base}>
          <h3 className={heading.section}>律师简介</h3>
          <p className="mt-3 text-sm text-foreground/80 leading-relaxed">{profile.bio}</p>
        </div>

        {/* 数据卡片行 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className={`${cardStyle.base} text-center`}>
            <p className={heading.micro}>收费标准</p>
            <p className="text-lg font-bold text-foreground mt-1">
              {profile.hourly_rate_min}-{profile.hourly_rate_max}
            </p>
            <p className="text-xs text-muted-foreground">元/小时</p>
          </div>
          <div className={`${cardStyle.base} text-center`}>
            <p className={heading.micro}>办理案件</p>
            <p className="text-lg font-bold text-foreground mt-1">{profile.total_cases}</p>
            <p className="text-xs text-muted-foreground">件</p>
          </div>
          <div className={`${cardStyle.base} text-center`}>
            <p className={heading.micro}>成功案例</p>
            <p className="text-lg font-bold text-foreground mt-1">{profile.success_cases}</p>
            <p className="text-xs text-muted-foreground">件</p>
          </div>
          <div className={`${cardStyle.base} text-center`}>
            <p className={heading.micro}>成功率</p>
            <p className="text-lg font-bold text-emerald-600 mt-1">{successRate}%</p>
            <p className="text-xs text-muted-foreground">胜诉/调解</p>
          </div>
        </div>

        {/* 评价统计 */}
        <div className={cardStyle.base}>
          <h3 className={heading.section}>评价统计</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
            {/* 左侧: 评分分布 */}
            <div>
              <div className="flex items-center gap-3 mb-4">
                <span className="text-4xl font-bold text-foreground">{stats.average_rating}</span>
                <div>
                  <StarRating rating={stats.average_rating} size="md" />
                  <p className="text-xs text-muted-foreground mt-0.5">{stats.total_reviews} 条评价</p>
                </div>
              </div>
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ratingChartData} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <XAxis type="number" hide />
                    <YAxis type="category" dataKey="name" width={40} tick={{ fontSize: 12 }} />
                    <Tooltip
                      formatter={(value: number) => [`${value} 条`, '数量']}
                      contentStyle={{ borderRadius: 8, border: '1px solid var(--border)' }}
                    />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={20}>
                      {ratingChartData.map((_, idx) => (
                        <Cell key={idx} fill={chartColors[0]} opacity={1 - idx * 0.15} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 右侧: 热门标签 */}
            <div>
              <p className={`${heading.card} mb-3`}>用户评价标签</p>
              <div className="flex flex-wrap gap-2">
                {stats.top_tags.map((t) => (
                  <span
                    key={t.tag}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-muted text-foreground/80"
                  >
                    {t.tag}
                    <span className="text-xs text-muted-foreground">({t.count})</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 评价列表 */}
        <div className={cardStyle.base}>
          <h3 className={heading.section}>用户评价</h3>
          <div className="mt-4 space-y-4">
            {displayedReviews.map((review) => (
              <div key={review.id} className="border-b border-border last:border-b-0 pb-4 last:pb-0">
                {/* 评价头部 */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
                      {review.is_anonymous ? '匿' : (review.reviewer_name?.charAt(0) || '?')}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {review.is_anonymous ? '匿名用户' : review.reviewer_name}
                      </p>
                      <p className="text-xs text-muted-foreground">{formatDate(review.created_at)}</p>
                    </div>
                  </div>
                  <StarRating rating={review.rating} />
                </div>

                {/* 评价内容 */}
                {review.content && (
                  <p className="mt-2 text-sm text-foreground/80 leading-relaxed">{review.content}</p>
                )}

                {/* 标签 */}
                {review.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {review.tags.map((tag) => (
                      <span key={tag} className="px-2 py-0.5 text-xs rounded-md bg-primary/5 text-primary">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* 律师回复 */}
                {review.reply_content && (
                  <div className="mt-3 ml-6 pl-3 border-l-2 border-primary/20 bg-muted/30 rounded-r-lg p-3">
                    <p className="text-xs font-medium text-primary mb-1">律师回复</p>
                    <p className="text-sm text-foreground/80">{review.reply_content}</p>
                    {review.replied_at && (
                      <p className="text-xs text-muted-foreground mt-1">{formatDate(review.replied_at)}</p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4 pt-4 border-t border-border">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                上一页
              </button>
              <span className="text-sm text-muted-foreground">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                下一页
              </button>
            </div>
          )}
        </div>

        {/* 底部固定咨询按钮 */}
        <div className="sticky bottom-4 flex justify-center">
          <button
            onClick={() => navigate('/find-lawyer')}
            className="px-8 py-3 bg-primary text-primary-foreground rounded-xl text-base font-medium shadow-lg hover:bg-primary/90 active:scale-[0.98] transition-all"
          >
            立即咨询
          </button>
        </div>
      </div>
    </PageContainer>
  )
}
