/**
 * AcquisitionDashboard - 获客数据看板
 *
 * 展示线索漏斗、趋势图、来源分布、律师业绩排行等获客指标。
 * 数据来源：acquisitionApi
 */

import { useState, useEffect } from'react'
import { PageContainer } from'@/components/ui/PageContainer'
import { Skeleton } from'@/components/ui/skeleton'
import { cardStyle, heading, statusBadge, chartColors, iconSize } from'@/lib/design-tokens'
import { StatCard, StatGrid, StatCardSkeleton } from'@/components/ui-unified'
import { icons } from'@/lib/icons'
import { acquisitionApi } from'@/lib/api'
import {
 BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
 LineChart, Line, CartesianGrid, Legend,
 PieChart, Pie,
} from'recharts'

// ===== 类型定义 =====

interface KPICard {
 label: string
 value: string | number
 change: string
 trend:'up' |'down' |'flat'
 icon: React.ComponentType<{ className?: string }>
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
 const [error, setError] = useState<string | null>(null)

 const [kpis, setKpis] = useState<KPICard[]>([])
 const [funnel, setFunnel] = useState<FunnelItem[]>([])
 const [trend, setTrend] = useState<TrendItem[]>([])
 const [sources, setSources] = useState<SourceItem[]>([])
 const [lawyerPerformance, setLawyerPerformance] = useState<LawyerPerformance[]>([])

 useEffect(() => {
 let cancelled = false
 async function fetchData() {
 setLoading(true)
 setError(null)
 try {
 const [funnelData, sourcesData, performanceData, conversionData] = await Promise.all([
 acquisitionApi.getFunnel(),
 acquisitionApi.getSources(),
 acquisitionApi.getLawyerPerformance({ limit: 10 }),
 acquisitionApi.getConversionRates(),
 ])
 if (cancelled) return

 // 漏斗数据
 if (Array.isArray(funnelData)) {
 setFunnel(funnelData)
 } else if (funnelData?.stages) {
 setFunnel(funnelData.stages)
 } else {
 setFunnel([])
 }

 // 来源数据
 if (Array.isArray(sourcesData)) {
 setSources(sourcesData)
 } else if (sourcesData?.sources) {
 setSources(sourcesData.sources)
 } else {
 setSources([])
 }

 // 律师业绩
 if (Array.isArray(performanceData)) {
 setLawyerPerformance(performanceData)
 } else if (performanceData?.lawyers) {
 setLawyerPerformance(performanceData.lawyers)
 } else {
 setLawyerPerformance([])
 }

 // 从 conversion 接口提取 KPI 和趋势数据
 if (conversionData) {
 // KPI 卡片
 const kpiCards: KPICard[] = [
 {
 label:'总线索数',
 value: conversionData.total_leads ?? conversionData.totalLeads ?? 0,
 change: conversionData.leads_change ?? conversionData.leadsChange ??'--',
 trend: (conversionData.leads_trend ?? conversionData.leadsTrend ??'flat') as'up' |'down' |'flat',
 icon: icons.Users,
 },
 {
 label:'本月新增',
 value: conversionData.new_leads ?? conversionData.newLeads ?? 0,
 change: conversionData.new_leads_change ?? conversionData.newLeadsChange ??'--',
 trend: (conversionData.new_leads_trend ?? conversionData.newLeadsTrend ??'flat') as'up' |'down' |'flat',
 icon: icons.Plus,
 },
 {
 label:'转化率',
 value: conversionData.conversion_rate ?? conversionData.conversionRate ??'0%',
 change: conversionData.conversion_change ?? conversionData.conversionChange ??'--',
 trend: (conversionData.conversion_trend ?? conversionData.conversionTrend ??'flat') as'up' |'down' |'flat',
 icon: icons.TrendingUp,
 },
 {
 label:'活跃律师',
 value: conversionData.active_lawyers ?? conversionData.activeLawyers ?? 0,
 change: conversionData.lawyers_change ?? conversionData.lawyersChange ??'--',
 trend: (conversionData.lawyers_trend ?? conversionData.lawyersTrend ??'flat') as'up' |'down' |'flat',
 icon: icons.Briefcase,
 },
 ]
 setKpis(kpiCards)

 // 趋势数据
 if (Array.isArray(conversionData.trend)) {
 setTrend(conversionData.trend)
 } else if (Array.isArray(conversionData.daily_trend)) {
 setTrend(conversionData.daily_trend)
 } else {
 setTrend([])
 }
 }
 } catch (err: any) {
 if (!cancelled) {
 console.error('获客数据加载失败:', err)
 setError(err?.message ||'数据加载失败，请稍后重试')
 }
 } finally {
 if (!cancelled) setLoading(false)
 }
 }
 fetchData()
 return () => { cancelled = true }
 }, [timeRange])

 if (error) {
 return (
 <PageContainer title="获客分析" description="线索转化与业绩追踪">
 <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
 <icons.AlertCircle className={`${iconSize.xl} text-destructive mb-3`} />
 <p className={heading.section}>加载失败</p>
 <p className="text-sm text-muted-foreground mt-1">{error}</p>
 <button
 onClick={() => setLoading(true)}
 className="mt-4 px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
 >
 重试
 </button>
 </div>
 </PageContainer>
 )
 }

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
 ?'bg-primary text-primary-foreground'
 :'bg-muted text-muted-foreground hover:text-foreground'
 }`}
 >
 {d === 7 ?'7天' : d === 30 ?'30天' :'90天'}
 </button>
 ))}
 </div>
 }
 >
 {loading ? (
 <div className="space-y-4">
 <StatCardSkeleton count={4} />
 {/* 图表骨架 */}
 <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
 <div className={cardStyle.base}>
 <Skeleton className="h-5 w-24 mb-4" />
 <Skeleton className="h-64 w-full rounded-dd_lg" />
 </div>
 <div className={cardStyle.base}>
 <Skeleton className="h-5 w-32 mb-4" />
 <Skeleton className="h-64 w-full rounded-dd_lg" />
 </div>
 </div>
 </div>
 ) : (
 <>
 {/* KPI 卡片行 — 接入 StatGrid，自动获得 tone 色调 / 趋势徽章 / 错峰入场 */}
 {kpis.length > 0 ? (
 <StatGrid cols={4}>
 {kpis.map((kpi, index) => (
 <StatCard
 key={kpi.label}
 index={index}
 icon={kpi.icon}
 tone="primary"
 label={kpi.label}
 value={kpi.value}
 trend={kpi.trend === 'up' ? 'up' : kpi.trend === 'down' ? 'down' : 'flat'}
 trendValue={kpi.change}
 hint="较上期"
 />
 ))}
 </StatGrid>
 ) : (
 <div className={`${cardStyle.base} text-center py-8`}>
 <p className="text-sm text-muted-foreground">暂无 KPI 数据</p>
 </div>
 )}

 {/* 漏斗图 + 趋势图 */}
 <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
 {/* 漏斗图 */}
 <div className={cardStyle.base}>
 <h3 className={heading.section}>线索漏斗</h3>
 {funnel.length > 0 ? (
 <div className="h-64 mt-4">
 <ResponsiveContainer width="100%" height="100%">
 <BarChart
 data={funnel.filter((f) => f.stage !=='lost')}
 layout="vertical"
 margin={{ left: 20, right: 20, top: 5, bottom: 5 }}
 >
 <XAxis type="number" hide />
 <YAxis type="category" dataKey="label" width={60} tick={{ fontSize: 12 }} />
 <Tooltip
 formatter={(value: number) => [`${value} 条`,'数量']}
 contentStyle={{ borderRadius: 8, border:'1px solid var(--border)' }}
 />
 <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={28}>
 {funnel.filter((f) => f.stage !=='lost').map((_, idx) => (
 <Cell key={idx} fill={chartColors[idx % chartColors.length]} />
 ))}
 </Bar>
 </BarChart>
 </ResponsiveContainer>
 </div>
 ) : (
 <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">暂无漏斗数据</div>
 )}
 </div>

 {/* 趋势图 */}
 <div className={cardStyle.base}>
 <h3 className={heading.section}>线索趋势（近 {timeRange} 天）</h3>
 {trend.length > 0 ? (
 <div className="h-64 mt-4">
 <ResponsiveContainer width="100%" height="100%">
 <LineChart data={trend} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
 <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
 <XAxis
 dataKey="date"
 tick={{ fontSize: 11 }}
 interval={Math.floor(trend.length / 6)}
 />
 <YAxis tick={{ fontSize: 11 }} width={30} />
 <Tooltip
 contentStyle={{ borderRadius: 8, border:'1px solid var(--border)' }}
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
 ) : (
 <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">暂无趋势数据</div>
 )}
 </div>
 </div>

 {/* 来源分布 + 律师业绩 */}
 <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
 {/* 来源分布饼图 */}
 <div className={cardStyle.base}>
 <h3 className={heading.section}>来源分布</h3>
 {sources.length > 0 ? (
 <>
 <div className="h-64 mt-4">
 <ResponsiveContainer width="100%" height="100%">
 <PieChart>
 <Pie
 data={sources}
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
 {sources.map((_, idx) => (
 <Cell key={idx} fill={chartColors[idx % chartColors.length]} />
 ))}
 </Pie>
 <Tooltip
 formatter={(value: number, name: string) => [`${value} 条`, name]}
 contentStyle={{ borderRadius: 8, border:'1px solid var(--border)' }}
 />
 </PieChart>
 </ResponsiveContainer>
 </div>
 {/* 图例 */}
 <div className="flex flex-wrap gap-3 mt-2">
 {sources.map((s, idx) => (
 <div key={s.source} className="flex items-center gap-1.5 text-xs text-muted-foreground">
 <span
 className="w-2.5 h-2.5 rounded-sm shrink-0"
 style={{ backgroundColor: chartColors[idx % chartColors.length] }}
 />
 {s.source}
 </div>
 ))}
 </div>
 </>
 ) : (
 <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">暂无来源数据</div>
 )}
 </div>

 {/* 律师业绩排行 */}
 <div className={`${cardStyle.base} lg:col-span-2`}>
 <h3 className={heading.section}>律师业绩排行 TOP 10</h3>
 {lawyerPerformance.length > 0 ? (
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
 {lawyerPerformance.map((lp, idx) => (
 <tr key={lp.rank || idx} className="border-b border-border/50 last:border-b-0 hover:bg-muted/30 transition-colors">
 <td className="py-2.5 px-2">
 <span
 className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
 (lp.rank || idx + 1) <= 3
 ?'bg-primary/10 text-primary'
 :'bg-muted text-muted-foreground'
 }`}
 >
 {lp.rank || idx + 1}
 </span>
 </td>
 <td className="py-2.5 px-2 font-medium text-foreground">{lp.lawyer_name}</td>
 <td className="py-2.5 px-2 text-muted-foreground hidden sm:table-cell">{lp.law_firm}</td>
 <td className="py-2.5 px-2 text-right text-foreground">{lp.total_consultations}</td>
 <td className="py-2.5 px-2 text-right text-foreground">{lp.total_delegations}</td>
 <td className="py-2.5 px-2 text-right font-medium text-foreground">{formatCurrency(lp.revenue)}</td>
 <td className="py-2.5 px-2 text-right">
 <span className="inline-flex items-center gap-0.5">
 <icons.Star className="w-3 h-3 text-warning fill-amber-400" />
 <span className="text-foreground">{lp.avg_rating}</span>
 </span>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 ) : (
 <div className="mt-4 py-12 text-center text-sm text-muted-foreground">暂无律师业绩数据</div>
 )}
 </div>
 </div>
 </>
 )}
 </PageContainer>
 )
}
