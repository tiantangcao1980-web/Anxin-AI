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

// @mock-data FALLBACK: 后端就绪后从 /lawyers/{profileId} API 获取

const mockProfile: LawyerProfileData = {
  id: 'mock-profile-001',
  real_name: '张明律师',
  avatar_url: null,
  law_firm: '北京盈科律师事务所',
  years_of_practice: 12,
  city: '北京',
  province: '北京市',
  specializations: ['合同纠纷', '公司法', '知识产权', '劳动争议'],
  bio: '毕业于中国政法大学，曾任某知名科技公司法务总监。专注企业法律服务领域超过 12 年，累计服务企业客户 200+，擅长合同纠纷、股权架构设计、知识产权保护等领域。秉持"预防优于诉讼"的服务理念，为客户提供全流程法律风险管控方案。',
  hourly_rate_min: 500,
  hourly_rate_max: 1200,
  rating: 4.8,
  total_cases: 356,
  success_cases: 328,
  total_reviews: 89,
  is_verified: true,
  is_online: true,
}

const mockStats: ReviewStats = {
  average_rating: 4.8,
  total_reviews: 89,
  rating_distribution: { 1: 1, 2: 2, 3: 5, 4: 18, 5: 63 },
  top_tags: [
    { tag: '专业', count: 56 },
    { tag: '耐心', count: 43 },
    { tag: '高效', count: 38 },
    { tag: '态度好', count: 29 },
    { tag: '经验丰富', count: 22 },
    { tag: '解释清晰', count: 18 },
  ],
}

const mockReviews: Review[] = [
  {
    id: 'r1',
    rating: 5,
    content: '张律师非常专业，帮我们公司处理了一起复杂的合同纠纷案件，从法律分析到庭审准备都非常细致。最终帮我们挽回了大量损失，非常感谢！',
    tags: ['专业', '高效', '经验丰富'],
    is_anonymous: false,
    reviewer_id: 'u1',
    reviewer_name: '李先生',
    reply_content: '感谢您的信任和认可，能帮到您很高兴。如后续有法律需求可随时联系。',
    replied_at: '2026-03-20T10:30:00',
    created_at: '2026-03-18T14:20:00',
  },
  {
    id: 'r2',
    rating: 5,
    content: '咨询了劳动合同方面的问题，张律师给出了非常详细的解答和建议，态度非常好，解答也很专业。',
    tags: ['耐心', '态度好', '解释清晰'],
    is_anonymous: false,
    reviewer_id: 'u2',
    reviewer_name: '王女士',
    reply_content: null,
    replied_at: null,
    created_at: '2026-03-15T09:00:00',
  },
  {
    id: 'r3',
    rating: 4,
    content: '知识产权案件处理得很好，过程中沟通也很及时。唯一不足是前期等待时间稍长，可能是律师太忙了。',
    tags: ['专业', '高效'],
    is_anonymous: true,
    reviewer_id: null,
    reviewer_name: null,
    reply_content: '感谢您的反馈，我们会优化咨询响应流程，缩短等待时间。',
    replied_at: '2026-03-12T16:00:00',
    created_at: '2026-03-10T11:30:00',
  },
  {
    id: 'r4',
    rating: 5,
    content: '股权架构方面的咨询，张律师给的方案非常系统，有理有据。推荐！',
    tags: ['专业', '经验丰富'],
    is_anonymous: false,
    reviewer_id: 'u4',
    reviewer_name: '赵总',
    reply_content: null,
    replied_at: null,
    created_at: '2026-03-05T13:45:00',
  },
  {
    id: 'r5',
    rating: 3,
    content: '基本问题回答了，但感觉不太深入。可能是咨询时间太短的原因。',
    tags: [],
    is_anonymous: true,
    reviewer_id: null,
    reviewer_name: null,
    reply_content: null,
    replied_at: null,
    created_at: '2026-02-28T08:15:00',
  },
]

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

  // 模拟加载
  useEffect(() => {
    setLoading(true)
    const timer = setTimeout(() => setLoading(false), 300)
    return () => clearTimeout(timer)
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

  // TODO: 根据 profileId 从 API 获取数据
  // const { data: profile } = useSWR(`/lawyer/lawyers/${profileId}`, fetcher)
  const profile = mockProfile
  const stats = mockStats
  const reviews = mockReviews
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
