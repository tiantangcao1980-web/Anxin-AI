/**
 * 智能调查 — 专业调查仪表板
 *
 * 仪表板布局：左侧导航(8模块) + 右侧动态内容区
 * 模块：调查概览 / 风险评估 / 诉讼分析 / 信用合规 / 关系图谱 / 舆情监控 / 风险推演 / 调查报告
 *
 * 数据流：搜索 → SSE 流式调查 → 结果分发到各模块
 * 联动法律智库知识图谱
 */
import { useState, useCallback, useMemo, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { cardStyle, heading, buttonStyle, inputStyle } from '@/lib/design-tokens'
import { dueDiligenceApi, licApi, knowledgeApi, InvestigationStreamEvent } from '@/lib/api'
import { toast } from 'sonner'
import { v4 as uuidv4 } from 'uuid'

// 子组件
import { type InvestigationSection } from '@/components/due-diligence/InvestigationSidebar'
import { InvestigationOverview } from '@/components/due-diligence/InvestigationOverview'
import { InvestigationProgress, type InvestigationStage, type ConflictInfo } from '@/components/due-diligence/InvestigationProgress'
import { CompanyProfile } from '@/components/due-diligence/CompanyProfile'
import { SentimentAnalysis } from '@/components/due-diligence/SentimentAnalysis'
import { LegalCases } from '@/components/due-diligence/LegalCases'
import { ComplianceReport } from '@/components/due-diligence/ComplianceReport'
import { RiskTimeline } from '@/components/due-diligence/RiskTimeline'
import { SentimentDashboard } from '@/components/due-diligence/SentimentDashboard'
import { InteractiveGraph } from '@/components/due-diligence/InteractiveGraph'
import { ScenarioSimulation } from '@/components/due-diligence/ScenarioSimulation'
import { InvestigationReport } from '@/components/due-diligence/InvestigationReport'

// ===== 类型 =====
type SearchMode = 'hybrid' | 'keyword' | 'vector' | 'rag'

interface InvestigationData {
  companyName: string
  basicInfo: any
  litigation: any
  credit: any
  risk: any
}

// (DEMO_DATA 已移除 — 未调查时显示空状态引导)

interface SearchResult {
  id?: string
  title?: string
  content: string
  source?: string
  score?: number
}

interface RAGAnswer {
  answer: string
  sources: any[]
  chunks_used?: number
}

const SEARCH_MODES: { key: SearchMode; label: string; desc: string }[] = [
  { key: 'hybrid', label: '混合检索', desc: '关键词 + 向量综合排序' },
  { key: 'keyword', label: '关键词', desc: '精确匹配关键词' },
  { key: 'vector', label: '语义检索', desc: '基于语义相似度' },
  { key: 'rag', label: 'RAG 问答', desc: 'AI 智能问答' },
]

// ===== 智能搜索子组件 =====
function SearchSection() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [results, setResults] = useState<SearchResult[]>([])
  const [ragAnswer, setRagAnswer] = useState<RAGAnswer | null>(null)
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return
    setLoading(true)
    setHasSearched(true)
    setRagAnswer(null)
    try {
      if (mode === 'rag') {
        const answer = await knowledgeApi.ragQuery(query)
        setRagAnswer(answer)
        setResults([])
      } else {
        const data = await knowledgeApi.search(query, undefined, 20, mode === 'hybrid')
        setResults(Array.isArray(data) ? data : [])
      }
    } catch (err: any) {
      toast.error('搜索失败: ' + (err.message || '服务不可用'))
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [query, mode])

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="输入搜索关键词或问题..."
            className={`${inputStyle.search} pl-10`}
          />
        </div>
        <button onClick={handleSearch} disabled={loading || !query.trim()} className={`${buttonStyle.primary} min-w-[80px]`}>
          {loading ? <icons.RefreshCw className="w-4 h-4 animate-spin" /> : '搜索'}
        </button>
      </div>

      <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1">
        {SEARCH_MODES.map(m => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap shrink-0 ${
              mode === m.key ? 'bg-primary text-white' : 'bg-muted text-muted-foreground hover:text-foreground'
            }`}
            title={m.desc}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="min-h-[300px]">
        {!hasSearched && (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <icons.Search className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-sm">输入关键词开始搜索知识库</p>
            <p className="text-xs mt-1 opacity-60">支持关键词检索、语义检索和 RAG 智能问答</p>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-20">
            <icons.RefreshCw className="w-6 h-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">搜索中...</span>
          </div>
        )}

        {ragAnswer && !loading && (
          <div className="space-y-4">
            <div className={cardStyle.highlight}>
              <div className="flex items-center gap-2 mb-3">
                <icons.Sparkles className="w-4 h-4 text-primary" />
                <span className={heading.section}>AI 回答</span>
              </div>
              <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{ragAnswer.answer}</div>
              {ragAnswer.chunks_used && (
                <p className="text-xs text-muted-foreground mt-3">参考了 {ragAnswer.chunks_used} 个知识片段</p>
              )}
            </div>
          </div>
        )}

        {hasSearched && !loading && results.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-3">找到 {results.length} 条结果</p>
            <div className="space-y-3">
              {results.map((r, i) => (
                <div key={r.id || i} className={cardStyle.interactive}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <h3 className={`${heading.card} mb-1`}>{r.title || `结果 ${i + 1}`}</h3>
                      <p className="text-xs text-muted-foreground line-clamp-3">{r.content?.slice(0, 300)}</p>
                      {r.source && (
                        <div className="flex items-center gap-1 mt-2">
                          <icons.Link className="w-3 h-3 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">{r.source}</span>
                        </div>
                      )}
                    </div>
                    {r.score !== undefined && (
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        r.score > 0.8 ? 'text-emerald-600 bg-emerald-50' : r.score > 0.5 ? 'text-amber-600 bg-amber-50' : 'text-muted-foreground bg-muted'
                      }`}>
                        {(r.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {hasSearched && !loading && results.length === 0 && !ragAnswer && (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <icons.FileSearch className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">未找到相关结果</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ===== 主组件 =====
export default function DueDiligence() {
  const navigate = useNavigate()

  // 搜索状态
  const [searchInput, setSearchInput] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [hasResults, setHasResults] = useState(false)
  const [companyName, setCompanyName] = useState('')
  const [investigationData, setInvestigationData] = useState<InvestigationData | null>(null)

  // 从 URL 参数读取当前模块（由 Layout 侧边栏驱动）
  const { section: urlSection } = useParams<{ section?: string }>()
  const SECTION_MAP: Record<string, InvestigationSection> = {
    risk: 'risk', litigation: 'litigation', compliance: 'compliance',
    graph: 'graph', sentiment: 'sentiment', simulation: 'simulation', report: 'report',
  }
  const activeSection: InvestigationSection = SECTION_MAP[urlSection || ''] || 'overview'
  const setActiveSection = useCallback((s: InvestigationSection) => {
    if (s === 'overview') navigate('/due-diligence')
    else navigate(`/due-diligence/${s}`)
  }, [navigate])

  // 多阶段进度
  const [stages, setStages] = useState<InvestigationStage[]>([])
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([])
  const [consensus, setConsensus] = useState<any>(null)
  const [licTaskId, setLicTaskId] = useState('')
  const [investigateStartTime, setInvestigateStartTime] = useState(0)

  // 是否显示搜索模式（未开始调查时）
  const [showSearch, setShowSearch] = useState(false)

  // SSE 中断控制
  const sseAbortRef = useRef<AbortController | null>(null)
  const inactivityTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const collectedDataRef = useRef<any>(null)

  // 45 秒无新事件则自动 fallback
  const INACTIVITY_TIMEOUT = 45_000

  const resetInactivityTimer = useCallback((name: string) => {
    if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current)
    inactivityTimerRef.current = setTimeout(() => {
      toast.info('AI 调查响应超时，正在切换查询方式...')
      sseAbortRef.current?.abort()
      fallbackInvestigate(name, collectedDataRef.current || { companyName: name })
    }, INACTIVITY_TIMEOUT)
  }, [])

  /** 手动跳过 SSE，降级到 REST */
  const handleSkipToFallback = useCallback(() => {
    sseAbortRef.current?.abort()
    if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current)
    const name = companyName
    toast.info('正在切换为快速查询模式...')
    fallbackInvestigate(name, collectedDataRef.current || { companyName: name })
  }, [companyName])

  /** 取消调查 */
  const handleCancelInvestigation = useCallback(() => {
    sseAbortRef.current?.abort()
    if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current)
    setIsSearching(false)
    setStages([])
    toast.info('调查已取消')
  }, [])

  // 开始调查
  const handleInvestigate = useCallback(async (name: string) => {
    if (!name.trim()) return
    setCompanyName(name)
    setIsSearching(true)
    setHasResults(false)
    setInvestigationData(null)
    setShowSearch(false)
    setConflicts([])
    setConsensus(null)
    setActiveSection('overview')
    setInvestigateStartTime(Date.now())

    // 启动 LIC 爬取（fire-and-forget，不阻塞核心流程）
    const taskId = uuidv4()
    setLicTaskId(taskId)
    licApi.startCrawl({ url: 'https://www.tianyancha.com', keyword: name, task_id: taskId }).catch(() => {})

    // 初始化三阶段
    const initialStages: InvestigationStage[] = [
      {
        id: 'collection',
        label: '数据采集',
        status: 'active',
        agents: [
          { name: 'due_diligence', label: '企业背景调查', status: 'loading' },
          { name: 'risk_assessor', label: '风险评估分析', status: 'loading' },
          { name: 'compliance', label: '合规审查', status: 'loading' },
        ],
      },
      { id: 'verification', label: '交叉验证', status: 'pending', agents: [] },
      { id: 'synthesis', label: '综合分析', status: 'pending', agents: [] },
    ]
    setStages(initialStages)

    const collectedData: any = { companyName: name }
    collectedDataRef.current = collectedData

    // 初始化 SSE 中断控制器
    if (sseAbortRef.current) sseAbortRef.current.abort()
    sseAbortRef.current = new AbortController()

    // 启动无活动超时计时器
    resetInactivityTimer(name)

    try {
      await dueDiligenceApi.streamInvestigate(
        name,
        'comprehensive',
        (event: InvestigationStreamEvent) => {
          // 每收到一个事件都重置无活动计时器
          resetInactivityTimer(name)

          if (event.type === 'step') {
            setStages(prev => prev.map(stage => {
              if (stage.id !== 'collection') return stage
              return {
                ...stage,
                agents: stage.agents?.map(a => {
                  if (event.step === 'basic_info' && a.name === 'due_diligence') return { ...a, status: 'loading' as const }
                  if (event.step === 'risk' && a.name === 'risk_assessor') return { ...a, status: 'loading' as const }
                  if (event.step === 'credit' && a.name === 'compliance') return { ...a, status: 'loading' as const }
                  return a
                }) || [],
              }
            }))
          } else if (event.type === 'result') {
            if (event.step === 'basic_info') { collectedData.basicInfo = event.data }
            if (event.step === 'litigation') { collectedData.litigation = event.data }
            if (event.step === 'credit') { collectedData.credit = event.data }
            if (event.step === 'risk') { collectedData.risk = event.data }

            setStages(prev => prev.map(stage => {
              if (stage.id !== 'collection') return stage
              return {
                ...stage,
                agents: stage.agents?.map(a => {
                  if (event.step === 'basic_info' && a.name === 'due_diligence') return { ...a, status: 'done' as const, data: event.data }
                  if (event.step === 'risk' && a.name === 'risk_assessor') return { ...a, status: 'done' as const, data: event.data }
                  if (event.step === 'credit' && a.name === 'compliance') return { ...a, status: 'done' as const, data: event.data }
                  return a
                }) || [],
              }
            }))
          } else if (event.type === 'stage') {
            setStages(prev => prev.map(s => {
              if (s.id === event.step) return { ...s, status: 'active' }
              if (s.status === 'active' && s.id !== event.step) return { ...s, status: 'done' }
              return s
            }))
          } else if (event.type === 'conflict') {
            setConflicts(prev => [...prev, { description: event.message || '', agents: (event.data as any)?.agents || [] }])
          } else if (event.type === 'consensus') {
            setConsensus(event.data)
          } else if (event.type === 'done') {
            if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current)
            setStages(prev => prev.map(s => ({ ...s, status: 'done' as const })))
            setInvestigationData(collectedData)
            setIsSearching(false)
            setHasResults(true)
            toast.success('尽职调查完成')
          } else if (event.type === 'error') {
            if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current)
            // 如果已收集到部分数据，尝试用 fallback 补全
            const hasPartialData = collectedData.basicInfo || collectedData.litigation || collectedData.risk
            if (hasPartialData) {
              toast.info('部分数据已获取，正在补全...')
              fallbackInvestigate(name, collectedData)
            } else {
              toast.info('正在切换查询方式...')
              fallbackInvestigate(name, collectedData)
            }
          }
        },
        () => {
          if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current)
          toast.info('正在切换查询方式...')
          fallbackInvestigate(name, collectedData)
        }
      )
    } catch {
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current)
      toast.info('正在切换查询方式...')
      fallbackInvestigate(name, collectedData)
    }
  }, [resetInactivityTimer])

  const fallbackInvestigate = async (name: string, collectedData: any) => {
    // 更新进度状态为"快速查询"
    setStages([
      { id: 'collection', label: '数据采集', status: 'active', agents: [
        { name: 'due_diligence', label: '企业背景调查', status: 'loading' },
        { name: 'risk_assessor', label: '风险评估分析', status: 'loading' },
        { name: 'compliance', label: '合规审查', status: 'loading' },
      ]},
      { id: 'verification', label: '交叉验证', status: 'pending', agents: [] },
      { id: 'synthesis', label: '综合分析', status: 'pending', agents: [] },
    ])

    try {
      const [profile, risks, litigation] = await Promise.all([
        dueDiligenceApi.getCompanyProfile(name),
        dueDiligenceApi.getCompanyRisks(name),
        dueDiligenceApi.getCompanyLitigation(name),
      ])
      collectedData.basicInfo = profile.profile
      const litSummary = litigation.summary || {}
      collectedData.litigation = {
        total_cases: litSummary.total_cases || 0,
        as_plaintiff: litSummary.as_plaintiff || 0,
        as_defendant: litSummary.as_defendant || 0,
        execution_cases: litSummary.execution_cases || 0,
        dishonest_records: litSummary.dishonest_records || 0,
        major_cases: litigation.major_cases || [],
      }
      collectedData.credit = {
        credit_rating: risks.risk_score ? (risks.risk_score > 80 ? 'AA' : risks.risk_score > 60 ? 'A' : risks.risk_score > 40 ? 'BBB' : 'B') : 'B',
        administrative_penalties: 0,
        tax_violations: 0,
        environmental_penalties: 0,
        abnormal_operations: 0,
        serious_violations: 0,
      }
      collectedData.risk = {
        operation_risk: risks.breakdown?.operation_risk?.score || 0,
        litigation_risk: risks.breakdown?.litigation_risk?.score || 0,
        credit_risk: risks.breakdown?.credit_risk?.score || 0,
        compliance_risk: risks.breakdown?.compliance_risk?.score || 0,
        relation_risk: risks.breakdown?.relation_risk?.score || 0,
        overall_rating: risks.risk_level || 'medium',
        risk_points: risks.risk_points || [],
        recommendations: risks.recommendations || [],
      }

      setStages(prev => prev.map(s => ({ ...s, status: 'done' as const })))
      setInvestigationData(collectedData)
      setIsSearching(false)
      setHasResults(true)
      toast.success('尽职调查完成')
    } catch (error: any) {
      toast.error(error.message || '调查失败')
      setIsSearching(false)
    }
  }

  // 联动知识图谱
  const handleEntityClick = useCallback((entityName: string) => {
    navigate(`/knowledge-graph?search=${encodeURIComponent(entityName)}`)
  }, [navigate])

  // 是否处于空状态（未进行调查）
  const isDemo = !hasResults && !isSearching
  const activeData = investigationData
  const activeName = companyName || ''

  // 渲染当前活跃的内容区域
  const renderContent = () => {
    const data = activeData

    // 未调查时显示空状态引导（不再展示假数据）
    if (!data) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <icons.Search className="w-16 h-16 mb-4 opacity-20" />
          <p className="text-lg font-medium mb-2">尚未开始调查</p>
          <p className="text-sm opacity-60 mb-6 text-center max-w-md">
            在上方搜索框输入企业名称，启动 AI 智能尽职调查，多 Agent 协同为您生成全方位企业调查报告
          </p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>试试：</span>
            {['阿里巴巴', '腾讯', '华为'].map(name => (
              <button
                key={name}
                onClick={() => { setSearchInput(name); handleInvestigate(name) }}
                className={`${buttonStyle.ghost} text-xs rounded-full`}
              >
                {name}
              </button>
            ))}
          </div>
        </div>
      )
    }

    switch (activeSection) {
      case 'overview':
        return (
          <InvestigationOverview
            data={{
              basicInfo: data.basicInfo,
              risk: data.risk,
              litigation: data.litigation,
              credit: data.credit,
            }}
            companyName={activeName}
            onNavigate={(s) => setActiveSection(s as InvestigationSection)}
            onGenerateReport={() => setActiveSection('report')}
          />
        )
      case 'risk':
        return (
          <div className="space-y-6">
            <SentimentAnalysis data={data.risk} />
            <RiskTimeline data={data.risk} />
          </div>
        )
      case 'litigation':
        return <LegalCases data={data.litigation} />
      case 'compliance':
        return <ComplianceReport data={{
          ...data.credit,
          dishonest_records: data.litigation?.dishonest_records || data.credit?.dishonest_records || 0,
        }} />
      case 'graph':
        return (
          <InteractiveGraph
            companyName={activeName}
            onEntityClick={handleEntityClick}
            showKnowledgeLink={!isDemo}
          />
        )
      case 'sentiment':
        return (
          <SentimentDashboard
            companyName={activeName}
            onEntityClick={handleEntityClick}
            investigationData={{
              risk: data.risk,
              litigation: data.litigation,
              credit: data.credit,
            }}
          />
        )
      case 'simulation':
        return (
          <ScenarioSimulation
            companyName={activeName}
            currentRisk={data.risk}
          />
        )
      case 'report':
        return (
          <InvestigationReport
            companyName={activeName}
            investigationData={data}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* 顶部搜索栏 */}
      <div className="shrink-0 p-4 sm:p-5 lg:p-6 pb-0 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h1 className={`${heading.page} tracking-tight flex flex-wrap items-end`}>智能调查</h1>
            <p className={`${heading.muted} mt-0.5`}>多 Agent 协同 · 一站式智能法律调查平台</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setShowSearch(!showSearch) }}
              className={`${showSearch ? buttonStyle.primary : buttonStyle.ghost} text-xs flex items-center gap-1.5`}
            >
              <icons.Search className="w-3.5 h-3.5" />
              知识搜索
            </button>
          </div>
        </div>

        {/* 调查搜索框 — 始终显示（非知识搜索模式下） */}
        {!showSearch && (
          <div className="flex gap-3 items-center">
            <div className="flex-1 relative">
              <icons.Building2 className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleInvestigate(searchInput)}
                placeholder="输入企业名称，启动智能尽职调查..."
                disabled={isSearching}
                className={`${inputStyle.search} pl-10 pr-32 py-3 rounded-xl disabled:opacity-50`}
              />
              <button
                onClick={() => handleInvestigate(searchInput)}
                disabled={!searchInput.trim() || isSearching}
                className={`${buttonStyle.primary} absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 rounded-lg disabled:opacity-50 flex items-center gap-1.5 shadow-sm`}
              >
                {isSearching ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : <icons.Sparkles className="w-4 h-4" />}
                {isSearching ? '调查中...' : '开始调查'}
              </button>
            </div>
          </div>
        )}

        {/* 快速开始 — 仅在示例模式下显示 */}
        {!showSearch && isDemo && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">快速开始：</span>
            {['阿里巴巴', '腾讯', '华为', '字节跳动'].map(name => (
              <button
                key={name}
                onClick={() => { setSearchInput(name); handleInvestigate(name) }}
                className={`${buttonStyle.ghost} text-xs rounded-full`}
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 主内容区 */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {/* 知识搜索模式 */}
        {showSearch && (
          <div className="h-full overflow-y-auto p-4 sm:p-5 lg:p-6">
            <SearchSection />
          </div>
        )}

        {/* 调查进度 */}
        {!showSearch && isSearching && (
          <div className="h-full overflow-y-auto">
            <InvestigationProgress
              companyName={companyName}
              stages={stages}
              conflicts={conflicts}
              consensus={consensus}
              licTaskId={licTaskId}
              onSkip={handleSkipToFallback}
              onCancel={handleCancelInvestigation}
              startTime={investigateStartTime}
            />
          </div>
        )}

        {/* 模块内容 — 示例模式 或 真实数据模式 */}
        {!showSearch && !isSearching && (
          <div className="h-full overflow-y-auto">
            <div className="p-4 sm:p-5 lg:p-6 space-y-4">
              {/* 企业概况 Hero — 仅在有调查数据时展示 */}
              {activeSection === 'overview' && activeData && (
                <CompanyProfile data={activeData.basicInfo} companyName={activeName} riskData={activeData.risk} />
              )}

              {/* 动态内容 */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeSection}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  {renderContent()}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
