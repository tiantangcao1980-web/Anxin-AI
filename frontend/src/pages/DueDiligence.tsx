/**
 * 智能调查 — 深度整合智能搜索 + 尽职调查 + 舆情监控
 *
 * Tab1: 智能搜索（4 种模式：混合/关键词/语义/RAG）
 * Tab2: 尽职调查（风险雷达 + 诉讼记录）
 * Tab3: 舆情监控（舆情概览 + 预警 + 监控配置）
 */
import { useState, useCallback } from 'react'
import { PageContainer } from '@/components/ui/PageContainer'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { icons } from '@/lib/icons'
import { cardStyle, heading, buttonStyle, statusBadge, statusColor, inputStyle } from '@/lib/design-tokens'
import { knowledgeApi } from '@/lib/api'
import { toast } from 'sonner'
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend, PieChart, Pie, Cell,
} from 'recharts'

// ===== 类型定义 =====

type SearchMode = 'hybrid' | 'keyword' | 'vector' | 'rag'

interface SearchResult {
  id?: string
  title?: string
  content: string
  source?: string
  score?: number
  metadata?: Record<string, any>
}

interface RAGAnswer {
  answer: string
  sources: any[]
  context_used: boolean
  chunks_used?: number
}

// ===== Mock 数据 =====

// @mock-data FALLBACK
const MOCK_RISK_RADAR = [
  { dimension: '经营风险', score: 72 },
  { dimension: '诉讼风险', score: 58 },
  { dimension: '信用风险', score: 85 },
  { dimension: '合规风险', score: 63 },
  { dimension: '关联风险', score: 44 },
]

// @mock-data FALLBACK
const MOCK_LITIGATION_RECORDS = [
  { id: '1', caseNo: '(2025)京01民初12345号', title: '买卖合同纠纷', role: '被告', court: '北京市第一中级人民法院', date: '2025-11-15', status: '审理中', amount: '¥1,200,000' },
  { id: '2', caseNo: '(2025)沪02民终6789号', title: '知识产权侵权纠纷', role: '原告', court: '上海知识产权法院', date: '2025-08-22', status: '已结案', amount: '¥3,500,000' },
  { id: '3', caseNo: '(2024)粤03执异234号', title: '执行异议之诉', role: '被执行人', court: '深圳市中级人民法院', date: '2024-12-03', status: '执行中', amount: '¥800,000' },
  { id: '4', caseNo: '(2024)京0105民初56789号', title: '劳动争议', role: '被告', court: '北京市朝阳区人民法院', date: '2024-06-10', status: '已结案', amount: '¥150,000' },
]

// @mock-data FALLBACK
const MOCK_RISK_DETAILS = [
  { category: '经营风险', level: 'high' as const, description: '近12个月内经营异常记录2条', date: '2025-10-20' },
  { category: '诉讼风险', level: 'medium' as const, description: '作为被告涉及3起未结诉讼', date: '2025-11-15' },
  { category: '信用风险', level: 'low' as const, description: '信用评级AA，近期无负面记录', date: '2025-09-01' },
  { category: '合规风险', level: 'medium' as const, description: '行政处罚记录1条（环保相关）', date: '2025-07-08' },
  { category: '关联风险', level: 'high' as const, description: '关联企业中2家存在失信记录', date: '2025-08-30' },
]

// @mock-data FALLBACK
const MOCK_SENTIMENT_OVERVIEW = { positive: 128, neutral: 342, negative: 47 }

// @mock-data FALLBACK
const MOCK_SENTIMENT_TIMELINE = [
  { date: '03-22', positive: 15, neutral: 40, negative: 5 },
  { date: '03-23', positive: 18, neutral: 38, negative: 8 },
  { date: '03-24', positive: 12, neutral: 45, negative: 3 },
  { date: '03-25', positive: 20, neutral: 35, negative: 10 },
  { date: '03-26', positive: 22, neutral: 42, negative: 6 },
  { date: '03-27', positive: 16, neutral: 50, negative: 4 },
  { date: '03-28', positive: 25, neutral: 32, negative: 11 },
]

// @mock-data FALLBACK
const MOCK_ALERTS = [
  { id: '1', severity: 'critical' as const, title: '重大负面舆情：环保处罚通报', source: '生态环境部官网', time: '2小时前', summary: '企业因违规排放被处以50万元罚款' },
  { id: '2', severity: 'warning' as const, title: '诉讼风险提醒：新增被告案件', source: '中国裁判文书网', time: '5小时前', summary: '新增一起合同纠纷案件，涉案金额200万元' },
  { id: '3', severity: 'info' as const, title: '行业政策变动：新合规要求', source: '国务院法制办', time: '1天前', summary: '行业新规将于下月生效，涉及数据安全合规' },
  { id: '4', severity: 'warning' as const, title: '关联企业信用降级', source: '企查查', time: '2天前', summary: '关联公司信用评级从A降至BBB' },
]

// @mock-data FALLBACK
const MOCK_MONITOR_KEYWORDS = ['公司名称', '法定代表人', '商标侵权', '环保处罚', '失信被执行人']

const SEARCH_MODES: { key: SearchMode; label: string; desc: string }[] = [
  { key: 'hybrid', label: '混合检索', desc: '关键词 + 向量综合排序' },
  { key: 'keyword', label: '关键词', desc: '精确匹配关键词' },
  { key: 'vector', label: '语义检索', desc: '基于语义相似度' },
  { key: 'rag', label: 'RAG 问答', desc: 'AI 智能问答' },
]

const PIE_COLORS = ['#34C759', '#8E8E93', '#FF3B30']

// ===== 子组件 =====

function SearchTab({ keyword }: { keyword: string }) {
  const [query, setQuery] = useState(keyword)
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  const highlightText = (text: string, q: string) => {
    if (!q.trim() || !text) return text
    try {
      const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'))
      return parts.map((part, i) =>
        part.toLowerCase() === q.toLowerCase()
          ? <mark key={i} className="bg-yellow-200 dark:bg-yellow-800 rounded px-0.5">{part}</mark>
          : part
      )
    } catch {
      return text
    }
  }

  return (
    <div className="space-y-4">
      {/* 搜索框 */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入搜索关键词或问题..."
            className={inputStyle.search + ' pl-10'}
          />
        </div>
        <button onClick={handleSearch} disabled={loading || !query.trim()} className={buttonStyle.primary + ' min-w-[80px]'}>
          {loading ? <icons.Refresh className="w-4 h-4 animate-spin" /> : '搜索'}
        </button>
      </div>

      {/* 模式切换 */}
      <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1">
        {SEARCH_MODES.map(m => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap shrink-0 ${
              mode === m.key
                ? 'bg-primary text-white'
                : 'bg-muted text-muted-foreground hover:text-foreground'
            }`}
            title={m.desc}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* 搜索结果 */}
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
            <icons.Refresh className="w-6 h-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">搜索中...</span>
          </div>
        )}

        {/* RAG 回答 */}
        {ragAnswer && !loading && (
          <div className="space-y-4">
            <div className={cardStyle.highlight}>
              <div className="flex items-center gap-2 mb-3">
                <icons.Sparkles className="w-4 h-4 text-primary" />
                <span className={heading.section}>AI 回答</span>
              </div>
              <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                {ragAnswer.answer}
              </div>
              {ragAnswer.chunks_used && (
                <p className="text-xs text-muted-foreground mt-3">
                  参考了 {ragAnswer.chunks_used} 个知识片段
                </p>
              )}
            </div>
            {ragAnswer.sources?.length > 0 && (
              <div>
                <h3 className={heading.card + ' mb-2'}>参考来源</h3>
                <div className="space-y-2">
                  {ragAnswer.sources.map((s: any, i: number) => (
                    <div key={i} className="text-xs p-2 rounded-lg bg-muted/50 text-muted-foreground">
                      {s.title || s.source || `来源 ${i + 1}`}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 常规结果列表 */}
        {hasSearched && !loading && results.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-3">找到 {results.length} 条结果</p>
            <div className="space-y-3">
              {results.map((r, i) => (
                <div key={r.id || i} className={cardStyle.interactive}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <h3 className={heading.card + ' mb-1'}>
                        {r.title ? highlightText(r.title, query) : `结果 ${i + 1}`}
                      </h3>
                      <p className="text-xs text-muted-foreground line-clamp-3">
                        {highlightText(r.content?.slice(0, 300) || '', query)}
                      </p>
                      {r.source && (
                        <div className="flex items-center gap-1 mt-2">
                          <icons.Link className="w-3 h-3 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">{r.source}</span>
                        </div>
                      )}
                    </div>
                    {r.score !== undefined && (
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        r.score > 0.8 ? statusColor.success : r.score > 0.5 ? statusColor.warning : statusColor.neutral
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
            <p className="text-xs mt-1">尝试使用不同的关键词或切换搜索模式</p>
          </div>
        )}
      </div>
    </div>
  )
}

function DueDiligenceTab({ keyword }: { keyword: string }) {
  const [target, setTarget] = useState(keyword)
  const [loading, setLoading] = useState(false)
  const [hasResult, setHasResult] = useState(false)

  const handleInvestigate = useCallback(() => {
    if (!target.trim()) return
    setLoading(true)
    // @mock-data FALLBACK — 模拟 API 调用
    setTimeout(() => {
      setLoading(false)
      setHasResult(true)
    }, 1500)
  }, [target])

  const riskLevelStyle = (level: 'high' | 'medium' | 'low') => {
    switch (level) {
      case 'high': return statusBadge.error
      case 'medium': return statusBadge.warning
      case 'low': return statusBadge.success
    }
  }

  const riskLevelLabel = (level: 'high' | 'medium' | 'low') => {
    switch (level) {
      case 'high': return '高风险'
      case 'medium': return '中风险'
      case 'low': return '低风险'
    }
  }

  return (
    <div className="space-y-6">
      {/* 调查对象输入 */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <icons.Building className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={target}
            onChange={e => setTarget(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleInvestigate()}
            placeholder="输入企业名称或个人姓名..."
            className={inputStyle.search + ' pl-10'}
          />
        </div>
        <button onClick={handleInvestigate} disabled={loading || !target.trim()} className={buttonStyle.primary + ' min-w-[100px]'}>
          {loading ? <icons.Refresh className="w-4 h-4 animate-spin" /> : '开始调查'}
        </button>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-20">
          <icons.Refresh className="w-8 h-8 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">正在进行尽职调查...</p>
          <p className="text-xs text-muted-foreground mt-1">收集企业工商、诉讼、信用、合规等多维度数据</p>
        </div>
      )}

      {!hasResult && !loading && (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <icons.FileSearch className="w-16 h-16 mb-4 opacity-20" />
          <p className="text-sm">输入企业名称，启动智能尽职调查</p>
          <p className="text-xs mt-1 opacity-60">涵盖经营、诉讼、信用、合规、关联五大维度</p>
        </div>
      )}

      {hasResult && !loading && (
        <>
          {/* 风险雷达图 + 风险概要 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className={cardStyle.base}>
              <h3 className={heading.section + ' mb-4'}>风险雷达图</h3>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={MOCK_RISK_RADAR}>
                  <PolarGrid strokeDasharray="3 3" />
                  <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 12 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Radar name="风险评分" dataKey="score" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.2} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className={cardStyle.base}>
              <h3 className={heading.section + ' mb-4'}>风险详情</h3>
              <div className="space-y-3">
                {MOCK_RISK_DETAILS.map((item, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${riskLevelStyle(item.level)}`}>
                      {riskLevelLabel(item.level)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{item.category}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">{item.date}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 诉讼记录 */}
          <div className={cardStyle.base}>
            <h3 className={heading.section + ' mb-4'}>诉讼记录</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="pb-3 pr-4 font-medium text-muted-foreground">案号</th>
                    <th className="pb-3 pr-4 font-medium text-muted-foreground">案由</th>
                    <th className="pb-3 pr-4 font-medium text-muted-foreground">身份</th>
                    <th className="pb-3 pr-4 font-medium text-muted-foreground">法院</th>
                    <th className="pb-3 pr-4 font-medium text-muted-foreground">日期</th>
                    <th className="pb-3 pr-4 font-medium text-muted-foreground">涉案金额</th>
                    <th className="pb-3 font-medium text-muted-foreground">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_LITIGATION_RECORDS.map(record => (
                    <tr key={record.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                      <td className="py-3 pr-4 text-xs font-mono text-primary">{record.caseNo}</td>
                      <td className="py-3 pr-4">{record.title}</td>
                      <td className="py-3 pr-4">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          record.role === '被告' || record.role === '被执行人' ? statusBadge.error : statusBadge.info
                        }`}>
                          {record.role}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-xs text-muted-foreground">{record.court}</td>
                      <td className="py-3 pr-4 text-xs text-muted-foreground">{record.date}</td>
                      <td className="py-3 pr-4 font-medium">{record.amount}</td>
                      <td className="py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          record.status === '已结案' ? statusBadge.success
                            : record.status === '执行中' ? statusBadge.warning
                            : statusBadge.info
                        }`}>
                          {record.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function SentimentTab({ keyword }: { keyword: string }) {
  const [monitorKeywords, setMonitorKeywords] = useState(MOCK_MONITOR_KEYWORDS)
  const [newKeyword, setNewKeyword] = useState('')
  const [generating, setGenerating] = useState(false)

  const addKeyword = () => {
    if (!newKeyword.trim()) return
    if (monitorKeywords.includes(newKeyword.trim())) {
      toast.error('关键词已存在')
      return
    }
    setMonitorKeywords([...monitorKeywords, newKeyword.trim()])
    setNewKeyword('')
    toast.success('关键词已添加')
  }

  const removeKeyword = (kw: string) => {
    setMonitorKeywords(monitorKeywords.filter(k => k !== kw))
    toast.success('关键词已移除')
  }

  const handleGenerateReport = () => {
    setGenerating(true)
    setTimeout(() => {
      setGenerating(false)
      toast.success('舆情报告已生成')
    }, 2000)
  }

  const pieData = [
    { name: '正面', value: MOCK_SENTIMENT_OVERVIEW.positive },
    { name: '中立', value: MOCK_SENTIMENT_OVERVIEW.neutral },
    { name: '负面', value: MOCK_SENTIMENT_OVERVIEW.negative },
  ]

  const severityStyle = (severity: 'critical' | 'warning' | 'info') => {
    switch (severity) {
      case 'critical': return statusBadge.error
      case 'warning': return statusBadge.warning
      case 'info': return statusBadge.info
    }
  }

  const severityLabel = (severity: 'critical' | 'warning' | 'info') => {
    switch (severity) {
      case 'critical': return '严重'
      case 'warning': return '警告'
      case 'info': return '提示'
    }
  }

  return (
    <div className="space-y-6">
      {/* 舆情概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className={cardStyle.base + ' text-center'}>
          <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-emerald-50 dark:bg-emerald-950/30 flex items-center justify-center">
            <icons.TrendingUp className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{MOCK_SENTIMENT_OVERVIEW.positive}</p>
          <p className="text-xs text-muted-foreground mt-1">正面舆情</p>
        </div>
        <div className={cardStyle.base + ' text-center'}>
          <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-muted flex items-center justify-center">
            <icons.Minus className="w-5 h-5 text-muted-foreground" />
          </div>
          <p className="text-2xl font-bold text-muted-foreground">{MOCK_SENTIMENT_OVERVIEW.neutral}</p>
          <p className="text-xs text-muted-foreground mt-1">中立舆情</p>
        </div>
        <div className={cardStyle.base + ' text-center'}>
          <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-red-50 dark:bg-red-950/30 flex items-center justify-center">
            <icons.TrendingDown className="w-5 h-5 text-red-600 dark:text-red-400" />
          </div>
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">{MOCK_SENTIMENT_OVERVIEW.negative}</p>
          <p className="text-xs text-muted-foreground mt-1">负面舆情</p>
        </div>
      </div>

      {/* 舆情趋势 + 分布 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={cardStyle.base + ' lg:col-span-2'}>
          <h3 className={heading.section + ' mb-4'}>舆情趋势</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={MOCK_SENTIMENT_TIMELINE}>
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
          <h3 className={heading.section + ' mb-4'}>舆情分布</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {pieData.map((_, index) => (
                  <Cell key={index} fill={PIE_COLORS[index]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 预警列表 */}
      <div className={cardStyle.base}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={heading.section}>舆情预警</h3>
          <button onClick={handleGenerateReport} disabled={generating} className={buttonStyle.secondary + ' text-xs'}>
            {generating ? (
              <><icons.Refresh className="w-3 h-3 animate-spin mr-1 inline" />生成中...</>
            ) : (
              <><icons.FileText className="w-3 h-3 mr-1 inline" />生成舆情报告</>
            )}
          </button>
        </div>
        <div className="space-y-3">
          {MOCK_ALERTS.map(alert => (
            <div key={alert.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
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
            </div>
          ))}
        </div>
      </div>

      {/* 监控配置 */}
      <div className={cardStyle.base}>
        <h3 className={heading.section + ' mb-4'}>监控关键词配置</h3>
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newKeyword}
            onChange={e => setNewKeyword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addKeyword()}
            placeholder="添加监控关键词..."
            className={inputStyle.search + ' flex-1'}
          />
          <button onClick={addKeyword} disabled={!newKeyword.trim()} className={buttonStyle.primary}>
            添加
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {monitorKeywords.map(kw => (
            <span key={kw} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
              {kw}
              <button onClick={() => removeKeyword(kw)} className="hover:text-destructive transition-colors">
                <icons.X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

// ===== 主组件 =====

export default function DueDiligence() {
  const [searchKeyword, setSearchKeyword] = useState('')
  const [activeTab, setActiveTab] = useState('search')
  const [committedKeyword, setCommittedKeyword] = useState('')

  const handleGlobalSearch = () => {
    setCommittedKeyword(searchKeyword)
  }

  return (
    <PageContainer title="智能调查" description="搜索 / 尽调 / 舆情 -- 一站式智能法律信息调查">
      {/* 顶部统一搜索栏 */}
      <div className="flex gap-3 items-center">
        <div className="flex-1 relative">
          <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchKeyword}
            onChange={e => setSearchKeyword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleGlobalSearch()}
            placeholder="搜索企业、法律问题、关键词..."
            className={inputStyle.search + ' pl-10'}
          />
        </div>
        <button onClick={handleGlobalSearch} className={buttonStyle.primary}>
          <icons.Search className="w-4 h-4 mr-1.5 inline" />
          搜索
        </button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="search">
            <icons.Search className="w-4 h-4 mr-1.5" />
            智能搜索
          </TabsTrigger>
          <TabsTrigger value="duediligence">
            <icons.FileSearch className="w-4 h-4 mr-1.5" />
            尽职调查
          </TabsTrigger>
          <TabsTrigger value="sentiment">
            <icons.Activity className="w-4 h-4 mr-1.5" />
            舆情监控
          </TabsTrigger>
        </TabsList>

        <TabsContent value="search">
          <SearchTab keyword={committedKeyword} />
        </TabsContent>

        <TabsContent value="duediligence">
          <DueDiligenceTab keyword={committedKeyword} />
        </TabsContent>

        <TabsContent value="sentiment">
          <SentimentTab keyword={committedKeyword} />
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
