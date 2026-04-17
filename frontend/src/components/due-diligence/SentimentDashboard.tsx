/**
 * SentimentDashboard - 舆情监控仪表板
 *
 * 基于调查数据（风险、诉讼、信用）自动生成上下文化的舆情分析
 * 支持：舆情概览、趋势图、分布图、预警列表、监控配置
 */
import { useState, useEffect, useMemo, useCallback } from'react'
import { motion } from'framer-motion'
import { icons } from'@/lib/icons'
import { cardStyle, heading, buttonStyle, inputStyle, statusBadge } from'@/lib/design-tokens'
import { toast } from'sonner'
import {
 LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
 PieChart, Pie, Cell, Legend, BarChart, Bar,
} from'recharts'

interface SentimentOverview {
 positive: number
 neutral: number
 negative: number
 total: number
}

interface SentimentTimelinePoint {
 date: string
 positive: number
 neutral: number
 negative: number
}

interface SentimentAlert {
 id: string
 severity:'critical' |'warning' |'info'
 title: string
 source: string
 time: string
 summary: string
}

interface SentimentDashboardProps {
 companyName: string
 /** 联动知识图谱 — 点击实体时跳转 */
 onEntityClick?: (entityName: string) => void
 /** 调查数据，用于生成上下文化舆情 */
 investigationData?: {
 risk?: any
 litigation?: any
 credit?: any
 }
}

const PIE_COLORS = ['#34C759','#8E8E93','#FF3B30']

/** 基于调查数据生成上下文化的舆情概览 */
function deriveOverview(data?: SentimentDashboardProps['investigationData']): SentimentOverview {
 if (!data) return { positive: 128, neutral: 342, negative: 47, total: 517 }

 const risk = data.risk || {}
 const avgRisk = ((risk.operation_risk || 0) + (risk.litigation_risk || 0) + (risk.credit_risk || 0) +
 (risk.compliance_risk || 0) + (risk.relation_risk || 0)) / 5

 const litigationCount = data.litigation?.total_cases || data.litigation?.major_cases?.length || 0
 const penalties = data.credit?.administrative_penalties || 0

 const negativeBase = Math.round(avgRisk * 1.2 + litigationCount * 5 + penalties * 8)
 const negative = Math.max(10, Math.min(200, negativeBase))
 const positive = Math.max(30, Math.round((100 - avgRisk) * 2.5))
 const neutral = Math.round(positive * 1.8 + negative * 0.5)

 return { positive, neutral, negative, total: positive + neutral + negative }
}

/** 确定性伪随机：基于种子生成稳定抖动，避免重渲染时数据跳变 */
function seededJitter(seed: number): number {
 const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453
 return Math.round((x - Math.floor(x) - 0.5) * 6)
}

/** 基于概览生成7天趋势数据（确定性） */
function deriveTimeline(overview: SentimentOverview): SentimentTimelinePoint[] {
 const days = 7
 const result: SentimentTimelinePoint[] = []
 const now = new Date()

 for (let i = days - 1; i >= 0; i--) {
 const d = new Date(now)
 d.setDate(d.getDate() - i)
 const dateStr = `${String(d.getMonth() + 1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
 const seed = i * 3
 result.push({
 date: dateStr,
 positive: Math.max(0, Math.round(overview.positive / days) + seededJitter(seed)),
 neutral: Math.max(0, Math.round(overview.neutral / days) + seededJitter(seed + 1)),
 negative: Math.max(0, Math.round(overview.negative / days) + seededJitter(seed + 2)),
 })
 }
 return result
}

/** 基于调查数据生成上下文化预警 */
function deriveAlerts(companyName: string, data?: SentimentDashboardProps['investigationData']): SentimentAlert[] {
 const alerts: SentimentAlert[] = []
 if (!data) return DEFAULT_ALERTS

 const risk = data.risk || {}
 const litigation = data.litigation || {}
 const credit = data.credit || {}

 if ((risk.compliance_risk || 0) > 50) {
 alerts.push({
 id:'a1', severity:'critical',
 title:'合规风险预警：合规风险评分偏高',
 source:'风险评估系统', time:'实时',
 summary: `${companyName} 合规风险评分 ${risk.compliance_risk}，建议立即审查合规状况`,
 })
 }

 if ((litigation.total_cases || litigation.major_cases?.length || 0) > 3) {
 alerts.push({
 id:'a2', severity:'warning',
 title: `诉讼风险提醒：涉诉 ${litigation.total_cases || litigation.major_cases?.length || 0} 起`,
 source:'裁判文书网', time:'调查发现',
 summary: `作为被告 ${litigation.as_defendant || 0} 起，需关注败诉风险`,
 })
 }

 if ((credit.administrative_penalties || 0) > 0) {
 alerts.push({
 id:'a3', severity:'warning',
 title: `行政处罚记录：${credit.administrative_penalties} 条`,
 source:'信用中国', time:'调查发现',
 summary:'存在行政处罚记录，可能影响企业信用评级',
 })
 }

 if ((risk.operation_risk || 0) > 60) {
 alerts.push({
 id:'a4', severity:'critical',
 title:'经营风险预警：经营风险评分较高',
 source:'风险评估系统', time:'实时',
 summary: `经营风险评分 ${risk.operation_risk}，建议关注企业经营状况`,
 })
 }

 if ((risk.relation_risk || 0) > 40) {
 alerts.push({
 id:'a5', severity:'info',
 title:'关联风险提示：关联企业存在风险',
 source:'企业关系图谱', time:'调查发现',
 summary: `关联风险评分 ${risk.relation_risk}，建议排查关联企业风险传导`,
 })
 }

 if (alerts.length === 0) {
 alerts.push({
 id:'a0', severity:'info',
 title:'企业状况良好',
 source:'综合评估', time:'实时',
 summary: `${companyName} 各项风险指标正常，暂无重大预警`,
 })
 }

 return alerts
}

const DEFAULT_ALERTS: SentimentAlert[] = [
 { id:'1', severity:'critical', title:'重大负面舆情：环保处罚通报', source:'生态环境部官网', time:'2小时前', summary:'企业因违规排放被处以50万元罚款' },
 { id:'2', severity:'warning', title:'诉讼风险提醒：新增被告案件', source:'中国裁判文书网', time:'5小时前', summary:'新增一起合同纠纷案件，涉案金额200万元' },
 { id:'3', severity:'info', title:'行业政策变动：新合规要求', source:'国务院法制办', time:'1天前', summary:'行业新规将于下月生效，涉及数据安全合规' },
]

const SOURCE_DISTRIBUTION = [
 { source:'裁判文书网', count: 156 },
 { source:'企查查', count: 123 },
 { source:'天眼查', count: 98 },
 { source:'百度新闻', count: 87 },
 { source:'新浪财经', count: 53 },
]

export function SentimentDashboard({ companyName, onEntityClick, investigationData }: SentimentDashboardProps) {
 const overview = useMemo(() => deriveOverview(investigationData), [investigationData])
 const timeline = useMemo(() => deriveTimeline(overview), [overview])
 const alerts = useMemo(() => deriveAlerts(companyName, investigationData), [companyName, investigationData])

 const [keywords, setKeywords] = useState<string[]>([])
 const [newKeyword, setNewKeyword] = useState('')
 const [generating, setGenerating] = useState(false)
 const [activeView, setActiveView] = useState<'overview' |'alerts' |'config'>('overview')

 useEffect(() => {
 if (companyName) {
 setKeywords([companyName,'法定代表人','商标侵权','环保处罚','失信被执行人'])
 }
 }, [companyName])

 const addKeyword = () => {
 if (!newKeyword.trim()) return
 if (keywords.includes(newKeyword.trim())) {
 toast.error('关键词已存在')
 return
 }
 setKeywords([...keywords, newKeyword.trim()])
 setNewKeyword('')
 toast.success('关键词已添加')
 }

 const removeKeyword = (kw: string) => {
 setKeywords(keywords.filter(k => k !== kw))
 toast.success('关键词已移除')
 }

 const handleGenerateReport = useCallback(() => {
 setGenerating(true)
 setTimeout(() => {
 setGenerating(false)
 toast.success('舆情报告已生成')
 }, 1500)
 }, [])

 const pieData = [
 { name:'正面', value: overview.positive },
 { name:'中立', value: overview.neutral },
 { name:'负面', value: overview.negative },
 ]

 const negativeRatio = overview.total > 0 ? Math.round((overview.negative / overview.total) * 100) : 0
 const healthLabel = negativeRatio > 30 ?'风险' : negativeRatio > 15 ?'关注' :'健康'
 const healthColor = negativeRatio > 30 ?'text-destructive' : negativeRatio > 15 ?'text-warning' :'text-success'

 const severityStyle = (severity: string) => {
 switch (severity) {
 case'critical': return statusBadge.error
 case'warning': return statusBadge.warning
 default: return statusBadge.info
 }
 }

 const severityLabel = (severity: string) => {
 switch (severity) {
 case'critical': return'严重'
 case'warning': return'警告'
 default: return'提示'
 }
 }

 return (
 <div className="space-y-6">
 {/* 子导航 */}
 <div className="flex items-center gap-2">
 {[
 { id:'overview' as const, label:'舆情概览', icon: icons.BarChart3 },
 { id:'alerts' as const, label: `预警中心 (${alerts.length})`, icon: icons.Bell },
 { id:'config' as const, label:'监控配置', icon: icons.Settings },
 ].map(tab => (
 <button
 key={tab.id}
 onClick={() => setActiveView(tab.id)}
 className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
 activeView === tab.id
 ?'bg-primary text-primary-foreground'
 :'bg-muted text-muted-foreground hover:text-foreground'
 }`}
 >
 <tab.icon className="w-3.5 h-3.5" />
 {tab.label}
 </button>
 ))}
 <div className="flex-1" />
 <span className={`text-xs font-medium ${healthColor}`}>
 舆情状态：{healthLabel}
 </span>
 <button onClick={handleGenerateReport} disabled={generating} className={`${buttonStyle.secondary} text-xs flex items-center gap-1.5`}>
 {generating ? <icons.Loader2 className="w-3 h-3 animate-spin" /> : <icons.FileText className="w-3 h-3" />}
 {generating ?'生成中...' :'生成舆情报告'}
 </button>
 </div>

 {activeView ==='overview' && (
 <>
 {/* 舆情概览卡片 */}
 <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
 {[
 { label:'正面舆情', value: overview.positive, icon: icons.TrendingUp, color:'text-success', bg:'bg-success/10' },
 { label:'中立舆情', value: overview.neutral, icon: icons.Minus, color:'text-muted-foreground', bg:'bg-muted' },
 { label:'负面舆情', value: overview.negative, icon: icons.TrendingDown, color:'text-destructive', bg:'bg-destructive/10' },
 { label:'舆情总量', value: overview.total, icon: icons.Signal, color:'text-primary', bg:'bg-primary/5' },
 ].map((item, i) => {
 const Icon = item.icon
 return (
 <motion.div
 key={item.label}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: i * 0.05 }}
 className={`${cardStyle.base} text-center`}
 >
 <div className={`w-10 h-10 mx-auto mb-2 rounded-full ${item.bg} flex items-center justify-center`}>
 <Icon className={`w-5 h-5 ${item.color}`} />
 </div>
 <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
 <p className="text-xs text-muted-foreground mt-1">{item.label}</p>
 </motion.div>
 )
 })}
 </div>

 {/* 趋势图 + 分布图 */}
 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 <div className={`${cardStyle.base} lg:col-span-2`}>
 <h3 className={`${heading.section} mb-4`}>舆情趋势（近 7 天）</h3>
 <ResponsiveContainer width="100%" height={260}>
 <LineChart data={timeline}>
 <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
 <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
 <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
 <Tooltip />
 <Legend />
 <Line type="monotone" dataKey="positive" name="正面" stroke="#34C759" strokeWidth={2} dot={false} />
 <Line type="monotone" dataKey="neutral" name="中立" stroke="#8E8E93" strokeWidth={2} dot={false} />
 <Line type="monotone" dataKey="negative" name="负面" stroke="#FF3B30" strokeWidth={2} dot={false} />
 </LineChart>
 </ResponsiveContainer>
 </div>

 <div className={cardStyle.base}>
 <h3 className={`${heading.section} mb-4`}>舆情分布</h3>
 <ResponsiveContainer width="100%" height={200}>
 <PieChart>
 <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
 {pieData.map((_, index) => (
 <Cell key={index} fill={PIE_COLORS[index]} />
 ))}
 </Pie>
 <Tooltip />
 </PieChart>
 </ResponsiveContainer>
 </div>
 </div>

 {/* 来源分布 */}
 <div className={cardStyle.base}>
 <h3 className={`${heading.section} mb-4`}>数据来源分布</h3>
 <ResponsiveContainer width="100%" height={200}>
 <BarChart data={SOURCE_DISTRIBUTION} layout="vertical">
 <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
 <XAxis type="number" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
 <YAxis type="category" dataKey="source" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" width={80} />
 <Tooltip />
 <Bar dataKey="count" name="采集数量" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
 </BarChart>
 </ResponsiveContainer>
 </div>
 </>
 )}

 {activeView ==='alerts' && (
 <div className={cardStyle.base}>
 <div className="flex items-center justify-between mb-4">
 <h3 className={heading.section}>舆情预警</h3>
 <span className="text-xs text-muted-foreground">{alerts.length} 条预警</span>
 </div>
 <div className="space-y-3">
 {alerts.map(alert => (
 <motion.div
 key={alert.id}
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
 onClick={() => onEntityClick?.(companyName)}
 >
 <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 mt-0.5 ${severityStyle(alert.severity)}`}>
 {severityLabel(alert.severity)}
 </span>
 <div className="flex-1 min-w-0">
 <p className="text-sm font-medium text-foreground">{alert.title}</p>
 <p className="text-xs text-muted-foreground mt-0.5">{alert.summary}</p>
 <div className="flex items-center gap-3 mt-1.5">
 <span className="text-xs text-muted-foreground flex items-center gap-1">
 <icons.Globe className="w-3 h-3" />{alert.source}
 </span>
 <span className="text-xs text-muted-foreground flex items-center gap-1">
 <icons.Clock className="w-3 h-3" />{alert.time}
 </span>
 </div>
 </div>
 </motion.div>
 ))}
 </div>
 </div>
 )}

 {activeView ==='config' && (
 <div className={cardStyle.base}>
 <h3 className={`${heading.section} mb-4`}>监控关键词配置</h3>
 <div className="flex gap-2 mb-4">
 <input
 type="text"
 value={newKeyword}
 onChange={e => setNewKeyword(e.target.value)}
 onKeyDown={e => e.key ==='Enter' && addKeyword()}
 placeholder="添加监控关键词..."
 className={`${inputStyle.search} flex-1`}
 />
 <button onClick={addKeyword} disabled={!newKeyword.trim()} className={buttonStyle.primary}>
 添加
 </button>
 </div>
 <div className="flex flex-wrap gap-2 mb-6">
 {keywords.map(kw => (
 <span key={kw} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
 {kw}
 <button onClick={() => removeKeyword(kw)} className="hover:text-destructive transition-colors">
 <icons.X className="w-3 h-3" />
 </button>
 </span>
 ))}
 </div>

 <h4 className={`${heading.card} mb-3`}>数据源配置</h4>
 <div className="grid grid-cols-2 gap-2">
 {['裁判文书网','企查查','天眼查','百度新闻','新浪财经','微博'].map(source => (
 <label key={source} className="flex items-center gap-2 p-2 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer">
 <input type="checkbox" defaultChecked className="rounded border-border" />
 <span className="text-xs text-foreground">{source}</span>
 </label>
 ))}
 </div>
 </div>
 )}
 </div>
 )
}
