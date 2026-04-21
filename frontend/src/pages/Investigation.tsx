/**
 * 智能调查 — 重构自原 DueDiligence，改为搜索+内联详情模式
 * v3.0 导航重构：原 8 个子导航改为内联视图
 *
 * 数据流：搜索 → SSE 流式调查 → 结果分发到各子组件
 */

import { useState, useCallback } from'react'
import { useParams, useNavigate } from'react-router-dom'
import {
 Search, ArrowLeft, Clock, TrendingUp, Building2,
 Shield, Scale, FileCheck, Network, FileText, Cpu, BarChart3
} from'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from'@/components/ui/tabs'
import { PageContainer } from'@/components/ui/PageContainer'
import { dueDiligenceApi, type InvestigationStreamEvent } from'@/lib/api'
import { toast } from'sonner'
import { heading } from'@/lib/design-tokens'

// 子组件
import { InvestigationOverview } from'@/components/due-diligence/InvestigationOverview'
import { SentimentAnalysis } from'@/components/due-diligence/SentimentAnalysis'
import { RiskTimeline } from'@/components/due-diligence/RiskTimeline'
import { LegalCases } from'@/components/due-diligence/LegalCases'
import { ComplianceReport } from'@/components/due-diligence/ComplianceReport'
import { InteractiveGraph } from'@/components/due-diligence/InteractiveGraph'
import { ScenarioSimulation } from'@/components/due-diligence/ScenarioSimulation'
import { InvestigationReport } from'@/components/due-diligence/InvestigationReport'

// 调查数据结构
interface InvestigationData {
 companyName: string
 basicInfo: any
 litigation: any
 credit: any
 risk: any
}

const EMPTY_DATA: InvestigationData = {
 companyName:'',
 basicInfo: {},
 litigation: {},
 credit: {},
 risk: {},
}

// 内联子视图 Tab 配置
const detailTabs = [
 { id:'overview', label:'调查概览', icon: BarChart3 },
 { id:'risk', label:'风险评估', icon: Shield },
 { id:'litigation', label:'诉讼分析', icon: Scale },
 { id:'compliance', label:'信用合规', icon: FileCheck },
 { id:'graph', label:'关系图谱', icon: Network },
 { id:'simulation', label:'风险推演', icon: Cpu },
 { id:'report', label:'调查报告', icon: FileText },
] as const

// 模拟历史搜索
const recentSearches = [
 { id:'1', name:'华为技术有限公司', time:'2 小时前' },
 { id:'2', name:'阿里巴巴集团', time:'昨天' },
 { id:'3', name:'深圳市腾讯计算机系统有限公司', time:'3 天前' },
]

// 模拟热点推荐
const hotTopics = [
 { id:'h1', name:'恒大地产集团', reason:'债务重组进展', trend:'up' },
 { id:'h2', name:'碧桂园控股', reason:'财务报告异常', trend:'up' },
 { id:'h3', name:'蚂蚁集团', reason:'监管政策更新', trend:'stable' },
]

// 搜索首页
function SearchView({ onSelect }: { onSelect: (id: string, name: string) => void }) {
 const [query, setQuery] = useState('')

 return (
 <PageContainer scrollable={false} showHeader={false}>
 <div data-analysis-shell className="max-w-5xl mx-auto space-y-6 fade-in-up">
 {/* 搜索区 — 左对齐紧凑版：标题 + 描述 + 搜索条一组 */}
 <div data-analysis-toolbar className="space-y-3 pt-4">
 <div>
 <h1 className="text-[28px] font-semibold leading-tight tracking-heading-md text-foreground">智能调查</h1>
 <p className="mt-1 text-body text-foreground-tertiary">输入企业名称，AI 自动搜索爬取并生成全维度调查报告</p>
 </div>
 <div className="relative max-w-2xl">
 <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-tertiary" />
 <input
 type="text"
 placeholder="输入企业名称开始调查..."
 value={query}
 onChange={e => setQuery(e.target.value)}
 onKeyDown={e => { if (e.key ==='Enter' && query.trim()) onSelect(query.trim(), query.trim()) }}
 className="w-full pl-10 pr-4 py-3 bg-card border border-border rounded-dd_xl text-body-lg text-foreground placeholder:text-foreground-tertiary shadow-elev-1 transition-[border-color,box-shadow] duration-fast ease-standard focus:outline-none focus:border-primary focus:shadow-focus-ring"
 />
 </div>
 </div>

 <div data-analysis-main className="grid md:grid-cols-2 gap-4">
 {/* 历史搜索 */}
 <div className="space-y-2">
 <h2 className="text-caption font-medium text-foreground-tertiary flex items-center gap-1.5 uppercase tracking-caption">
 <Clock className="h-3.5 w-3.5" />
 最近搜索
 </h2>
 <div className="space-y-2">
 {recentSearches.map(item => (
 <button
 key={item.id}
 onClick={() => onSelect(item.id, item.name)}
 className="w-full flex items-center justify-between p-3 bg-card border border-border rounded-dd_lg shadow-elev-1 hover:border-primary/30 hover:shadow-elev-2 active:scale-[0.99] transition-[transform,border-color,box-shadow] duration-fast ease-standard text-left focus-visible:outline-none focus-visible:shadow-focus-ring"
 >
 <div className="flex items-center gap-3">
 <Building2 className="h-4 w-4 text-muted-foreground" />
 <span className="text-sm font-medium">{item.name}</span>
 </div>
 <span className="text-xs text-muted-foreground">{item.time}</span>
 </button>
 ))}
 </div>
 </div>

 {/* 热点推荐 */}
 <div className="space-y-2">
 <h2 className="text-caption font-medium text-foreground-tertiary flex items-center gap-1.5 uppercase tracking-caption">
 <TrendingUp className="h-3.5 w-3.5" />
 热点推荐
 </h2>
 <div className="space-y-2">
 {hotTopics.map(item => (
 <button
 key={item.id}
 onClick={() => onSelect(item.id, item.name)}
 className="w-full flex items-center justify-between p-3 bg-card border border-border rounded-dd_lg shadow-elev-1 hover:border-primary/30 hover:shadow-elev-2 active:scale-[0.99] transition-[transform,border-color,box-shadow] duration-fast ease-standard text-left focus-visible:outline-none focus-visible:shadow-focus-ring"
 >
 <div className="flex items-center gap-3">
 <Building2 className="h-4 w-4 text-primary" />
 <div>
 <span className="text-sm font-medium">{item.name}</span>
 <p className="text-xs text-muted-foreground">{item.reason}</p>
 </div>
 </div>
 {item.trend ==='up' && <TrendingUp className="h-4 w-4 text-destructive" />}
 </button>
 ))}
 </div>
 </div>
 </div>
 </div>
 </PageContainer>
 )
}

// 调查详情（内联子视图）
function DetailView({ companyName, onBack }: { companyName: string; onBack: () => void }) {
 const [activeTab, setActiveTab] = useState('overview')
 const [data, setData] = useState<InvestigationData>({ ...EMPTY_DATA, companyName })
 const [investigating, setInvestigating] = useState(false)

 // 启动 SSE 流式调查
 const startInvestigation = useCallback(async () => {
 if (investigating) return
 setInvestigating(true)
 setData({ ...EMPTY_DATA, companyName })

 const collectedData: InvestigationData = { ...EMPTY_DATA, companyName }

 const handleEvent = (event: InvestigationStreamEvent) => {
 if (event.type ==='result') {
 if (event.step ==='basic_info') { collectedData.basicInfo = event.data; setData(prev => ({ ...prev, basicInfo: event.data })) }
 if (event.step ==='litigation') { collectedData.litigation = event.data; setData(prev => ({ ...prev, litigation: event.data })) }
 if (event.step ==='credit') { collectedData.credit = event.data; setData(prev => ({ ...prev, credit: event.data })) }
 if (event.step ==='risk') { collectedData.risk = event.data; setData(prev => ({ ...prev, risk: event.data })) }
 } else if (event.type ==='done') {
 setData({ ...collectedData })
 setInvestigating(false)
 toast.success('调查完成')
 } else if (event.type ==='error') {
 setInvestigating(false)
 toast.error('调查出错:' + (event.message ||'未知错误'))
 }
 }

 try {
 await dueDiligenceApi.streamInvestigate(
 companyName,'comprehensive', handleEvent, (err) => {
 setInvestigating(false)
 toast.error('调查出错:' + err.message)
 },
 )
 } catch {
 setInvestigating(false)
 toast.error('无法启动调查，请稍后重试')
 }
 }, [companyName, investigating])

 const handleBack = useCallback(() => {
 onBack()
 }, [onBack])

 // Tab 内容渲染
 function renderTabContent(tabId: string) {
 switch (tabId) {
 case'overview':
 return (
 <InvestigationOverview
 data={{
 basicInfo: data.basicInfo,
 risk: data.risk,
 litigation: data.litigation,
 credit: data.credit,
 }}
 companyName={companyName}
 onNavigate={setActiveTab}
 onGenerateReport={() => setActiveTab('report')}
 />
 )
 case'risk':
 return (
 <div className="space-y-6">
 <SentimentAnalysis data={data.risk} />
 <RiskTimeline data={data.risk} />
 </div>
 )
 case'litigation':
 return <LegalCases data={data.litigation} />
 case'compliance':
 return (
 <ComplianceReport data={{
 ...data.credit,
 dishonest_records: data.litigation?.dishonest_records || data.credit?.dishonest_records || 0,
 }} />
 )
 case'graph':
 return (
 <InteractiveGraph
 companyName={companyName}
 showKnowledgeLink
 />
 )
 case'simulation':
 return (
 <ScenarioSimulation
 companyName={companyName}
 currentRisk={data.risk}
 />
 )
 case'report':
 return (
 <InvestigationReport
 companyName={companyName}
 investigationData={data}
 />
 )
 default:
 return null
 }
 }

 return (
 <PageContainer scrollable={false} showHeader={false}>
 {/* 顶部：返回 + 公司名 + 操作 + Tab */}
 <div className="border-b bg-background/95 backdrop-blur px-6 pt-3 pb-0">
 <div className="flex items-center gap-3 mb-3">
 <button
 onClick={handleBack}
 className="p-1.5 rounded-lg hover:bg-muted transition-colors"
 >
 <ArrowLeft className="h-5 w-5" />
 </button>
 <div className="flex-1">
 <h1 className={heading.card}>{companyName}</h1>
 <p className="text-xs text-muted-foreground">企业全维度调查报告</p>
 </div>
 <button
 onClick={startInvestigation}
 disabled={investigating}
 className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
 >
 {investigating ?'调查中...' :'开始调查'}
 </button>
 </div>
 <Tabs value={activeTab} onValueChange={setActiveTab}>
 <TabsList className="bg-muted/50 flex-wrap h-auto gap-0.5">
 {detailTabs.map(tab => (
 <TabsTrigger key={tab.id} value={tab.id} className="gap-1 text-xs data-[state=active]:bg-background">
 <tab.icon className="h-3.5 w-3.5" />
 {tab.label}
 </TabsTrigger>
 ))}
 </TabsList>
 </Tabs>
 </div>

 {/* 内容区 */}
 <div className="flex-1 overflow-auto p-6">
 {renderTabContent(activeTab)}
 </div>
 </PageContainer>
 )
}

export default function Investigation() {
 const { companyId } = useParams()
 const navigate = useNavigate()
 const [selectedCompany, setSelectedCompany] = useState<{ id: string; name: string } | null>(
 companyId ? { id: companyId, name: companyId } : null
 )

 const handleSelect = useCallback((id: string, name: string) => {
 setSelectedCompany({ id, name })
 navigate(`/investigation/${encodeURIComponent(id)}`, { replace: true })
 }, [navigate])

 const handleBack = useCallback(() => {
 setSelectedCompany(null)
 navigate('/investigation', { replace: true })
 }, [navigate])

 if (selectedCompany) {
 return <DetailView companyName={selectedCompany.name} onBack={handleBack} />
 }

 return <SearchView onSelect={handleSelect} />
}
