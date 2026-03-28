/**
 * AcquisitionDashboard - 获客数据看板
 *
 * 展示线索漏斗、趋势图、来源分布、律师业绩排行等获客指标。
 * 当前使用 mock 数据，后续接入 API。
 */

import { useState, useEffect } from 'react'
import { PageContainer } from '@/components/ui/PageContainer'
import { Skeleton } from '@/components/ui/skeleton'
import { cardStyle, heading, statusBadge, chartColors, iconSize } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, CartesianGrid, Legend,
  PieChart, Pie,
} from 'recharts'

// ===== 类型定义 =====

interface KPICard {
  label: string
  value: string | number
  change: string
  trend: 'up' | 'down' | 'flat'
  icon: React.ElementType
}

interface FunnelItem {
  stage: string
  label: string
  count: number
}

interface TrendItem {
  date: string
  count: number
}

interface SourceItem {
  source: string
  count: number
}

interface LawyerPerformance {
  rank: number
  lawyer_name: string
  law_firm: string
  total_consultations: number
  total_delegations: number
  revenue: number
  avg_rating: number
}

// @mock-data FALLBACK: 后端就绪后从 /acquisition/* API 获取

const mockKPIs: KPICard[] = [
  {
    label: '总线索数',
    value: 1280,
    change: '+12.5%',
    trend: 'up',
    icon: icons.Users,
  },
  {
    label: '本月新增',
    value: 186,
    change: '+8.3%',
    trend: 'up',
    icon: icons.Plus,
  },
  {
    label: '转化率',
    value: '23.4%',
    change: '+2.1%',
    trend: 'up',
    icon: icons.TrendingUp,
  },
  {
    label: '活跃律师',
    value: 42,
    change: '-3',
    trend: 'down',
    icon: icons.Briefcase,
  },
]

const mockFunnel: FunnelItem[] = [
  { stage: 'new', label: '新线索', count: 186 },
  { stage: 'contacted', label: '已联系', count: 142 },
  { stage: 'qualified', label: '已评估', count: 98 },
  { stage: 'proposal', label: '方案中', count: 65 },
  { stage: 'won', label: '已成交', count: 43 },
  { stage: 'lost', label: '已流失', count: 21 },
]

const mockTrend: TrendItem[] = Array.from({ length: 30 }, (_, i) => {
  const d = new Date()
  d.setDate(d.getDate() - (29 - i))
  return {
    date: `${d.getMonth() + 1}/${d.getDate()}`,
    count: Math.floor(Math.random() * 12) + 3,
  }
})

const mockSources: SourceItem[] = [
  { source: '线上咨询', count: 68 },
  { source: '转介绍', count: 45 },
  { source: '主动拓展', count: 32 },
  { source: '电话咨询', count: 24 },
  { source: '合作渠道', count: 17 },
]

const mockLawyerPerformance: LawyerPerformance[] = [
  { rank: 1, lawyer_name: '张明', law_firm: '北京盈科', total_consultations: 58, total_delegations: 23, revenue: 184000, avg_rating: 4.9 },
  { rank: 2, lawyer_name: '李婷', law_firm: '金杜律所', total_consultations: 52, total_delegations: 20, revenue: 168000, avg_rating: 4.8 },
  { rank: 3, lawyer_name: '王强', law_firm: '中伦律所', total_consultations: 45, total_delegations: 18, revenue: 152000, avg_rating: 4.7 },
  { rank: 4, lawyer_name: '陈晓', law_firm: '德恒律所', total_consultations: 41, total_delegations: 15, revenue: 128000, avg_rating: 4.8 },
  { rank: 5, lawyer_name: '赵丽', law_firm: '大成律所', total_consultations: 38, total_delegations: 14, revenue: 112000, avg_rating: 4.6 },
  { rank: 6, lawyer_name: '刘伟', law_firm: '锦天城', total_consultations: 35, total_delegations: 12, revenue: 96000, avg_rating: 4.5 },
  { rank: 7, lawyer_name: '周敏', law_firm: '国浩律所', total_consultations: 32, total_delegations: 11, revenue: 88000, avg_rating: 4.7 },
  { rank: 8, lawyer_name: '吴芳', law_firm: '君合律所', total_consultations: 28, total_delegations: 10, revenue: 80000, avg_rating: 4.4 },
  { rank: 9, lawyer_name: '孙杰', law_firm: '通商律所', total_consultations: 25, total_delegations: 9, revenue: 72000, avg_rating: 4.5 },
  { rank: 10, lawyer_name: '郑华', law_firm: '海问律所', total_consultations: 22, total_delegations: 8, revenue: 64000, avg_rating: 4.3 },
]

// ===== 辅助函数 =====

function formatCurrency(amount: number): string {
  if (amount >= 10000) {
    return `${(amount / 10000).toFixed(1)}万`
  }
  return amount.toLocaleString()
}

// ===== 主组件 =====

export default function AcquisitionDashboard() {
  const [timeRange, setTimeRange] = useState<number>(30)
  const [loading, setLoading] = useState(true)

  // 模拟加载
  useEffect(() => {
    setLoading(true)
    const timer = setTimeout(() => setLoading(false), 300)
    return () => clearTimeout(timer)
  }, [timeRange])

  // TODO: 接入 API
  // const { data: funnel } = useSWR(`/acquisition/funnel?days=${timeRange}`, fetcher)
  // const { data: sources } = useSWR(`/acquisition/sources?days=${timeRange}`, fetcher)
  // const { data: performance } = useSWR(`/acquisition/lawyer-performance?days=${timeRange}`, fetcher)

  return (
    <PageContainer
      title="获客分析"
      description="线索转化与业绩追踪"
      actions={
        <div className="flex items-center gap-2">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setTimeRange(d)}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                timeRange === d
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              {d === 7 ? '7天' : d === 30 ? '30天' : '90天'}
            </button>
          ))}
        </div>
      }
    >
      {loading ? (
        <div className="space-y-4">
          {/* KPI 骨架 */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className={cardStyle.base}>
                <div className="flex items-center justify-between mb-3">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-5 w-5 rounded" />
                </div>
                <Skeleton className="h-8 w-20 mb-2" />
                <Skeleton className="h-3 w-24" />
              </div>
            ))}
          </div>
          {/* 图表骨架 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className={cardStyle.base}>
              <Skeleton className="h-5 w-24 mb-4" />
              <Skeleton className="h-64 w-full rounded-lg" />
            </div>
            <div className={cardStyle.base}>
              <Skeleton className="h-5 w-32 mb-4" />
              <Skeleton className="h-64 w-full rounded-lg" />
            </div>
          </div>
        </div>
      ) : (
      <>
      {/* KPI 卡片行 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {mockKPIs.map((kpi) => (
          <div key={kpi.label} className={cardStyle.base}>
            <div className="flex items-center justify-between">
              <p className={heading.micro}>{kpi.label}</p>
              <kpi.icon className={`${iconSize.md} text-muted-foreground`} />
            </div>
            <p className="text-2xl font-bold text-foreground mt-2">{kpi.value}</p>
            <p
              className={`text-xs mt-1 ${
                kpi.trend === 'up'
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : kpi.trend === 'down'
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-muted-foreground'
              }`}
            >
              {kpi.change} 较上期
            </p>
          </div>
        ))}
      </div>

      {/* 漏斗图 + 趋势图 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 漏斗图 */}
        <div className={cardStyle.base}>
          <h3 className={heading.section}>线索漏斗</h3>
          <div className="h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={mockFunnel.filter((f) => f.stage !== 'lost')}
                layout="vertical"
                margin={{ left: 20, right: 20, top: 5, bottom: 5 }}
              >
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="label" width={60} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value: number) => [`${value} 条`, '数量']}
                  contentStyle={{ borderRadius: 8, border: '1px solid var(--border)' }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={28}>
                  {mockFunnel.filter((f) => f.stage !== 'lost').map((_, idx) => (
                    <Cell key={idx} fill={chartColors[idx % chartColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 趋势图 */}
        <div className={cardStyle.base}>
          <h3 className={heading.section}>线索趋势（近 {timeRange} 天）</h3>
          <div className="h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockTrend} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  interval={Math.floor(mockTrend.length / 6)}
                />
                <YAxis tick={{ fontSize: 11 }} width={30} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid var(--border)' }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke={chartColors[0]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  name="线索数"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 来源分布 + 律师业绩 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 来源分布饼图 */}
        <div className={cardStyle.base}>
          <h3 className={heading.section}>来源分布</h3>
          <div className="h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={mockSources}
                  dataKey="count"
                  nameKey="source"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  innerRadius={40}
                  paddingAngle={2}
                  label={({ source, percent }) =>
                    `${source} ${(percent * 100).toFixed(0)}%`
                  }
                  labelLine={{ strokeWidth: 1 }}
                >
                  {mockSources.map((_, idx) => (
                    <Cell key={idx} fill={chartColors[idx % chartColors.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number, name: string) => [`${value} 条`, name]}
                  contentStyle={{ borderRadius: 8, border: '1px solid var(--border)' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          {/* 图例 */}
          <div className="flex flex-wrap gap-3 mt-2">
            {mockSources.map((s, idx) => (
              <div key={s.source} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ backgroundColor: chartColors[idx % chartColors.length] }}
                />
                {s.source}
              </div>
            ))}
          </div>
        </div>

        {/* 律师业绩排行 */}
        <div className={`${cardStyle.base} lg:col-span-2`}>
          <h3 className={heading.section}>律师业绩排行 TOP 10</h3>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">排名</th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">律师</th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground hidden sm:table-cell">律所</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">咨询</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">委托</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">收入</th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">评分</th>
                </tr>
              </thead>
              <tbody>
                {mockLawyerPerformance.map((lp) => (
                  <tr key={lp.rank} className="border-b border-border/50 last:border-b-0 hover:bg-muted/30 transition-colors">
                    <td className="py-2.5 px-2">
                      <span
                        className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                          lp.rank <= 3
                            ? 'bg-primary/10 text-primary'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {lp.rank}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 font-medium text-foreground">{lp.lawyer_name}</td>
                    <td className="py-2.5 px-2 text-muted-foreground hidden sm:table-cell">{lp.law_firm}</td>
                    <td className="py-2.5 px-2 text-right text-foreground">{lp.total_consultations}</td>
                    <td className="py-2.5 px-2 text-right text-foreground">{lp.total_delegations}</td>
                    <td className="py-2.5 px-2 text-right font-medium text-foreground">{formatCurrency(lp.revenue)}</td>
                    <td className="py-2.5 px-2 text-right">
                      <span className="inline-flex items-center gap-0.5">
                        <icons.Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                        <span className="text-foreground">{lp.avg_rating}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      </>
      )}
    </PageContainer>
  )
}
