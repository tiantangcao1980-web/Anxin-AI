/**
 * RevenueReport - 收入报表看板
 *
 * - KPI 卡片行(4个): 总收入、已收款、待收款、平均客单价
 * - 月度收入趋势 LineChart
 * - 收入来源分布 PieChart（按案件类型）
 * - 律师业绩排行 Table
 * 全部 mock 数据，使用 recharts + design-tokens
 */

import { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { icons } from '@/lib/icons'
import { cardStyle, heading, iconSize, chartColors, statusBadge } from '@/lib/design-tokens'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { billingApi } from '@/lib/api'

// 数据类型定义
interface RevenueKpi {
  totalRevenue: number
  paidAmount: number
  pendingAmount: number
  avgOrderValue: number
}

interface MonthlyPoint {
  month: string
  amount: number
}

interface SourcePoint {
  name: string
  value: number
}

interface LawyerRankItem {
  rank: number
  name: string
  hours: number
  revenue: number
  cases: number
}

// ========== 工具函数 ==========

function formatCurrency(value: number): string {
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}万`
  }
  return value.toLocaleString()
}

// ========== KPI 卡片 ==========

interface KpiCardProps {
  icon: React.ReactNode
  label: string
  value: string
  sub?: string
  colorClass?: string
}

function KpiCard({ icon, label, value, sub, colorClass = 'text-foreground' }: KpiCardProps) {
  return (
    <div className={cardStyle.base}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className={heading.muted}>{label}</span>
      </div>
      <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

// ========== 组件 ==========

export default function RevenueReport() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [kpiData, setKpiData] = useState<RevenueKpi>({ totalRevenue: 0, paidAmount: 0, pendingAmount: 0, avgOrderValue: 0 })
  const [monthlyData, setMonthlyData] = useState<MonthlyPoint[]>([])
  const [sourceData, setSourceData] = useState<SourcePoint[]>([])
  const [lawyerRanking, setLawyerRanking] = useState<LawyerRankItem[]>([])

  useEffect(() => {
    let cancelled = false
    async function fetchReport() {
      try {
        setLoading(true)
        setError(null)
        const data = await billingApi.getRevenueReport()
        if (cancelled) return
        // 适配后端字段
        setKpiData({
          totalRevenue: data.total_revenue ?? data.totalRevenue ?? 0,
          paidAmount: data.paid_amount ?? data.paidAmount ?? 0,
          pendingAmount: data.pending_amount ?? data.pendingAmount ?? 0,
          avgOrderValue: data.avg_order_value ?? data.avgOrderValue ?? 0,
        })
        setMonthlyData(
          (data.monthly_data ?? data.monthly ?? []).map((m: any) => ({
            month: m.month,
            amount: m.amount ?? m.revenue ?? 0,
          }))
        )
        setSourceData(
          (data.source_data ?? data.sources ?? data.by_category ?? []).map((s: any) => ({
            name: s.name ?? s.category ?? '',
            value: s.value ?? s.amount ?? 0,
          }))
        )
        setLawyerRanking(
          (data.lawyer_ranking ?? data.rankings ?? []).map((r: any, idx: number) => ({
            rank: r.rank ?? idx + 1,
            name: r.name ?? '',
            hours: r.hours ?? 0,
            revenue: r.revenue ?? 0,
            cases: r.cases ?? r.case_count ?? 0,
          }))
        )
      } catch (err: any) {
        if (!cancelled) setError(err.message || '加载收入报表失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchReport()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    )
  }

  if (error) {
    return (
      <div className={`${cardStyle.base} flex flex-col items-center justify-center py-12`}>
        <icons.AlertTriangle className={`${iconSize.xl} text-destructive/60 mb-3`} />
        <p className="text-sm text-muted-foreground mb-3">{error}</p>
        <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
          重试
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* KPI 卡片行 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon={<icons.DollarSign className={`${iconSize.md} text-primary`} />}
          label="总收入"
          value={`${formatCurrency(kpiData.totalRevenue)}元`}
          sub="本年累计"
          colorClass="text-foreground"
        />
        <KpiCard
          icon={<icons.CheckCircle className={`${iconSize.md} text-emerald-600 dark:text-emerald-400`} />}
          label="已收款"
          value={`${formatCurrency(kpiData.paidAmount)}元`}
          sub={`回款率 ${kpiData.totalRevenue > 0 ? ((kpiData.paidAmount / kpiData.totalRevenue) * 100).toFixed(0) : 0}%`}
          colorClass="text-emerald-600 dark:text-emerald-400"
        />
        <KpiCard
          icon={<icons.Clock className={`${iconSize.md} text-amber-600 dark:text-amber-400`} />}
          label="待收款"
          value={`${formatCurrency(kpiData.pendingAmount)}元`}
          sub="含已发送和逾期"
          colorClass="text-amber-600 dark:text-amber-400"
        />
        <KpiCard
          icon={<icons.TrendingUp className={`${iconSize.md} text-primary`} />}
          label="平均客单价"
          value={`${formatCurrency(kpiData.avgOrderValue)}元`}
          colorClass="text-primary"
        />
      </div>

      {/* 图表行 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 月度收入趋势 */}
        <div className={`${cardStyle.base} lg:col-span-2`}>
          <h3 className={`${heading.section} mb-4`}>月度收入趋势</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                tickFormatter={v => `${(v / 10000).toFixed(0)}万`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '13px',
                }}
                formatter={(value: number) => [`${formatCurrency(value)}元`, '收入']}
              />
              <Line
                type="monotone"
                dataKey="amount"
                stroke={chartColors[0]}
                strokeWidth={2}
                dot={{ r: 4, fill: chartColors[0] }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 收入来源分布 */}
        <div className={cardStyle.base}>
          <h3 className={`${heading.section} mb-4`}>收入来源分布</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={sourceData}
                cx="50%"
                cy="45%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={{ strokeWidth: 1 }}
              >
                {sourceData.map((_, idx) => (
                  <Cell key={idx} fill={chartColors[idx % chartColors.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '13px',
                }}
                formatter={(value: number) => [`${formatCurrency(value)}元`, '收入']}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 律师业绩排行 */}
      <div className={cardStyle.base}>
        <h3 className={`${heading.section} mb-4`}>律师业绩排行</h3>
        {lawyerRanking.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">暂无排行数据</p>
        ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">排名</TableHead>
              <TableHead>律师</TableHead>
              <TableHead className="text-right">工时 (h)</TableHead>
              <TableHead className="text-right">收入</TableHead>
              <TableHead className="text-right">案件数</TableHead>
              <TableHead className="text-right">时均产出</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {lawyerRanking.map(row => {
              const hourlyRate = row.hours > 0 ? Math.round(row.revenue / row.hours) : 0
              return (
                <TableRow key={row.rank}>
                  <TableCell>
                    {row.rank <= 3 ? (
                      <Badge
                        variant="outline"
                        className={`text-xs px-1.5 py-0 ${
                          row.rank === 1
                            ? statusBadge.warning
                            : row.rank === 2
                              ? statusBadge.neutral
                              : statusBadge.info
                        }`}
                      >
                        {row.rank === 1 ? '🥇' : row.rank === 2 ? '🥈' : '🥉'}
                      </Badge>
                    ) : (
                      <span className="text-sm text-muted-foreground ml-2">{row.rank}</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium text-primary">
                        {row.name.slice(0, 1)}
                      </div>
                      <span className="text-sm font-medium text-foreground">{row.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right text-sm">{row.hours}</TableCell>
                  <TableCell className="text-right text-sm font-medium text-foreground">
                    {formatCurrency(row.revenue)}元
                  </TableCell>
                  <TableCell className="text-right text-sm">{row.cases}</TableCell>
                  <TableCell className="text-right text-sm text-muted-foreground">
                    {hourlyRate}元/h
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        )}
      </div>
    </div>
  )
}
