import { useState, useEffect, useMemo } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, buttonStyle, heading, iconSize, inputStyle, statusBadge, chartColors } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { aiAssistantApi } from '@/lib/api'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts'

interface ConversationSummary {
  id: string
  conversation_id?: string
  created_at?: string
  key_topics?: string[]
  summary: string
  action_items?: string[]
  sentiment: 'positive' | 'neutral' | 'negative'
  legal_domains?: string[]
}

interface FeedbackStats {
  total_feedbacks: number
  avg_rating: number
  rating_distribution: Record<string, number>
  type_distribution: Record<string, number>
  trend: Array<{
    date: string
    avg_rating: number
    count: number
  }>
}

interface StatsCard {
  label: string
  value: string | number
  icon: keyof typeof icons
  trend?: string
  trendUp?: boolean
}

type PageState = 'loading' | 'error' | 'ready'

const feedbackTypeLabels: Record<string, string> = {
  helpful: '非常有帮助',
  unhelpful: '帮助有限',
  incorrect: '回答有误',
  offensive: '内容不当',
  other: '其他',
}

const sentimentConfig = {
  positive: { label: '积极', color: 'bg-emerald-500' },
  neutral: { label: '中性', color: 'bg-gray-400' },
  negative: { label: '消极', color: 'bg-red-500' },
} as const

export default function ConversationInsights() {
  const [state, setState] = useState<PageState>('loading')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [summaries, setSummaries] = useState<ConversationSummary[]>([])
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStats | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setState('loading')
    setError('')
    try {
      const [summaryData, statsData] = await Promise.all([
        aiAssistantApi.listSummaries({ page: 1, page_size: 50 }),
        aiAssistantApi.getFeedbackStats(30),
      ])
      setSummaries(summaryData || [])
      setFeedbackStats(statsData || null)
      setState('ready')
    } catch (e: any) {
      setSummaries([])
      setFeedbackStats(null)
      setError(e.message || '无法加载对话洞察数据')
      setState('error')
    }
  }

  const statsCards = useMemo<StatsCard[]>(() => {
    const currentMonth = new Date().toISOString().slice(0, 7)
    const monthlyNewCount = summaries.filter(item => item.created_at?.startsWith(currentMonth)).length
    const todoCount = summaries.reduce((count, item) => count + (item.action_items?.length || 0), 0)
    const avgRating = feedbackStats?.avg_rating ?? 0
    const totalFeedbacks = feedbackStats?.total_feedbacks ?? 0
    const helpfulCount = feedbackStats?.type_distribution?.helpful ?? 0
    const helpfulRate = totalFeedbacks > 0 ? Math.round((helpfulCount / totalFeedbacks) * 100) : 0

    return [
      { label: '总摘要数', value: summaries.length, icon: 'Chat' },
      { label: '本月新增', value: monthlyNewCount, icon: 'Calendar' },
      { label: '平均满意度', value: avgRating ? avgRating.toFixed(1) : '0.0', icon: 'Star' },
      { label: '待办事项', value: todoCount, icon: 'Tasks', trend: `${helpfulRate}%`, trendUp: true },
    ]
  }, [feedbackStats, summaries])

  const filteredSummaries = useMemo(() => {
    if (!searchQuery.trim()) return summaries
    const q = searchQuery.toLowerCase()
    return summaries.filter(
      s =>
        (s.conversation_id || '').toLowerCase().includes(q) ||
        s.summary.toLowerCase().includes(q) ||
        (s.key_topics || []).some(t => t.toLowerCase().includes(q))
    )
  }, [searchQuery, summaries])

  const ratingDistribution = useMemo(
    () =>
      Array.from({ length: 5 }, (_, index) => {
        const rating = index + 1
        return {
          rating: `${rating}星`,
          count: feedbackStats?.rating_distribution?.[String(rating)] ?? feedbackStats?.rating_distribution?.[rating] ?? 0,
        }
      }),
    [feedbackStats]
  )

  const feedbackTypes = useMemo(
    () =>
      Object.entries(feedbackStats?.type_distribution || {}).map(([key, value], index) => ({
        key,
        name: feedbackTypeLabels[key] || key,
        value,
        color: chartColors[index % chartColors.length],
      })),
    [feedbackStats]
  )

  const satisfactionTrend = useMemo(
    () =>
      (feedbackStats?.trend || []).map(item => ({
        date: item.date.slice(5).replace('-', '/'),
        满意度: item.avg_rating,
        count: item.count,
      })),
    [feedbackStats]
  )

  if (state === 'loading') {
    return (
      <PageContainer title="对话洞察" description="AI 对话分析与反馈统计">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-96 rounded-xl mt-6" />
      </PageContainer>
    )
  }

  if (state === 'error') {
    return (
      <PageContainer title="对话洞察" description="AI 对话分析与反馈统计">
        <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
          <icons.AlertCircle className={`${iconSize.xl} text-destructive mb-3`} />
          <p className={heading.section}>加载失败</p>
          <p className={`${heading.muted} mt-1`}>{error}</p>
          <Button className="mt-4" onClick={loadData}>
            <icons.Refresh className={iconSize.sm} />
            重试
          </Button>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="对话洞察" description="AI 对话分析与反馈统计">
      {/* ===== 顶部统计卡片 ===== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statsCards.map(stat => {
          const Icon = icons[stat.icon]
          return (
            <div key={stat.label} className={cardStyle.base}>
              <div className="flex items-start justify-between">
                <div>
                  <p className={heading.micro}>{stat.label}</p>
                  <p className="text-2xl font-bold text-foreground mt-1">
                    {stat.label === '平均满意度' ? (
                      <span className="flex items-center gap-1">
                        {stat.value}
                        <icons.Star className="w-5 h-5 text-amber-500 fill-amber-500" />
                      </span>
                    ) : (
                      stat.value
                    )}
                  </p>
                </div>
                <div className="p-2 rounded-lg bg-primary/5">
                  <Icon className={`${iconSize.md} text-primary`} />
                </div>
              </div>
              {stat.trend && (
                <p className={`text-xs mt-2 ${stat.trendUp ? 'text-emerald-600' : 'text-red-600'}`}>
                  {stat.trendUp ? <icons.TrendingUp className="w-3 h-3 inline mr-1" /> : <icons.TrendingDown className="w-3 h-3 inline mr-1" />}
                  {stat.trend} 较上月
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* ===== 主区域 Tabs ===== */}
      <Tabs defaultValue="summaries" className="space-y-4">
        <TabsList>
          <TabsTrigger value="summaries" className="flex items-center gap-1.5 text-sm">
            <icons.FileText className={iconSize.sm} />
            对话摘要
          </TabsTrigger>
          <TabsTrigger value="feedback" className="flex items-center gap-1.5 text-sm">
            <icons.BarChart3 className={iconSize.sm} />
            反馈统计
          </TabsTrigger>
        </TabsList>

        {/* ===== Tab 1: 对话摘要 ===== */}
        <TabsContent value="summaries" className="space-y-4">
          <Input
            className={`${inputStyle.search} max-w-md`}
            placeholder="搜索对话摘要..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />

          <div className="space-y-3">
            {filteredSummaries.map(conv => {
              const isExpanded = expandedId === conv.id
              const sentCfg = sentimentConfig[conv.sentiment]
              const date = conv.created_at?.slice(0, 10) || '—'
              const title = conv.key_topics?.[0]
                ? `${conv.key_topics[0]}咨询摘要`
                : `对话摘要 ${conv.conversation_id?.slice(0, 8) || conv.id.slice(0, 8)}`
              const todos = conv.action_items || []
              const topics = conv.key_topics || []
              const legalDomains = conv.legal_domains || []
              return (
                <div key={conv.id} className={cardStyle.base}>
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : conv.id)}
                    className="w-full text-left"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${sentCfg.color}`} title={sentCfg.label} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className={heading.card}>{title}</p>
                          <span className={heading.micro}>{date}</span>
                          {todos.length > 0 && (
                            <Badge variant="secondary" className="text-xs">
                              <icons.Tasks className="w-3 h-3 mr-1" />
                              {todos.length}
                            </Badge>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {topics.map(topic => (
                            <Badge key={topic} variant="outline" className="text-xs">{topic}</Badge>
                          ))}
                        </div>
                        <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{conv.summary}</p>
                      </div>
                      <icons.ChevronDown
                        className={`${iconSize.sm} text-muted-foreground shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      />
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-border space-y-3 ml-5.5">
                      <div>
                        <p className={heading.card + ' mb-1'}>完整摘要</p>
                        <p className="text-sm text-foreground/80 leading-relaxed">{conv.summary}</p>
                      </div>
                      {todos.length > 0 && (
                        <div>
                          <p className={heading.card + ' mb-1'}>待办事项</p>
                          <ul className="space-y-1">
                            {todos.map((todo, i) => (
                              <li key={i} className="flex items-center gap-2 text-sm text-foreground/80">
                                <icons.Circle className="w-3 h-3 text-muted-foreground shrink-0" />
                                {todo}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1">
                        {legalDomains.map(domain => (
                          <Badge key={domain} className={statusBadge.info + ' text-xs'}>{domain}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}

            {filteredSummaries.length === 0 && (
              <div className={`${cardStyle.base} text-center py-12`}>
                <icons.Search className={`${iconSize.xl} text-muted-foreground mx-auto mb-3`} />
                <p className={heading.muted}>未找到匹配的对话摘要</p>
              </div>
            )}
          </div>
        </TabsContent>

        {/* ===== Tab 2: 反馈统计 ===== */}
        <TabsContent value="feedback" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 评分分布 */}
            <div className={cardStyle.base}>
              <PageSection title="评分分布">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={ratingDistribution}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="rating" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      />
                      <Bar dataKey="count" name="次数" fill={chartColors[0]} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </PageSection>
            </div>

            {/* 反馈类型分布 */}
            <div className={cardStyle.base}>
              <PageSection title="反馈类型分布">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={feedbackTypes}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={90}
                        paddingAngle={3}
                        dataKey="value"
                        nameKey="name"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {feedbackTypes.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </PageSection>
            </div>
          </div>

          {/* 满意度趋势 */}
          <div className={cardStyle.base}>
            <PageSection title="满意度趋势（近30天）">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={satisfactionTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={4} />
                    <YAxis domain={[3, 5]} tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="满意度"
                      stroke={chartColors[0]}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </PageSection>
          </div>

          {/* 反馈类型明细 */}
          <div className={cardStyle.base}>
            <PageSection title="反馈类型明细">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[160px]">反馈类型</TableHead>
                      <TableHead className="w-[120px]">数量</TableHead>
                      <TableHead>占比</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {feedbackTypes.length > 0 ? (
                      feedbackTypes.map(type => (
                        <TableRow key={type.key}>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">{type.name}</Badge>
                          </TableCell>
                          <TableCell className="text-sm text-foreground/80">{type.value}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {feedbackStats && feedbackStats.total_feedbacks > 0
                              ? `${((type.value / feedbackStats.total_feedbacks) * 100).toFixed(1)}%`
                              : '0%'}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                          暂无反馈统计数据
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </PageSection>
          </div>
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
