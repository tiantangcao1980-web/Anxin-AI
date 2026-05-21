/**
 * Investigation · 智能调查（Editorial Luxury 改造 · Phase 1.10）
 *
 * 旧版用 PageContainer + bg-card shadow-elev-1 圆角搜索卡片 + Tabs 默认色块。
 * 新版：EditorialPageHeader + 1px hairline 网格 + 极简 Tab 下划线。
 *
 * 数据流：搜索 → SSE 流式调查 → 结果分发到各子组件
 */
import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Search, ArrowLeft, Clock, TrendingUp, Building2,
  Shield, Scale, FileCheck, Network, FileText, Cpu, BarChart3,
} from 'lucide-react'
import { toast } from 'sonner'

import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import { dueDiligenceApi, type InvestigationStreamEvent } from '@/lib/api'
import { cn } from '@/components/ui/utils'

// 子组件
import { InvestigationOverview } from '@/components/due-diligence/InvestigationOverview'
import { SentimentAnalysis } from '@/components/due-diligence/SentimentAnalysis'
import { RiskTimeline } from '@/components/due-diligence/RiskTimeline'
import { LegalCases } from '@/components/due-diligence/LegalCases'
import { ComplianceReport } from '@/components/due-diligence/ComplianceReport'
import { InteractiveGraph } from '@/components/due-diligence/InteractiveGraph'
import { ScenarioSimulation } from '@/components/due-diligence/ScenarioSimulation'
import { InvestigationReport } from '@/components/due-diligence/InvestigationReport'

interface InvestigationData {
  companyName: string
  basicInfo: any
  litigation: any
  credit: any
  risk: any
}

const EMPTY_DATA: InvestigationData = {
  companyName: '',
  basicInfo: {},
  litigation: {},
  credit: {},
  risk: {},
}

const detailTabs = [
  { id: 'overview',   label: '调查概览', labelEn: 'Overview',   icon: BarChart3 },
  { id: 'risk',       label: '风险评估', labelEn: 'Risk',       icon: Shield },
  { id: 'litigation', label: '诉讼分析', labelEn: 'Litigation', icon: Scale },
  { id: 'compliance', label: '信用合规', labelEn: 'Compliance', icon: FileCheck },
  { id: 'graph',      label: '关系图谱', labelEn: 'Graph',      icon: Network },
  { id: 'simulation', label: '风险推演', labelEn: 'Simulation', icon: Cpu },
  { id: 'report',     label: '调查报告', labelEn: 'Report',     icon: FileText },
] as const

const recentSearches = [
  { id: '1', name: '华为技术有限公司',           time: '2 小时前' },
  { id: '2', name: '阿里巴巴集团',               time: '昨天' },
  { id: '3', name: '深圳市腾讯计算机系统有限公司', time: '3 天前' },
]

const hotTopics = [
  { id: 'h1', name: '恒大地产集团', reason: '债务重组进展',   trend: 'up' as const },
  { id: 'h2', name: '碧桂园控股',   reason: '财务报告异常',   trend: 'up' as const },
  { id: 'h3', name: '蚂蚁集团',     reason: '监管政策更新',   trend: 'stable' as const },
]

/* ------------ 搜索首页 ------------ */
function SearchView({ onSelect }: { onSelect: (id: string, name: string) => void }) {
  const [query, setQuery] = useState('')

  return (
    <div className="min-h-screen flex flex-col">
      <EditorialPageHeader
        tracker={['Workspace', '智能调查']}
        title="智能调查"
        description="输入企业名称，AI 自动搜索爬取并生成全维度调查报告。"
      />

      <main className="flex-1 max-w-5xl w-full mx-auto px-8 py-10 space-y-12">
        {/* 搜索条 */}
        <section>
          <div className="relative max-w-2xl">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 stroke-[1.5] text-muted-foreground" />
            <input
              type="text"
              placeholder="输入企业名称开始调查…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && query.trim()) onSelect(query.trim(), query.trim()) }}
              className="w-full pl-11 pr-4 py-3.5 bg-card border border-border text-[15px] text-foreground placeholder:text-muted-foreground/70 transition-colors focus:outline-none focus:border-primary focus:ring-0"
            />
          </div>
        </section>

        {/* 历史 + 热点 1px hairline 网格 */}
        <section className="grid md:grid-cols-2 gap-px bg-border border-t border-l border-border">
          <div className="bg-card border-r border-b border-border p-6">
            <div className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
              <Clock className="w-3 h-3 stroke-[1.5]" />
              <span>Recent</span>
              <span className="text-foreground/30" aria-hidden>·</span>
              <span className="normal-case tracking-normal text-foreground/70">最近搜索</span>
            </div>
            <ul className="space-y-px">
              {recentSearches.map((item, i) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item.id, item.name)}
                    className="w-full flex items-center justify-between py-3 border-b border-border/60 last:border-b-0 transition-colors hover:bg-surface-2/40 -mx-2 px-2"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="font-serif text-[12px] text-muted-foreground w-6 tabular-nums shrink-0">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <Building2 className="w-4 h-4 stroke-[1.5] text-muted-foreground shrink-0" />
                      <span className="text-[14px] text-foreground truncate">{item.name}</span>
                    </div>
                    <span className="text-[12px] text-muted-foreground tabular-nums shrink-0 ml-3">{item.time}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-card border-r border-b border-border p-6">
            <div className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
              <TrendingUp className="w-3 h-3 stroke-[1.5]" />
              <span>Trending</span>
              <span className="text-foreground/30" aria-hidden>·</span>
              <span className="normal-case tracking-normal text-foreground/70">热点推荐</span>
            </div>
            <ul className="space-y-px">
              {hotTopics.map((item, i) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item.id, item.name)}
                    className="w-full flex items-center justify-between py-3 border-b border-border/60 last:border-b-0 transition-colors hover:bg-surface-2/40 -mx-2 px-2"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="font-serif text-[12px] text-muted-foreground w-6 tabular-nums shrink-0">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <Building2 className="w-4 h-4 stroke-[1.5] text-primary shrink-0" />
                      <div className="min-w-0">
                        <div className="text-[14px] text-foreground truncate">{item.name}</div>
                        <div className="text-[12px] text-muted-foreground mt-0.5 truncate">{item.reason}</div>
                      </div>
                    </div>
                    {item.trend === 'up' && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em] text-destructive shrink-0 ml-3">
                        <TrendingUp className="w-3 h-3 stroke-[1.5]" />
                        <span>Up</span>
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
    </div>
  )
}

/* ------------ 调查详情 ------------ */
function DetailView({ companyName, onBack }: { companyName: string; onBack: () => void }) {
  const [activeTab, setActiveTab] = useState<typeof detailTabs[number]['id']>('overview')
  const [data, setData] = useState<InvestigationData>({ ...EMPTY_DATA, companyName })
  const [investigating, setInvestigating] = useState(false)

  const startInvestigation = useCallback(async () => {
    if (investigating) return
    setInvestigating(true)
    setData({ ...EMPTY_DATA, companyName })

    const collectedData: InvestigationData = { ...EMPTY_DATA, companyName }

    const handleEvent = (event: InvestigationStreamEvent) => {
      if (event.type === 'result') {
        if (event.step === 'basic_info') { collectedData.basicInfo = event.data; setData((prev) => ({ ...prev, basicInfo: event.data })) }
        if (event.step === 'litigation') { collectedData.litigation = event.data; setData((prev) => ({ ...prev, litigation: event.data })) }
        if (event.step === 'credit')     { collectedData.credit     = event.data; setData((prev) => ({ ...prev, credit:     event.data })) }
        if (event.step === 'risk')       { collectedData.risk       = event.data; setData((prev) => ({ ...prev, risk:       event.data })) }
      } else if (event.type === 'done') {
        setData({ ...collectedData })
        setInvestigating(false)
        toast.success('调查完成')
      } else if (event.type === 'error') {
        setInvestigating(false)
        toast.error('调查出错: ' + (event.message || '未知错误'))
      }
    }

    try {
      await dueDiligenceApi.streamInvestigate(
        companyName, 'comprehensive', handleEvent,
        (err) => { setInvestigating(false); toast.error('调查出错: ' + err.message) },
      )
    } catch {
      setInvestigating(false)
      toast.error('无法启动调查，请稍后重试')
    }
  }, [companyName, investigating])

  function renderTabContent(tabId: typeof detailTabs[number]['id']) {
    switch (tabId) {
      case 'overview':
        return (
          <InvestigationOverview
            data={{
              basicInfo: data.basicInfo,
              risk: data.risk,
              litigation: data.litigation,
              credit: data.credit,
            }}
            companyName={companyName}
            onNavigate={(t) => setActiveTab(t as typeof detailTabs[number]['id'])}
            onGenerateReport={() => setActiveTab('report')}
          />
        )
      case 'risk':
        return (
          <div className="space-y-8">
            <SentimentAnalysis data={data.risk} />
            <RiskTimeline data={data.risk} />
          </div>
        )
      case 'litigation':
        return <LegalCases data={data.litigation} />
      case 'compliance':
        return (
          <ComplianceReport
            data={{
              ...data.credit,
              dishonest_records: data.litigation?.dishonest_records || data.credit?.dishonest_records || 0,
            }}
          />
        )
      case 'graph':
        return <InteractiveGraph companyName={companyName} showKnowledgeLink />
      case 'simulation':
        return <ScenarioSimulation companyName={companyName} currentRisk={data.risk} />
      case 'report':
        return <InvestigationReport companyName={companyName} investigationData={data} />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <EditorialPageHeader
        tracker={['Workspace', '智能调查', companyName]}
        title={companyName}
        description="企业全维度调查报告"
        actions={
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onBack}
              className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4 stroke-[1.5]" />
              <span>返回</span>
            </button>
            <button
              type="button"
              onClick={startInvestigation}
              disabled={investigating}
              className="bg-primary hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              {investigating ? '调查中…' : '开始调查'}
            </button>
          </div>
        }
      />

      {/* Editorial 下划线 tab */}
      <div className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-8 overflow-x-auto">
          <nav className="flex items-end gap-8" role="tablist">
            {detailTabs.map((tab) => {
              const active = activeTab === tab.id
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'relative pb-3 pt-3 flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.16em] transition-colors whitespace-nowrap',
                    active
                      ? 'text-foreground after:absolute after:left-0 after:right-0 after:bottom-0 after:h-px after:bg-primary'
                      : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  <Icon className="w-3.5 h-3.5 stroke-[1.5]" />
                  <span>{tab.labelEn}</span>
                  <span className="text-foreground/30" aria-hidden>·</span>
                  <span className="normal-case tracking-normal">{tab.label}</span>
                </button>
              )
            })}
          </nav>
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto px-8 py-8">
        {renderTabContent(activeTab)}
      </main>
    </div>
  )
}

/* ------------ 主页面 ------------ */
export default function Investigation() {
  const { companyId } = useParams()
  const navigate = useNavigate()
  const [selectedCompany, setSelectedCompany] = useState<{ id: string; name: string } | null>(
    companyId ? { id: companyId, name: companyId } : null,
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
