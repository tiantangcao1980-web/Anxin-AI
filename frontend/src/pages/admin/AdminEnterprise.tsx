/**
 * AdminEnterprise — 后台企业管理页面
 *
 * Tab1"企业信息": 组织列表 + 基本信息
 * Tab2"合规监控": 合规自检历史 + 风险趋势图
 * Tab3"风险概览": 企业风险评分卡 + 待处理风险项
 */
import { useState, useEffect } from'react'
import { PageContainer } from'@/components/ui/PageContainer'
import { Tabs, TabsList, TabsTrigger, TabsContent } from'@/components/ui/tabs'
import { DepartmentTreePanel } from '@/components/admin/enterprise/DepartmentTreePanel'
import { RoleBindingPanel } from '@/components/admin/enterprise/RoleBindingPanel'
import { SkillQuotaPanel } from '@/components/admin/enterprise/SkillQuotaPanel'
import { useAuthStore } from '@/lib/store'
import { Button } from'@/components/ui/button'
import { icons } from'@/lib/icons'
import { cardStyle, complianceScoreColors, heading, statusBadge, inputStyle, iconSize, riskLevelColors } from'@/lib/design-tokens'
import { adminApi, complianceApi } from'@/lib/api'
import { ErrorState, LoadingState } from'@/components/ui-unified'
import { StatCard, StatGrid } from'@/components/ui-unified'
import {
 LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
 BarChart, Bar, Legend,
} from'recharts'

// ============ 类型定义 ============

interface Enterprise {
 id: string
 name: string
 industry: string
 scale: string
 contact: string
 phone: string
 riskScore: number
 status:'active' |'inactive'
}

interface ComplianceHistoryItem {
 date: string
 score: number
 issues: number
}

interface ComplianceRecord {
 id: string
 enterprise: string
 type: string
 result:'pass' |'warning' |'fail'
 date: string
 issues: number
}

interface RiskItem {
 id: string
 enterprise: string
 category: string
 level:'critical' |'high' |'medium' |'low'
 description: string
 deadline: string
}

interface RiskTrendItem {
 month: string
 critical: number
 high: number
 medium: number
 low: number
}

// ============ 主组件 ============

export default function AdminEnterprise() {
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)

 const [enterprises, setEnterprises] = useState<Enterprise[]>([])
 const [complianceHistory, setComplianceHistory] = useState<ComplianceHistoryItem[]>([])
 const [complianceRecords, setComplianceRecords] = useState<ComplianceRecord[]>([])
 const [riskItems, setRiskItems] = useState<RiskItem[]>([])
 const [riskTrend, setRiskTrend] = useState<RiskTrendItem[]>([])

 useEffect(() => {
 let cancelled = false
 async function fetchData() {
 setLoading(true)
 setError(null)
 try {
 const [orgsData, industriesData] = await Promise.all([
 adminApi.listOrgs(),
 complianceApi.listIndustries().catch(() => null),
 ])
 if (cancelled) return

 // 企业列表
 const orgList = Array.isArray(orgsData) ? orgsData : (orgsData as any)?.organizations || []
 setEnterprises(orgList.map((o: any) => ({
 id: o.id ||'',
 name: o.name ||'',
 industry: o.industry ||'',
 scale: o.scale || o.company_size ||'',
 contact: o.contact || o.contact_name ||'',
 phone: o.phone || o.contact_phone ||'',
 riskScore: o.risk_score ?? o.riskScore ?? 0,
 status: o.status || (o.is_active ?'active' :'inactive'),
 })))

 // 合规历史和记录 - 从 industries 响应中提取（如果后端支持）
 if (industriesData) {
 const history = industriesData.compliance_history || industriesData.history || []
 if (Array.isArray(history)) setComplianceHistory(history)

 const records = industriesData.compliance_records || industriesData.records || []
 if (Array.isArray(records)) {
 setComplianceRecords(records.map((r: any) => ({
 id: r.id ||'',
 enterprise: r.enterprise || r.company_name ||'',
 type: r.type || r.check_type ||'',
 result: r.result || r.status ||'pass',
 date: r.date || r.created_at ||'',
 issues: r.issues ?? r.issue_count ?? 0,
 })))
 }

 // 风险项
 const risks = industriesData.risk_items || industriesData.risks || []
 if (Array.isArray(risks)) {
 setRiskItems(risks.map((r: any) => ({
 id: r.id ||'',
 enterprise: r.enterprise || r.company_name ||'',
 category: r.category ||'',
 level: r.level || r.severity ||'low',
 description: r.description ||'',
 deadline: r.deadline || r.due_date ||'',
 })))
 }

 // 风险趋势
 const trend = industriesData.risk_trend || industriesData.trend || []
 if (Array.isArray(trend)) setRiskTrend(trend)
 }
 } catch (err: any) {
 if (!cancelled) {
 console.error('企业数据加载失败:', err)
 setError(err?.message ||'数据加载失败，请稍后重试')
 }
 } finally {
 if (!cancelled) setLoading(false)
 }
 }
 fetchData()
 return () => { cancelled = true }
 }, [])

 if (loading) {
 return (
 <PageContainer title="企业管理">
 <LoadingState variant="skeleton" rows={6} />
 </PageContainer>
 )
 }

 if (error) {
 return (
 <PageContainer title="企业管理">
 <ErrorState title="加载失败" message={error} onRetry={() => window.location.reload()} />
 </PageContainer>
 )
 }

 // 当前账号所属组织 —— 给部门 / 角色绑定面板用
 const orgId = useAuthStore((s) => s.user?.org_id || null)

 return (
 <PageContainer title="企业管理" description="企业信息、合规监控、风险概览、组织目录与权限">
 <Tabs defaultValue="info">
 <TabsList>
 <TabsTrigger value="info">
 <icons.Building2 className="w-4 h-4 mr-1.5" />
 企业信息
 </TabsTrigger>
 <TabsTrigger value="compliance">
 <icons.ShieldCheck className="w-4 h-4 mr-1.5" />
 合规监控
 </TabsTrigger>
 <TabsTrigger value="risk">
 <icons.AlertTriangle className="w-4 h-4 mr-1.5" />
 风险概览
 </TabsTrigger>
 <TabsTrigger value="directory">
 <icons.Network className="w-4 h-4 mr-1.5" />
 组织目录
 </TabsTrigger>
 <TabsTrigger value="bindings">
 <icons.Lock className="w-4 h-4 mr-1.5" />
 权限绑定
 </TabsTrigger>
 <TabsTrigger value="quota">
 <icons.Cpu className="w-4 h-4 mr-1.5" />
 Skill 配额
 </TabsTrigger>
 </TabsList>

 <TabsContent value="info">
 <EnterpriseInfoTab enterprises={enterprises} />
 </TabsContent>

 <TabsContent value="compliance">
 <ComplianceTab history={complianceHistory} records={complianceRecords} />
 </TabsContent>

 <TabsContent value="risk">
 <RiskOverviewTab riskItems={riskItems} riskTrend={riskTrend} />
 </TabsContent>

 <TabsContent value="directory">
 <DepartmentTreePanel orgId={orgId} />
 </TabsContent>

 <TabsContent value="bindings">
 <RoleBindingPanel orgId={orgId} />
 </TabsContent>

 <TabsContent value="quota">
 <SkillQuotaPanel orgId={orgId} />
 </TabsContent>
 </Tabs>
 </PageContainer>
 )
}

// ============ Tab: 企业信息 ============

function EnterpriseInfoTab({ enterprises }: { enterprises: Enterprise[] }) {
 const [search, setSearch] = useState('')

 const filtered = enterprises.filter(e =>
 e.name.includes(search) || e.industry.includes(search)
 )

 const riskScoreColor = (score: number) => {
 if (score >= 80) return'text-success'
 if (score >= 60) return'text-warning'
 return'text-destructive'
 }

 return (
 <div className="space-y-4">
 <div className="flex gap-3">
 <div className="flex-1 relative">
 <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
 <input
 type="text"
 value={search}
 onChange={e => setSearch(e.target.value)}
 placeholder="搜索企业名称或行业..."
 className={inputStyle.search +' pl-10'}
 />
 </div>
 </div>

 {filtered.length > 0 ? (
 <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
 {filtered.map(ent => (
 <div key={ent.id} className={cardStyle.interactive}>
 <div className="flex items-start justify-between mb-3">
 <div>
 <h3 className={heading.card}>{ent.name}</h3>
 <p className="text-xs text-muted-foreground mt-0.5">{ent.industry} / {ent.scale}</p>
 </div>
 <span className={`text-xs px-2 py-0.5 rounded-full ${ent.status ==='active' ? statusBadge.success : statusBadge.neutral}`}>
 {ent.status ==='active' ?'活跃' :'非活跃'}
 </span>
 </div>
 <div className="space-y-1.5 text-xs text-muted-foreground">
 <div className="flex items-center gap-1.5">
 <icons.User className="w-3 h-3" />
 <span>联系人：{ent.contact}</span>
 </div>
 <div className="flex items-center gap-1.5">
 <icons.Phone className="w-3 h-3" />
 <span>{ent.phone}</span>
 </div>
 </div>
 <div className="mt-3 pt-3 border-t border-border/50 flex items-center justify-between">
 <span className="text-xs text-muted-foreground">风险评分</span>
 <span className={`text-lg font-bold ${riskScoreColor(ent.riskScore)}`}>{ent.riskScore}</span>
 </div>
 </div>
 ))}
 </div>
 ) : (
 <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
 <icons.Building2 className="w-12 h-12 mb-3 opacity-20" />
 <p className="text-sm">{enterprises.length === 0 ?'暂无企业数据' :'未找到匹配的企业'}</p>
 </div>
 )}
 </div>
 )
}

// ============ Tab: 合规监控 ============

function ComplianceTab({
 history,
 records,
}: {
 history: ComplianceHistoryItem[]
 records: ComplianceRecord[]
}) {
 const resultStyle = (result:'pass' |'warning' |'fail') => {
 switch (result) {
 case'pass': return statusBadge.success
 case'warning': return statusBadge.warning
 case'fail': return statusBadge.error
 }
 }

 const resultLabel = (result:'pass' |'warning' |'fail') => {
 switch (result) {
 case'pass': return'通过'
 case'warning': return'警告'
 case'fail': return'不通过'
 }
 }

 return (
 <div className="space-y-6">
 {/* 合规趋势 */}
 <div className={cardStyle.base}>
 <h3 className={heading.section +' mb-4'}>合规评分趋势</h3>
 {history.length > 0 ? (
 <ResponsiveContainer width="100%" height={260}>
 <LineChart data={history}>
 <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
 <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
 <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
 <Tooltip />
 <Legend />
 <Line type="monotone" dataKey="score" name="合规评分" stroke="hsl(var(--primary))" strokeWidth={2} />
 <Line type="monotone" dataKey="issues" name="问题数" stroke={complianceScoreColors.medium} strokeWidth={2} />
 </LineChart>
 </ResponsiveContainer>
 ) : (
 <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">暂无合规趋势数据</div>
 )}
 </div>

 {/* 自检记录 */}
 <div className={cardStyle.base}>
 <h3 className={heading.section +' mb-4'}>合规自检记录</h3>
 {records.length > 0 ? (
 <div className="overflow-x-auto">
 <table className="w-full text-sm">
 <thead>
 <tr className="border-b border-border text-left">
 <th className="pb-3 pr-4 font-medium text-muted-foreground">企业</th>
 <th className="pb-3 pr-4 font-medium text-muted-foreground">检查类型</th>
 <th className="pb-3 pr-4 font-medium text-muted-foreground">日期</th>
 <th className="pb-3 pr-4 font-medium text-muted-foreground">问题数</th>
 <th className="pb-3 font-medium text-muted-foreground">结果</th>
 </tr>
 </thead>
 <tbody>
 {records.map(record => (
 <tr key={record.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
 <td className="py-3 pr-4 font-medium">{record.enterprise}</td>
 <td className="py-3 pr-4 text-muted-foreground">{record.type}</td>
 <td className="py-3 pr-4 text-xs text-muted-foreground">{record.date}</td>
 <td className="py-3 pr-4">{record.issues}</td>
 <td className="py-3">
 <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${resultStyle(record.result)}`}>
 {resultLabel(record.result)}
 </span>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 ) : (
 <div className="py-12 text-center text-sm text-muted-foreground">暂无合规自检记录</div>
 )}
 </div>
 </div>
 )
}

// ============ Tab: 风险概览 ============

function RiskOverviewTab({
 riskItems,
 riskTrend,
}: {
 riskItems: RiskItem[]
 riskTrend: RiskTrendItem[]
}) {
 const levelStyle = (level:'critical' |'high' |'medium' |'low') => {
 switch (level) {
 case'critical': return statusBadge.error
 case'high': return statusBadge.warning
 case'medium': return statusBadge.info
 case'low': return statusBadge.neutral
 }
 }

 const levelLabel = (level:'critical' |'high' |'medium' |'low') => {
 switch (level) {
 case'critical': return'严重'
 case'high': return'高'
 case'medium': return'中'
 case'low': return'低'
 }
 }

 // 风险评分卡
 const riskCounts = {
 critical: riskItems.filter(r => r.level ==='critical').length,
 high: riskItems.filter(r => r.level ==='high').length,
 medium: riskItems.filter(r => r.level ==='medium').length,
 low: riskItems.filter(r => r.level ==='low').length,
 }

 return (
 <div className="space-y-6">
 {/* 风险评分卡 — 统一 StatGrid */}
 <StatGrid cols={4}>
 <StatCard index={0} icon={icons.AlertTriangle} tone="destructive" label="严重风险" value={riskCounts.critical} hint="需立即介入" />
 <StatCard index={1} icon={icons.AlertTriangle} tone="warning"     label="高风险"   value={riskCounts.high}     hint="建议处置" />
 <StatCard index={2} icon={icons.Clock}         tone="primary"     label="中风险"   value={riskCounts.medium}   hint="持续关注" />
 <StatCard index={3} icon={icons.CheckCircle}   tone="success"     label="低风险"   value={riskCounts.low}      hint="状态正常" />
 </StatGrid>

 {/* 风险趋势 */}
 <div className={cardStyle.base}>
 <h3 className={heading.section +' mb-4'}>风险趋势</h3>
 {riskTrend.length > 0 ? (
 <ResponsiveContainer width="100%" height={260}>
 <BarChart data={riskTrend}>
 <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
 <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
 <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
 <Tooltip />
 <Legend />
 <Bar dataKey="critical" name="严重" fill={riskLevelColors.critical} radius={[2, 2, 0, 0]} />
 <Bar dataKey="high" name="高" fill={riskLevelColors.high} radius={[2, 2, 0, 0]} />
 <Bar dataKey="medium" name="中" fill={riskLevelColors.medium} radius={[2, 2, 0, 0]} />
 <Bar dataKey="low" name="低" fill={riskLevelColors.low} radius={[2, 2, 0, 0]} />
 </BarChart>
 </ResponsiveContainer>
 ) : (
 <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">暂无风险趋势数据</div>
 )}
 </div>

 {/* 待处理风险项 */}
 <div className={cardStyle.base}>
 <h3 className={heading.section +' mb-4'}>待处理风险项</h3>
 {riskItems.length > 0 ? (
 <div className="space-y-3">
 {riskItems.map(item => (
 <div key={item.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
 <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 mt-0.5 ${levelStyle(item.level)}`}>
 {levelLabel(item.level)}
 </span>
 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-2">
 <p className="text-sm font-medium text-foreground">{item.enterprise}</p>
 <span className="text-xs text-muted-foreground">/ {item.category}</span>
 </div>
 <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
 </div>
 <div className="text-right shrink-0">
 <p className="text-xs text-muted-foreground">截止日期</p>
 <p className="text-xs font-medium text-foreground">{item.deadline}</p>
 </div>
 </div>
 ))}
 </div>
 ) : (
 <div className="py-12 text-center text-sm text-muted-foreground">暂无待处理风险项</div>
 )}
 </div>
 </div>
 )
}
