/**
 * ComplianceCheck.tsx - 企业合规自检页面
 *
 * 功能：
 * 1. 企业信息表单（公司名称、行业、规模、地区）
 * 2. 自检维度选择（劳动用工、合同管理、数据合规、知识产权、税务合规、公司治理）
 * 3. 进度动画 + 结果展示（总分环形图、维度条形图、风险项分组、AI 建议）
 * 4. 历史记录列表
 *
 * 后端 API: /api/v1/compliance-check
 */

import { useState, useMemo, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import {
  cardStyle,
  heading,
  buttonStyle,
  iconSize,
  statusBadge,
  inputStyle,
  chartColors,
} from '@/lib/design-tokens'
import { PageContainer } from '@/components/ui/PageContainer'
import { complianceApi } from '@/lib/api'
import { toast } from 'sonner'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

// ===== 类型定义 =====

type PageStep = 'form' | 'checking' | 'result'

interface CompanyForm {
  name: string
  industry: string
  scale: string
  region: string
}

interface DimensionScore {
  name: string
  score: number
  fullMark: number
}

interface RiskItem {
  id: string
  dimension: string
  title: string
  description: string
  level: 'high' | 'medium' | 'low'
  suggestion: string
  lawRef?: string
}

interface CheckResult {
  totalScore: number
  dimensions: DimensionScore[]
  risks: RiskItem[]
  suggestions: string[]
  checkTime: string
}

interface HistoryRecord {
  id: string
  companyName: string
  totalScore: number
  checkTime: string
  dimensions: string[]
}

// ===== 常量 =====

const INDUSTRIES = [
  { value: 'technology', label: '科技/互联网' },
  { value: 'manufacturing', label: '制造业' },
  { value: 'finance', label: '金融' },
  { value: 'retail', label: '零售/电商' },
  { value: 'real_estate', label: '房地产' },
  { value: 'healthcare', label: '医疗健康' },
  { value: 'education', label: '教育培训' },
  { value: 'other', label: '其他' },
]

const SCALES = [
  { value: 'micro', label: '微型（<20人）' },
  { value: 'small', label: '小型（20-99人）' },
  { value: 'medium', label: '中型（100-499人）' },
  { value: 'large', label: '大型（500人以上）' },
]

const REGIONS = [
  { value: 'beijing', label: '北京' },
  { value: 'shanghai', label: '上海' },
  { value: 'guangdong', label: '广东' },
  { value: 'zhejiang', label: '浙江' },
  { value: 'jiangsu', label: '江苏' },
  { value: 'sichuan', label: '四川' },
  { value: 'other', label: '其他地区' },
]

const DIMENSIONS = [
  { key: 'labor', label: '劳动用工', icon: icons.Users },
  { key: 'contract', label: '合同管理', icon: icons.FileText },
  { key: 'data', label: '数据合规', icon: icons.Database },
  { key: 'ip', label: '知识产权', icon: icons.ShieldCheck },
  { key: 'tax', label: '税务合规', icon: icons.Calculator },
  { key: 'governance', label: '公司治理', icon: icons.Building },
]

// (MOCK_RESULT / MOCK_HISTORY 已移除 — 使用真实 API 调用)

// ===== 辅助函数 =====

function getScoreColor(score: number) {
  if (score >= 90) return 'text-emerald-600 dark:text-emerald-400'
  if (score >= 75) return 'text-primary'
  if (score >= 60) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

function getScoreBg(score: number) {
  if (score >= 90) return 'bg-emerald-50 dark:bg-emerald-950/30'
  if (score >= 75) return 'bg-primary/10'
  if (score >= 60) return 'bg-amber-50 dark:bg-amber-950/30'
  return 'bg-red-50 dark:bg-red-950/30'
}

function getScoreLabel(score: number) {
  if (score >= 90) return '优秀'
  if (score >= 75) return '良好'
  if (score >= 60) return '一般'
  return '需改进'
}

function getRiskBadge(level: string) {
  switch (level) {
    case 'high':
      return statusBadge.error
    case 'medium':
      return statusBadge.warning
    case 'low':
      return statusBadge.neutral
    default:
      return statusBadge.neutral
  }
}

function getRiskLabel(level: string) {
  switch (level) {
    case 'high':
      return '高风险'
    case 'medium':
      return '中风险'
    case 'low':
      return '低风险'
    default:
      return level
  }
}

function getRiskIcon(level: string) {
  switch (level) {
    case 'high':
      return <icons.XCircle className={`${iconSize.md} text-red-500 flex-shrink-0`} />
    case 'medium':
      return <icons.AlertTriangle className={`${iconSize.md} text-amber-500 flex-shrink-0`} />
    case 'low':
      return <icons.Info className={`${iconSize.md} text-muted-foreground flex-shrink-0`} />
    default:
      return <icons.AlertCircle className={`${iconSize.md} text-muted-foreground flex-shrink-0`} />
  }
}

// ===== 环形图中心标签 =====

function ScoreLabel({ score, cx, cy }: { score: number; cx: number; cy: number }) {
  return (
    <>
      <text x={cx} y={cy - 8} textAnchor="middle" className="fill-foreground text-3xl font-bold">
        {score}
      </text>
      <text x={cx} y={cy + 16} textAnchor="middle" className="fill-muted-foreground text-xs">
        {getScoreLabel(score)}
      </text>
    </>
  )
}

// ===== 主组件 =====

export default function ComplianceCheck() {
  const [step, setStep] = useState<PageStep>('form')
  const [form, setForm] = useState<CompanyForm>({
    name: '',
    industry: '',
    scale: '',
    region: '',
  })
  const [selectedDimensions, setSelectedDimensions] = useState<Set<string>>(
    new Set(DIMENSIONS.map((d) => d.key))
  )
  const [result, setResult] = useState<CheckResult | null>(null)
  const [expandedRisks, setExpandedRisks] = useState<Set<string>>(new Set())
  const [checkProgress, setCheckProgress] = useState(0)
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  // 表单是否可提交
  const canSubmit =
    form.name.trim() && form.industry && form.scale && form.region && selectedDimensions.size > 0

  // 维度切换
  const toggleDimension = (key: string) => {
    setSelectedDimensions((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  // 风险展开/收起
  const toggleRisk = (id: string) => {
    setExpandedRisks((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  // 开始自检
  const handleStartCheck = async () => {
    setStep('checking')
    setCheckProgress(0)

    // 模拟进度动画（API 调用期间给用户视觉反馈）
    const progressSteps = [10, 25, 40, 55, 70]
    let progressIdx = 0
    const progressTimer = setInterval(() => {
      if (progressIdx < progressSteps.length) {
        setCheckProgress(progressSteps[progressIdx])
        progressIdx++
      }
    }, 400)

    try {
      // 构建答案列表：选中的维度视为合规项
      const answers = Array.from(selectedDimensions).map(dim => ({
        item_id: dim,
        answer: true,
      }))

      const data = await complianceApi.evaluate({
        industry: form.industry,
        company_size: form.scale,
        answers,
      })

      clearInterval(progressTimer)
      setCheckProgress(100)
      await new Promise((r) => setTimeout(r, 300))

      // 适配 API 返回的数据结构到 CheckResult
      const apiResult: CheckResult = {
        totalScore: data.totalScore ?? data.total_score ?? data.score ?? 0,
        dimensions: data.dimensions ?? data.dimension_scores?.map((d: any) => ({
          name: d.name || d.dimension,
          score: d.score,
          fullMark: 100,
        })) ?? [],
        risks: data.risks ?? data.risk_items?.map((r: any, i: number) => ({
          id: r.id || `r${i}`,
          dimension: r.dimension || '',
          title: r.title || r.name || '',
          description: r.description || '',
          level: r.level || r.severity || 'medium',
          suggestion: r.suggestion || r.recommendation || '',
          lawRef: r.lawRef || r.law_ref || undefined,
        })) ?? [],
        suggestions: data.suggestions ?? data.recommendations ?? [],
        checkTime: data.checkTime ?? data.check_time ?? new Date().toLocaleString('zh-CN'),
      }

      setResult(apiResult)
      setStep('result')
    } catch (err: any) {
      clearInterval(progressTimer)
      toast.error('合规检测失败: ' + (err.message || '请重试'))
      setStep('form')
    }
  }

  // 完成检测后，将结果追加到本地历史记录
  useEffect(() => {
    if (result && step === 'result') {
      const record: HistoryRecord = {
        id: `h_${Date.now()}`,
        companyName: form.name,
        totalScore: result.totalScore,
        checkTime: result.checkTime,
        dimensions: result.dimensions.map(d => d.name),
      }
      setHistory(prev => [record, ...prev])
    }
  }, [result, step])

  // 重新检测
  const handleReset = () => {
    setStep('form')
    setResult(null)
    setExpandedRisks(new Set())
    setCheckProgress(0)
  }

  // 风险按等级分组
  const groupedRisks = useMemo(() => {
    if (!result) return { high: [], medium: [], low: [] }
    const groups: Record<string, RiskItem[]> = { high: [], medium: [], low: [] }
    for (const risk of result.risks) {
      if (groups[risk.level]) {
        groups[risk.level].push(risk)
      }
    }
    return groups
  }, [result])

  // 环形图数据
  const pieData = useMemo(() => {
    if (!result) return []
    return [
      { name: '得分', value: result.totalScore },
      { name: '扣分', value: 100 - result.totalScore },
    ]
  }, [result])

  // 条形图数据
  const barData = useMemo(() => {
    if (!result) return []
    return result.dimensions.map((d) => ({
      name: d.name,
      score: d.score,
    }))
  }, [result])

  // 条形图 bar 颜色
  const getBarColor = (score: number) => {
    if (score >= 90) return 'hsl(160, 60%, 45%)'
    if (score >= 75) return chartColors[0]
    if (score >= 60) return 'hsl(35, 90%, 55%)'
    return 'hsl(350, 65%, 55%)'
  }

  return (
    <PageContainer title="企业合规自检" description="AI 智能分析企业合规状况，快速识别风险">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* ===== 主区域 ===== */}
        <div className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            {/* ===== Step 1: 表单 ===== */}
            {step === 'form' && (
              <motion.div
                key="form"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                {/* 企业信息 */}
                <div className={cardStyle.base}>
                  <h3 className={`${heading.section} mb-4 flex items-center gap-2`}>
                    <icons.Building className={iconSize.md} />
                    企业信息
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className={`${heading.micro} block mb-1.5`}>公司名称</label>
                      <input
                        type="text"
                        placeholder="请输入公司名称"
                        value={form.name}
                        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                        className={inputStyle.search}
                      />
                    </div>
                    <div>
                      <label className={`${heading.micro} block mb-1.5`}>所属行业</label>
                      <select
                        value={form.industry}
                        onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))}
                        className={inputStyle.search}
                      >
                        <option value="">请选择行业</option>
                        {INDUSTRIES.map((i) => (
                          <option key={i.value} value={i.value}>
                            {i.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={`${heading.micro} block mb-1.5`}>企业规模</label>
                      <select
                        value={form.scale}
                        onChange={(e) => setForm((f) => ({ ...f, scale: e.target.value }))}
                        className={inputStyle.search}
                      >
                        <option value="">请选择规模</option>
                        {SCALES.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={`${heading.micro} block mb-1.5`}>所在地区</label>
                      <select
                        value={form.region}
                        onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))}
                        className={inputStyle.search}
                      >
                        <option value="">请选择地区</option>
                        {REGIONS.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* 自检维度 */}
                <div className={cardStyle.base}>
                  <h3 className={`${heading.section} mb-4 flex items-center gap-2`}>
                    <icons.ClipboardCheck className={iconSize.md} />
                    自检维度
                  </h3>
                  <p className={`${heading.muted} mb-4`}>
                    选择需要检测的合规维度（至少选择一项）
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {DIMENSIONS.map((dim) => {
                      const Icon = dim.icon
                      const selected = selectedDimensions.has(dim.key)
                      return (
                        <button
                          key={dim.key}
                          onClick={() => toggleDimension(dim.key)}
                          className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                            selected
                              ? 'border-primary bg-primary/5 text-foreground'
                              : 'border-border bg-background text-muted-foreground hover:border-primary/30'
                          }`}
                        >
                          <div
                            className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                              selected
                                ? 'bg-primary border-primary text-white'
                                : 'border-muted-foreground/30 bg-background'
                            }`}
                          >
                            {selected && <icons.Check className="w-3 h-3" />}
                          </div>
                          <Icon className={`${iconSize.sm} flex-shrink-0 ${selected ? 'text-primary' : ''}`} />
                          <span className="text-sm font-medium">{dim.label}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* 提交按钮 */}
                <button
                  onClick={handleStartCheck}
                  disabled={!canSubmit}
                  className={`${buttonStyle.primary} w-full py-3 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <icons.ShieldCheck className={iconSize.md} />
                  开始合规自检
                </button>
              </motion.div>
            )}

            {/* ===== Step 2: 检测进度 ===== */}
            {step === 'checking' && (
              <motion.div
                key="checking"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="flex flex-col items-center justify-center py-20"
              >
                <div className={`${cardStyle.base} w-full max-w-md text-center`}>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    className="inline-block mb-6"
                  >
                    <icons.Loader2 className={`${iconSize['2xl']} text-primary`} />
                  </motion.div>
                  <h3 className={heading.section}>AI 正在分析合规状况...</h3>
                  <p className={`${heading.muted} mt-2 mb-6`}>
                    正在检测 {selectedDimensions.size} 个维度，请稍候
                  </p>
                  {/* 进度条 */}
                  <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-primary rounded-full"
                      initial={{ width: '0%' }}
                      animate={{ width: `${checkProgress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                  <p className={`${heading.micro} mt-2`}>{checkProgress}%</p>
                  {/* 检测项动画 */}
                  <div className="mt-6 space-y-2">
                    {DIMENSIONS.filter((d) => selectedDimensions.has(d.key)).map((dim, i) => {
                      const done = checkProgress > ((i + 1) / selectedDimensions.size) * 90
                      return (
                        <div
                          key={dim.key}
                          className={`flex items-center gap-2 text-sm transition-colors ${
                            done ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'
                          }`}
                        >
                          {done ? (
                            <icons.CheckCircle className={iconSize.sm} />
                          ) : (
                            <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
                          )}
                          {dim.label}
                        </div>
                      )
                    })}
                  </div>
                </div>
              </motion.div>
            )}

            {/* ===== Step 3: 结果展示 ===== */}
            {step === 'result' && result && (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-6"
              >
                {/* 总分 + 维度条形图 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* 总分环形图 */}
                  <div className={`${cardStyle.base} flex flex-col items-center`}>
                    <h3 className={`${heading.section} mb-4 self-start`}>合规总分</h3>
                    <div className="w-48 h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={55}
                            outerRadius={80}
                            startAngle={90}
                            endAngle={-270}
                            dataKey="value"
                            stroke="none"
                          >
                            <Cell
                              fill={
                                result.totalScore >= 90
                                  ? 'hsl(160, 60%, 45%)'
                                  : result.totalScore >= 75
                                    ? chartColors[0]
                                    : result.totalScore >= 60
                                      ? 'hsl(35, 90%, 55%)'
                                      : 'hsl(350, 65%, 55%)'
                              }
                            />
                            <Cell fill="hsl(var(--muted))" />
                          </Pie>
                          <text
                            x="50%"
                            y="46%"
                            textAnchor="middle"
                            dominantBaseline="middle"
                            className="fill-foreground"
                            style={{ fontSize: '28px', fontWeight: 700 }}
                          >
                            {result.totalScore}
                          </text>
                          <text
                            x="50%"
                            y="60%"
                            textAnchor="middle"
                            dominantBaseline="middle"
                            className="fill-muted-foreground"
                            style={{ fontSize: '12px' }}
                          >
                            {getScoreLabel(result.totalScore)}
                          </text>
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex items-center gap-4 mt-2">
                      <span
                        className={`text-sm font-medium px-3 py-1 rounded-lg ${getScoreBg(result.totalScore)} ${getScoreColor(result.totalScore)}`}
                      >
                        {getScoreLabel(result.totalScore)}
                      </span>
                      <span className={heading.muted}>
                        {result.risks.filter((r) => r.level === 'high').length} 项高风险
                      </span>
                    </div>
                  </div>

                  {/* 维度评分条形图 */}
                  <div className={cardStyle.base}>
                    <h3 className={`${heading.section} mb-4`}>各维度评分</h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
                          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                          <YAxis
                            type="category"
                            dataKey="name"
                            width={70}
                            tick={{ fontSize: 12 }}
                            stroke="hsl(var(--muted-foreground))"
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: 'hsl(var(--background))',
                              border: '1px solid hsl(var(--border))',
                              borderRadius: '8px',
                              fontSize: '12px',
                            }}
                            formatter={(value: number) => [`${value} 分`, '评分']}
                          />
                          <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={20}>
                            {barData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={getBarColor(entry.score)} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* 风险项分组 */}
                <div className={cardStyle.base}>
                  <h3 className={`${heading.section} mb-4 flex items-center gap-2`}>
                    <icons.AlertTriangle className={`${iconSize.md} text-amber-500`} />
                    风险项目（{result.risks.length} 项）
                  </h3>

                  {/* 高风险 */}
                  {groupedRisks.high.length > 0 && (
                    <RiskGroup
                      label="高风险"
                      badge={statusBadge.error}
                      risks={groupedRisks.high}
                      expandedRisks={expandedRisks}
                      toggleRisk={toggleRisk}
                    />
                  )}

                  {/* 中风险 */}
                  {groupedRisks.medium.length > 0 && (
                    <RiskGroup
                      label="中风险"
                      badge={statusBadge.warning}
                      risks={groupedRisks.medium}
                      expandedRisks={expandedRisks}
                      toggleRisk={toggleRisk}
                    />
                  )}

                  {/* 低风险 */}
                  {groupedRisks.low.length > 0 && (
                    <RiskGroup
                      label="低风险"
                      badge={statusBadge.neutral}
                      risks={groupedRisks.low}
                      expandedRisks={expandedRisks}
                      toggleRisk={toggleRisk}
                    />
                  )}
                </div>

                {/* AI 改善建议 */}
                <div className={cardStyle.base}>
                  <h3 className={`${heading.section} mb-4 flex items-center gap-2`}>
                    <icons.Lightbulb className={`${iconSize.md} text-primary`} />
                    AI 改善建议
                  </h3>
                  <div className="space-y-3">
                    {result.suggestions.map((sug, i) => (
                      <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-primary/5">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-bold">
                          {i + 1}
                        </span>
                        <p className="text-sm text-foreground leading-relaxed">{sug}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex flex-col sm:flex-row items-center gap-3">
                  <button onClick={handleReset} className={`${buttonStyle.secondary} w-full sm:w-auto`}>
                    <icons.RefreshCw className={`${iconSize.sm} mr-2`} />
                    重新检测
                  </button>
                  <button
                    onClick={() => window.dispatchEvent(new CustomEvent('auth:redirect', { detail: '/chat' }))}
                    className={`${buttonStyle.primary} w-full sm:flex-1 flex items-center justify-center gap-2`}
                  >
                    <icons.Chat className={iconSize.sm} />
                    咨询 AI 法务助手
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ===== 右侧：历史记录 ===== */}
        <div className="w-full lg:w-72 xl:w-80 flex-shrink-0">
          <div className={cardStyle.base}>
            <h3 className={`${heading.section} mb-4 flex items-center gap-2`}>
              <icons.Clock className={iconSize.md} />
              检测历史
            </h3>
            {history.length === 0 ? (
              <div className="text-center py-8">
                <icons.FileSearch className={`${iconSize.xl} text-muted-foreground mx-auto mb-3`} />
                <p className={heading.muted}>{historyLoading ? '加载中...' : '暂无检测记录'}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {history.map((record) => (
                  <button
                    key={record.id}
                    className="w-full text-left p-3 rounded-lg border border-border hover:border-primary/20 hover:bg-muted/30 transition-all"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-sm font-semibold ${getScoreColor(record.totalScore)}`}>
                        {record.totalScore} 分
                      </span>
                      <span className={heading.micro}>{record.checkTime.split(' ')[0]}</span>
                    </div>
                    <p className="text-sm text-foreground truncate">{record.companyName}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {record.dimensions.slice(0, 3).map((d) => (
                        <span
                          key={d}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                        >
                          {d}
                        </span>
                      ))}
                      {record.dimensions.length > 3 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                          +{record.dimensions.length - 3}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </PageContainer>
  )
}

// ===== 风险分组子组件 =====

function RiskGroup({
  label,
  badge,
  risks,
  expandedRisks,
  toggleRisk,
}: {
  label: string
  badge: string
  risks: RiskItem[]
  expandedRisks: Set<string>
  toggleRisk: (id: string) => void
}) {
  return (
    <div className="mb-4 last:mb-0">
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${badge}`}>
          {label}
        </span>
        <span className={heading.micro}>{risks.length} 项</span>
      </div>
      <div className="space-y-2">
        {risks.map((risk) => {
          const expanded = expandedRisks.has(risk.id)
          return (
            <div key={risk.id} className="rounded-lg border border-border overflow-hidden">
              <button
                onClick={() => toggleRisk(risk.id)}
                className="w-full flex items-center gap-3 p-3 text-left hover:bg-muted/30 transition-colors"
              >
                {getRiskIcon(risk.level)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{risk.title}</p>
                  <span className={heading.micro}>{risk.dimension}</span>
                </div>
                <icons.ChevronDown
                  className={`${iconSize.sm} text-muted-foreground transition-transform ${
                    expanded ? 'rotate-180' : ''
                  }`}
                />
              </button>
              <AnimatePresence>
                {expanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="px-3 pb-3 pt-0 border-t border-border">
                      <div className="pt-3 space-y-3">
                        <div>
                          <p className={`${heading.micro} mb-1`}>风险描述</p>
                          <p className="text-sm text-foreground">{risk.description}</p>
                        </div>
                        {risk.lawRef && (
                          <div>
                            <p className={`${heading.micro} mb-1`}>法律依据</p>
                            <p className="text-sm text-primary">{risk.lawRef}</p>
                          </div>
                        )}
                        <div>
                          <p className={`${heading.micro} mb-1`}>改善建议</p>
                          <p className="text-sm text-foreground">{risk.suggestion}</p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
    </div>
  )
}
