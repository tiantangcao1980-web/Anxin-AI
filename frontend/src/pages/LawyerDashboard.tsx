/**
 * LawyerDashboard - 律师工作台
 *
 * KPI 卡片 + 待处理咨询 + 收入/评分趋势图 + 快捷入口
 * 使用 PageContainer + design-tokens + recharts
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { lawyerApi } from '@/lib/api'
import { cardStyle, buttonStyle, heading, statusBadge, iconSize, chartColors } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

// ============ 类型定义 ============

interface KpiData {
  monthlyIncome: number
  monthlyOrders: number
  rating: number
  avgResponseMinutes: number
}

interface PendingConsultation {
  id: string
  summary: string
  field: string
  urgency: 'high' | 'medium' | 'low'
  createdAt: string
  clientName: string
}

interface TrendPoint {
  month: string
  income: number
  rating: number
}

const URGENCY_MAP: Record<string, { label: string; badge: string }> = {
  high: { label: '紧急', badge: statusBadge.error },
  medium: { label: '一般', badge: statusBadge.warning },
  low: { label: '普通', badge: statusBadge.neutral },
}

// ============ 主组件 ============

export default function LawyerDashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [kpi, setKpi] = useState<KpiData>({ monthlyIncome: 0, monthlyOrders: 0, rating: 0, avgResponseMinutes: 0 })
  const [pending, setPending] = useState<PendingConsultation[]>([])
  const [trend, setTrend] = useState<TrendPoint[]>([])

  useEffect(() => {
    let cancelled = false
    async function fetchDashboard() {
      try {
        setLoading(true)
        setError(null)
        const data = await lawyerApi.getDashboard()
        if (cancelled) return
        // 适配后端返回的字段名
        setKpi({
          monthlyIncome: data.monthly_income ?? data.monthlyIncome ?? 0,
          monthlyOrders: data.monthly_orders ?? data.monthlyOrders ?? 0,
          rating: data.rating ?? 0,
          avgResponseMinutes: data.avg_response_minutes ?? data.avgResponseMinutes ?? 0,
        })
        setPending(
          (data.pending_consultations ?? data.pending ?? []).map((c: any) => ({
            id: c.id,
            summary: c.summary,
            field: c.field ?? c.category ?? '',
            urgency: c.urgency ?? 'medium',
            createdAt: c.created_at ?? c.createdAt ?? '',
            clientName: c.client_name ?? c.clientName ?? '',
          }))
        )
        setTrend(
          (data.trend ?? data.income_trend ?? []).map((t: any) => ({
            month: t.month,
            income: t.income ?? t.amount ?? 0,
            rating: t.rating ?? 0,
          }))
        )
      } catch (err: any) {
        if (!cancelled) setError(err.message || '加载仪表板数据失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchDashboard()
    return () => { cancelled = true }
  }, [])

  function handleAccept(id: string) {
    setPending(p => p.filter(c => c.id !== id))
    toast.success('已接单')
  }

  function handleIgnore(id: string) {
    setPending(p => p.filter(c => c.id !== id))
    toast('已忽略')
  }

  if (loading) {
    return (
      <PageContainer title="律师工作台">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl mt-4" />
      </PageContainer>
    )
  }

  if (error) {
    return (
      <PageContainer title="律师工作台">
        <div className={`${cardStyle.flat} flex flex-col items-center justify-center py-12`}>
          <icons.AlertTriangle className={`${iconSize.xl} text-destructive/60 mb-3`} />
          <p className={heading.section}>加载失败</p>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
          <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
            重新加载
          </Button>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="律师工作台" description="查看收入、管理咨询、跟踪业绩">
      {/* KPI 卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon={icons.DollarSign}
          label="本月收入"
          value={`¥${kpi.monthlyIncome.toLocaleString()}`}
          color="text-emerald-600"
          bgColor="bg-emerald-50 dark:bg-emerald-950/30"
        />
        <KpiCard
          icon={icons.Briefcase}
          label="本月接单"
          value={`${kpi.monthlyOrders} 单`}
          color="text-primary"
          bgColor="bg-primary/5"
        />
        <KpiCard
          icon={icons.Star}
          label="综合评分"
          value={`${kpi.rating} ★`}
          color="text-amber-600"
          bgColor="bg-amber-50 dark:bg-amber-950/30"
        />
        <KpiCard
          icon={icons.Clock}
          label="平均回复"
          value={`${kpi.avgResponseMinutes} 分钟`}
          color="text-blue-600"
          bgColor="bg-blue-50 dark:bg-blue-950/30"
        />
      </div>

      {/* 待处理咨询 */}
      <PageSection title="待处理咨询" description={`${pending.length} 条待处理`}>
        {pending.length === 0 ? (
          <div className={`${cardStyle.flat} text-center py-8`}>
            <icons.CheckCircle className={`${iconSize.xl} text-emerald-500 mx-auto mb-2`} />
            <p className={heading.muted}>暂无待处理咨询</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pending.map(item => (
              <div key={item.id} className={cardStyle.base}>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <Badge className={`text-xs px-2 py-0.5 ${URGENCY_MAP[item.urgency].badge}`}>
                    {URGENCY_MAP[item.urgency].label}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{item.createdAt}</span>
                </div>
                <p className="text-sm text-foreground font-medium line-clamp-2 mb-2">{item.summary}</p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="secondary" className="text-xs">{item.field}</Badge>
                    <span>{item.clientName}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="ghost" onClick={() => handleIgnore(item.id)} className="text-xs h-7">
                      忽略
                    </Button>
                    <Button size="sm" onClick={() => handleAccept(item.id)} className="text-xs h-7 gap-1">
                      <icons.Check className={iconSize.xs} />
                      接单
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </PageSection>

      {/* 图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 收入趋势 */}
        <div className={cardStyle.base}>
          <h4 className={`${heading.card} mb-4`}>收入趋势（近 6 月）</h4>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="income"
                name="收入(¥)"
                stroke={chartColors[0]}
                strokeWidth={2}
                dot={{ r: 3, fill: chartColors[0] }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 评分趋势 */}
        <div className={cardStyle.base}>
          <h4 className={`${heading.card} mb-4`}>评分趋势（近 6 月）</h4>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis domain={[4, 5]} tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="rating"
                name="评分"
                stroke={chartColors[2]}
                strokeWidth={2}
                dot={{ r: 3, fill: chartColors[2] }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 快捷入口 */}
      <PageSection title="快捷入口">
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => navigate('/lawyer-onboarding')} className="gap-2">
            <icons.Edit className={iconSize.sm} />
            编辑个人资料
          </Button>
          <Button variant="outline" onClick={() => navigate('/experts')} className="gap-2">
            <icons.Star className={iconSize.sm} />
            查看评价
          </Button>
          <Button variant="outline" onClick={() => navigate('/lawyer-onboarding?step=3')} className="gap-2">
            <icons.Settings className={iconSize.sm} />
            接单设置
          </Button>
        </div>
      </PageSection>
    </PageContainer>
  )
}

// ============ KPI 卡片组件 ============

function KpiCard({
  icon: Icon,
  label,
  value,
  color,
  bgColor,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  color: string
  bgColor: string
}) {
  return (
    <div className={cardStyle.base}>
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${bgColor}`}>
          <Icon className={`${iconSize.md} ${color}`} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-bold text-foreground">{value}</p>
        </div>
      </div>
    </div>
  )
}
