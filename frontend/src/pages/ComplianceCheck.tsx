/**
 * ComplianceCheck · 企业合规自检（Editorial Luxury 改造 · Phase 2.5）
 *
 * 旧版：PageContainer + cardStyle.base 圆角卡 + bg-primary/5 选项 + 多色 PieChart + statusBadge。
 * 新版：EditorialPageHeader + 1px hairline 区块 + 单色环形 + tone-only Risk chip + 衬线序号。
 *
 * 3 步流程：form → checking → result
 * 6 个维度自检：劳动用工/合同管理/数据合规/知识产权/税务合规/公司治理
 */
import { useState, useMemo, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import {
  Building, ClipboardCheck, ShieldCheck, AlertTriangle, Loader2,
  CheckCircle, XCircle, Info, AlertCircle, Lightbulb, Clock, RefreshCw,
  MessageSquare, ChevronDown, Users, FileText, Database, Calculator, Check,
} from 'lucide-react'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'

import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import { complianceApi } from '@/lib/api'
import { cn } from '@/components/ui/utils'

type PageStep = 'form' | 'checking' | 'result'

interface CompanyForm {
  name: string
  industry: string
  scale: string
  region: string
}
interface DimensionScore { name: string; score: number; fullMark: number }
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

const INDUSTRIES = [
  { value: 'technology',    label: '科技/互联网' },
  { value: 'manufacturing', label: '制造业' },
  { value: 'finance',       label: '金融' },
  { value: 'retail',        label: '零售/电商' },
  { value: 'real_estate',   label: '房地产' },
  { value: 'healthcare',    label: '医疗健康' },
  { value: 'education',     label: '教育培训' },
  { value: 'other',         label: '其他' },
]
const SCALES = [
  { value: 'micro',  label: '微型（<20人）' },
  { value: 'small',  label: '小型（20-99人）' },
  { value: 'medium', label: '中型（100-499人）' },
  { value: 'large',  label: '大型（500人以上）' },
]
const REGIONS = [
  { value: 'beijing',   label: '北京' },
  { value: 'shanghai',  label: '上海' },
  { value: 'guangdong', label: '广东' },
  { value: 'zhejiang',  label: '浙江' },
  { value: 'jiangsu',   label: '江苏' },
  { value: 'sichuan',   label: '四川' },
  { value: 'other',     label: '其他地区' },
]
const DIMENSIONS = [
  { key: 'labor',      label: '劳动用工', icon: Users },
  { key: 'contract',   label: '合同管理', icon: FileText },
  { key: 'data',       label: '数据合规', icon: Database },
  { key: 'ip',         label: '知识产权', icon: ShieldCheck },
  { key: 'tax',        label: '税务合规', icon: Calculator },
  { key: 'governance', label: '公司治理', icon: Building },
]

// 单色 token-friendly chart colors
const SCORE_TONE = {
  excellent: 'var(--success)',
  good:      'var(--primary)',
  medium:    'var(--warning)',
  poor:      'var(--destructive)',
}

function getScoreTone(score: number): 'success' | 'normal' | 'warning' | 'error' {
  if (score >= 90) return 'success'
  if (score >= 75) return 'normal'
  if (score >= 60) return 'warning'
  return 'error'
}

function getScoreFill(score: number): string {
  if (score >= 90) return SCORE_TONE.excellent
  if (score >= 75) return SCORE_TONE.good
  if (score >= 60) return SCORE_TONE.medium
  return SCORE_TONE.poor
}

function getScoreLabel(score: number) {
  if (score >= 90) return '优秀'
  if (score >= 75) return '良好'
  if (score >= 60) return '一般'
  return '需改进'
}

function ToneChip({ tone, labelEn, label }: {
  tone: 'normal' | 'success' | 'warning' | 'error'
  labelEn: string
  label: string
}) {
  const toneClass = {
    normal:  'text-muted-foreground',
    success: 'text-success',
    warning: 'text-warning',
    error:   'text-destructive',
  }[tone]
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em]', toneClass)}>
      <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
      <span>{labelEn}</span>
      <span className="text-foreground/30" aria-hidden>·</span>
      <span className="normal-case tracking-normal text-foreground/80">{label}</span>
    </span>
  )
}

function Section({ tracker, title, description, children, icon: Icon }: {
  tracker: string
  title: string
  description?: string
  icon?: typeof Building
  children: React.ReactNode
}) {
  return (
    <section className="border border-border bg-card">
      <header className="px-6 py-4 border-b border-border">
        <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground inline-flex items-center gap-1.5">
          {Icon && <Icon className="w-3 h-3 stroke-[1.5]" />}
          <span>{tracker}</span>
        </div>
        <h3 className="font-serif text-[20px] text-foreground mt-1">{title}</h3>
        {description && <p className="text-[13px] text-muted-foreground mt-1">{description}</p>}
      </header>
      <div className="p-6">{children}</div>
    </section>
  )
}

const inputBase = 'w-full bg-background border border-border px-3 py-2.5 text-[14px] text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:border-primary transition-colors'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
        {label}
      </label>
      {children}
    </div>
  )
}

export default function ComplianceCheck() {
  const [step, setStep] = useState<PageStep>('form')
  const [form, setForm] = useState<CompanyForm>({ name: '', industry: '', scale: '', region: '' })
  const [selectedDimensions, setSelectedDimensions] = useState<Set<string>>(
    new Set(DIMENSIONS.map((d) => d.key))
  )
  const [result, setResult] = useState<CheckResult | null>(null)
  const [expandedRisks, setExpandedRisks] = useState<Set<string>>(new Set())
  const [checkProgress, setCheckProgress] = useState(0)
  const [history, setHistory] = useState<HistoryRecord[]>([])

  const canSubmit =
    form.name.trim() && form.industry && form.scale && form.region && selectedDimensions.size > 0

  const toggleDimension = (key: string) => {
    setSelectedDimensions((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const toggleRisk = (id: string) => {
    setExpandedRisks((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleStartCheck = async () => {
    setStep('checking')
    setCheckProgress(0)
    const progressSteps = [10, 25, 40, 55, 70]
    let progressIdx = 0
    const progressTimer = setInterval(() => {
      if (progressIdx < progressSteps.length) {
        setCheckProgress(progressSteps[progressIdx])
        progressIdx++
      }
    }, 400)
    try {
      const answers = Array.from(selectedDimensions).map((dim) => ({
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
      toast.error('合规检测失败: ' + (err?.message || '请重试'))
      setStep('form')
    }
  }

  useEffect(() => {
    if (result && step === 'result') {
      const record: HistoryRecord = {
        id: `h_${Date.now()}`,
        companyName: form.name,
        totalScore: result.totalScore,
        checkTime: result.checkTime,
        dimensions: result.dimensions.map((d) => d.name),
      }
      setHistory((prev) => [record, ...prev])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, step])

  const handleReset = () => {
    setStep('form')
    setResult(null)
    setExpandedRisks(new Set())
    setCheckProgress(0)
  }

  const groupedRisks = useMemo(() => {
    if (!result) return { high: [], medium: [], low: [] } as Record<string, RiskItem[]>
    const groups: Record<string, RiskItem[]> = { high: [], medium: [], low: [] }
    for (const risk of result.risks) {
      if (groups[risk.level]) groups[risk.level].push(risk)
    }
    return groups
  }, [result])

  const pieData = useMemo(() => {
    if (!result) return []
    return [
      { name: '得分', value: result.totalScore },
      { name: '扣分', value: 100 - result.totalScore },
    ]
  }, [result])

  const barData = useMemo(() => {
    if (!result) return []
    return result.dimensions.map((d) => ({ name: d.name, score: d.score }))
  }, [result])

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-10">
        <EditorialPageHeader
          tracker={['Workspace', '合规管理']}
          title="合规管理"
          description="AI 智能分析企业合规状况，快速识别风险点。"
        />

        <div className="flex flex-col lg:flex-row gap-8">
          {/* ===== 主区域 ===== */}
          <div className="flex-1 min-w-0">
            <AnimatePresence mode="wait">
              {/* Step 1: 表单 */}
              {step === 'form' && (
                <motion.div
                  key="form"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  className="space-y-8"
                >
                  <Section tracker="Company · 企业信息" title="企业信息" icon={Building}>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                      <Field label="公司名称">
                        <input
                          type="text"
                          placeholder="请输入公司名称"
                          value={form.name}
                          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                          className={inputBase}
                        />
                      </Field>
                      <Field label="所属行业">
                        <select
                          value={form.industry}
                          onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))}
                          className={inputBase}
                        >
                          <option value="">请选择行业</option>
                          {INDUSTRIES.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
                        </select>
                      </Field>
                      <Field label="企业规模">
                        <select
                          value={form.scale}
                          onChange={(e) => setForm((f) => ({ ...f, scale: e.target.value }))}
                          className={inputBase}
                        >
                          <option value="">请选择规模</option>
                          {SCALES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                        </select>
                      </Field>
                      <Field label="所在地区">
                        <select
                          value={form.region}
                          onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))}
                          className={inputBase}
                        >
                          <option value="">请选择地区</option>
                          {REGIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                        </select>
                      </Field>
                    </div>
                  </Section>

                  <Section
                    tracker="Dimensions · 自检维度"
                    title="自检维度"
                    icon={ClipboardCheck}
                    description="选择需要检测的合规维度（至少选择一项）。"
                  >
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-border border-t border-l border-border">
                      {DIMENSIONS.map((dim) => {
                        const Icon = dim.icon
                        const selected = selectedDimensions.has(dim.key)
                        return (
                          <button
                            key={dim.key}
                            type="button"
                            onClick={() => toggleDimension(dim.key)}
                            className={cn(
                              'relative bg-card border-r border-b border-border px-4 py-4 flex items-center gap-3 transition-colors text-left',
                              selected ? 'bg-surface-2/40' : 'hover:bg-surface-2/30',
                            )}
                          >
                            <span className={cn(
                              'w-4 h-4 border flex items-center justify-center shrink-0 transition-colors',
                              selected ? 'bg-primary border-primary text-primary-foreground' : 'border-border bg-background',
                            )}>
                              {selected && <Check className="w-3 h-3 stroke-[2]" />}
                            </span>
                            <Icon className={cn('w-4 h-4 stroke-[1.5] shrink-0', selected ? 'text-primary' : 'text-muted-foreground')} />
                            <span className={cn('text-[13px]', selected ? 'text-foreground' : 'text-muted-foreground')}>
                              {dim.label}
                            </span>
                            {selected && <span aria-hidden className="absolute left-0 top-0 bottom-0 w-px bg-primary" />}
                          </button>
                        )
                      })}
                    </div>
                  </Section>

                  <button
                    type="button"
                    onClick={() => void handleStartCheck()}
                    disabled={!canSubmit}
                    className="w-full inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground py-3 text-[14px] font-medium transition-colors"
                  >
                    <ShieldCheck className="w-4 h-4 stroke-[1.5]" />
                    <span>开始合规自检</span>
                  </button>
                </motion.div>
              )}

              {/* Step 2: 检测中 */}
              {step === 'checking' && (
                <motion.div
                  key="checking"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  className="flex flex-col items-center justify-center py-20"
                >
                  <div className="border border-border bg-card w-full max-w-md p-8 text-center">
                    <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-5">
                      Checking · 检测中
                    </div>
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                      className="inline-block mb-5"
                    >
                      <Loader2 className="w-10 h-10 stroke-[1.5] text-primary" />
                    </motion.div>
                    <h3 className="font-serif text-[20px] text-foreground">AI 正在分析合规状况…</h3>
                    <p className="text-[13px] text-muted-foreground mt-2 mb-6">
                      正在检测 {selectedDimensions.size} 个维度，请稍候。
                    </p>
                    <div className="w-full h-px bg-border relative mb-2">
                      <motion.div
                        className="absolute top-0 left-0 h-px bg-primary"
                        initial={{ width: '0%' }}
                        animate={{ width: `${checkProgress}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                    <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground tabular-nums">
                      {checkProgress}%
                    </p>
                    <ol className="mt-6 space-y-1.5 text-left">
                      {DIMENSIONS.filter((d) => selectedDimensions.has(d.key)).map((dim, i) => {
                        const done = checkProgress > ((i + 1) / selectedDimensions.size) * 90
                        return (
                          <li
                            key={dim.key}
                            className={cn(
                              'flex items-center gap-2 text-[13px] transition-colors',
                              done ? 'text-success' : 'text-muted-foreground',
                            )}
                          >
                            {done
                              ? <CheckCircle className="w-3.5 h-3.5 stroke-[1.5]" />
                              : <Loader2 className="w-3.5 h-3.5 stroke-[1.5] animate-spin" />}
                            <span>{dim.label}</span>
                          </li>
                        )
                      })}
                    </ol>
                  </div>
                </motion.div>
              )}

              {/* Step 3: 结果 */}
              {step === 'result' && result && (
                <motion.div
                  key="result"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  className="space-y-8"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-border border-t border-l border-border">
                    {/* 总分环形 */}
                    <div className="bg-card border-r border-b border-border p-6 flex flex-col items-center">
                      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground self-start mb-4">
                        Total Score · 合规总分
                      </div>
                      <div className="w-44 h-44">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={pieData}
                              cx="50%"
                              cy="50%"
                              innerRadius={56}
                              outerRadius={78}
                              startAngle={90}
                              endAngle={-270}
                              dataKey="value"
                              stroke="none"
                            >
                              <Cell fill={getScoreFill(result.totalScore)} />
                              <Cell fill="hsl(var(--muted))" />
                            </Pie>
                            <text
                              x="50%" y="46%"
                              textAnchor="middle" dominantBaseline="middle"
                              className="fill-foreground"
                              style={{ fontFamily: 'var(--font-serif)', fontSize: 30, fontWeight: 500 }}
                            >
                              {result.totalScore}
                            </text>
                            <text
                              x="50%" y="62%"
                              textAnchor="middle" dominantBaseline="middle"
                              className="fill-muted-foreground"
                              style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase' }}
                            >
                              {getScoreLabel(result.totalScore)}
                            </text>
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex items-center gap-4 mt-3">
                        <ToneChip
                          tone={getScoreTone(result.totalScore)}
                          labelEn="Grade"
                          label={getScoreLabel(result.totalScore)}
                        />
                        <span className="text-[12px] text-muted-foreground tabular-nums">
                          {result.risks.filter((r) => r.level === 'high').length} 项高风险
                        </span>
                      </div>
                    </div>

                    {/* 维度条形图 */}
                    <div className="bg-card border-r border-b border-border p-6">
                      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
                        Dimensions · 各维度评分
                      </div>
                      <div className="h-56">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 20, top: 4, bottom: 4 }}>
                            <XAxis
                              type="number" domain={[0, 100]}
                              tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                              axisLine={false} tickLine={false}
                            />
                            <YAxis
                              type="category" dataKey="name" width={70}
                              tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                              axisLine={false} tickLine={false}
                            />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: 'var(--card)',
                                border: '1px solid var(--border)',
                                borderRadius: 0,
                                fontSize: 12,
                              }}
                              formatter={(value: number) => [`${value} 分`, '评分']}
                            />
                            <Bar dataKey="score" maxBarSize={12}>
                              {barData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={getScoreFill(entry.score)} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>

                  {/* 风险项 */}
                  <Section
                    tracker={`Risks · ${result.risks.length} 项`}
                    title="风险项目"
                    icon={AlertTriangle}
                  >
                    {(['high', 'medium', 'low'] as const).map((lvl) => (
                      groupedRisks[lvl].length > 0 && (
                        <RiskGroup
                          key={lvl}
                          level={lvl}
                          risks={groupedRisks[lvl]}
                          expandedRisks={expandedRisks}
                          toggleRisk={toggleRisk}
                        />
                      )
                    ))}
                  </Section>

                  {/* AI 建议 */}
                  <Section tracker="Suggestion · AI 改善建议" title="AI 改善建议" icon={Lightbulb}>
                    <ol className="space-y-3">
                      {result.suggestions.map((sug, i) => (
                        <li key={i} className="flex items-start gap-3 py-3 border-b border-border/60 last:border-b-0">
                          <span className="font-serif text-[14px] text-primary w-8 shrink-0 tabular-nums pt-0.5">
                            {String(i + 1).padStart(2, '0')}
                          </span>
                          <p className="text-[14px] text-foreground/90 leading-relaxed">{sug}</p>
                        </li>
                      ))}
                    </ol>
                  </Section>

                  {/* 操作按钮 */}
                  <div className="flex flex-col sm:flex-row items-center gap-3">
                    <button
                      type="button"
                      onClick={handleReset}
                      className="inline-flex items-center gap-1.5 border border-border bg-card hover:bg-surface-2 px-5 py-2.5 text-[13px] text-foreground transition-colors w-full sm:w-auto justify-center"
                    >
                      <RefreshCw className="w-4 h-4 stroke-[1.5]" />
                      <span>重新检测</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => window.dispatchEvent(new CustomEvent('auth:redirect', { detail: '/chat' }))}
                      className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[13px] font-medium transition-colors w-full sm:flex-1 justify-center"
                    >
                      <MessageSquare className="w-4 h-4 stroke-[1.5]" />
                      <span>咨询 安心智能助手</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ===== 右侧：历史 ===== */}
          <aside className="w-full lg:w-72 xl:w-80 flex-shrink-0">
            <Section tracker="History · 检测历史" title="检测历史" icon={Clock}>
              {history.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mb-3">
                    Empty · 暂无记录
                  </p>
                  <p className="text-[13px] text-muted-foreground">完成一次检测后将出现在这里。</p>
                </div>
              ) : (
                <ol className="space-y-px">
                  {history.map((record, i) => {
                    const tone = getScoreTone(record.totalScore)
                    const toneClass = {
                      normal:  'text-foreground',
                      success: 'text-success',
                      warning: 'text-warning',
                      error:   'text-destructive',
                    }[tone]
                    return (
                      <li key={record.id} className="border-b border-border/60 last:border-b-0">
                        <button
                          type="button"
                          className="w-full text-left py-3 hover:bg-surface-2/40 -mx-3 px-3 transition-colors"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-serif text-[12px] text-muted-foreground tabular-nums">
                              {String(i + 1).padStart(2, '0')}
                            </span>
                            <span className={cn('font-serif text-[18px] tabular-nums', toneClass)}>
                              {record.totalScore}
                            </span>
                          </div>
                          <p className="text-[13px] text-foreground truncate">{record.companyName}</p>
                          <div className="text-[11px] text-muted-foreground mt-1 tabular-nums">
                            {record.checkTime.split(' ')[0]}
                          </div>
                        </button>
                      </li>
                    )
                  })}
                </ol>
              )}
            </Section>
          </aside>
        </div>
      </div>
    </div>
  )
}

// =============== 风险分组 ===============
function RiskGroup({
  level, risks, expandedRisks, toggleRisk,
}: {
  level: 'high' | 'medium' | 'low'
  risks: RiskItem[]
  expandedRisks: Set<string>
  toggleRisk: (id: string) => void
}) {
  const meta = {
    high:   { tone: 'error' as const,   labelEn: 'High',   label: '高风险', icon: XCircle },
    medium: { tone: 'warning' as const, labelEn: 'Medium', label: '中风险', icon: AlertTriangle },
    low:    { tone: 'normal' as const,  labelEn: 'Low',    label: '低风险', icon: Info },
  }[level]
  const Icon = meta.icon
  const toneClass = {
    normal:  'text-muted-foreground',
    success: 'text-success',
    warning: 'text-warning',
    error:   'text-destructive',
  }[meta.tone]
  return (
    <div className="mb-6 last:mb-0">
      <header className="flex items-center gap-2 mb-3">
        <ToneChip tone={meta.tone} labelEn={meta.labelEn} label={meta.label} />
        <span className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground tabular-nums">
          {risks.length} 项
        </span>
      </header>
      <ol className="space-y-px">
        {risks.map((risk, i) => {
          const expanded = expandedRisks.has(risk.id)
          return (
            <li key={risk.id} className="border-b border-border/60 last:border-b-0">
              <button
                type="button"
                onClick={() => toggleRisk(risk.id)}
                className="w-full flex items-center gap-3 py-3 px-2 -mx-2 text-left hover:bg-surface-2/40 transition-colors"
              >
                <span className="font-serif text-[12px] text-muted-foreground w-8 shrink-0 tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <Icon className={cn('w-4 h-4 stroke-[1.5] shrink-0', toneClass)} />
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] text-foreground truncate">{risk.title}</p>
                  <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mt-0.5">
                    {risk.dimension}
                  </p>
                </div>
                <ChevronDown
                  className={cn('w-4 h-4 stroke-[1.5] text-muted-foreground transition-transform', expanded && 'rotate-180')}
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
                    <div className="pl-12 pr-2 pb-4 space-y-3 bg-surface-2/30 -mx-2 px-12">
                      <div>
                        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-1">
                          Description · 风险描述
                        </p>
                        <p className="text-[13px] text-foreground/85">{risk.description}</p>
                      </div>
                      {risk.lawRef && (
                        <div>
                          <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-1">
                            Reference · 法律依据
                          </p>
                          <p className="text-[13px] text-primary">{risk.lawRef}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-1">
                          Suggestion · 改善建议
                        </p>
                        <p className="text-[13px] text-foreground/85">{risk.suggestion}</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
