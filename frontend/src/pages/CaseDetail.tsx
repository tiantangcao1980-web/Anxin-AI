/**
 * CaseDetail · 案件详情（Editorial Luxury 改造 · Phase 2.2）
 *
 * 旧版：cardStyle.base !p-0 overflow-hidden 头部色块 + bg-primary/[0.02] AI 卡 + 圆点 timeline。
 * 新版：DetailPageTemplate + PanelSection（hairline）+ tone-only chip + 序号 timeline。
 */
import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { toast } from 'sonner'
import {
  ArrowLeft, Sparkles, Loader2, Clock, Calendar, ChevronDown, ChevronUp,
  FileText, MessageSquare, User,
} from 'lucide-react'

import { DetailPageTemplate, PanelSection } from '@/components/ui/PageTemplates'
import { casesApi, type Case } from '@/lib/api'
import { cn } from '@/components/ui/utils'

type StatusKey = 'pending' | 'in_progress' | 'under_review' | 'completed' | 'closed'
type PriorityKey = 'low' | 'medium' | 'high' | 'urgent'

const STATUS_META: Record<StatusKey, { label: string; labelEn: string; tone: 'normal' | 'success' | 'warning' | 'error' }> = {
  pending:      { label: '待处理', labelEn: 'Pending',  tone: 'warning' },
  in_progress:  { label: '进行中', labelEn: 'Active',   tone: 'normal' },
  under_review: { label: '审核中', labelEn: 'Review',   tone: 'normal' },
  completed:    { label: '已完成', labelEn: 'Done',     tone: 'success' },
  closed:       { label: '已关闭', labelEn: 'Closed',   tone: 'normal' },
}

const PRIORITY_META: Record<PriorityKey, { label: string; labelEn: string; tone: 'normal' | 'success' | 'warning' | 'error' }> = {
  low:    { label: '低',    labelEn: 'Low',     tone: 'success' },
  medium: { label: '中',    labelEn: 'Medium',  tone: 'warning' },
  high:   { label: '高',    labelEn: 'High',    tone: 'warning' },
  urgent: { label: '紧急',  labelEn: 'Urgent',  tone: 'error' },
}

function ToneTag({ tone, labelEn, label }: { tone: 'normal' | 'success' | 'warning' | 'error'; labelEn: string; label: string }) {
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

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const [case_, setCase] = useState<Case | null>(null)
  const [loading, setLoading] = useState(true)
  const [timeline, setTimeline] = useState<any[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<any>(null)
  const [showRawAnalysis, setShowRawAnalysis] = useState(false)

  const loadCase = useCallback(async () => {
    if (!id) return
    try {
      const data = await casesApi.get(id)
      setCase(data)
    } catch (error: any) {
      toast.error(error?.message || '加载案件失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  const loadTimeline = useCallback(async () => {
    if (!id) return
    try {
      const events = await casesApi.getTimeline(id)
      setTimeline(events)
    } catch (error) {
      console.error('加载时间线失败', error)
    }
  }, [id])

  useEffect(() => {
    if (id) {
      void loadCase()
      void loadTimeline()
    }
  }, [id, loadCase, loadTimeline])

  const handleAnalyze = async () => {
    if (!id) return
    setAnalyzing(true)
    try {
      const result = await casesApi.analyze(id)
      setAnalysis(result)
      toast.success('分析完成')
      void loadTimeline()
      void loadCase()
    } catch (error: any) {
      toast.error(error?.message || '分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 stroke-[1.5] animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!case_) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-8">
        <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
          Case · 不存在
        </div>
        <p className="font-serif text-[22px] text-foreground mb-4">案件不存在</p>
        <Link to="/cases" className="text-[13px] uppercase tracking-[0.12em] text-primary hover:text-primary-700 transition-colors">
          ← 返回案件列表
        </Link>
      </div>
    )
  }

  const status = STATUS_META[case_.status as StatusKey] || STATUS_META.pending
  const priority = PRIORITY_META[case_.priority as PriorityKey] || PRIORITY_META.medium

  const report = analysis?.final_result?.report || analysis?.report || null
  const summary = analysis?.final_result?.summary || analysis?.summary || null
  const riskScore = case_.risk_score ?? null
  const riskTone = riskScore == null
    ? 'normal'
    : riskScore > 0.7 ? 'error' : riskScore > 0.4 ? 'warning' : 'success'

  return (
    <DetailPageTemplate
      tracker={['Workspace', '案件管理', case_.case_number || '案件']}
      title={case_.title}
      description={case_.case_number ? `案件编号：${case_.case_number}` : undefined}
      actions={
        <div className="flex items-center gap-3">
          <Link
            to="/cases"
            className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4 stroke-[1.5]" />
            <span>返回</span>
          </Link>
          <button
            type="button"
            onClick={() => void handleAnalyze()}
            disabled={analyzing}
            className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 disabled:opacity-50 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
          >
            {analyzing
              ? <Loader2 className="w-4 h-4 stroke-[1.5] animate-spin" />
              : <Sparkles className="w-4 h-4 stroke-[1.5]" />}
            <span>{analyzing ? '智能分析中…' : 'AI 深度分析'}</span>
          </button>
        </div>
      }
      aside={
        <div className="space-y-8">
          <PanelSection tracker="Profile · 画像" title="案件画像">
            <div className="space-y-4">
              <MetaRow icon={Calendar} label="创建时间" value={`${new Date(case_.created_at).toLocaleDateString()} ${new Date(case_.created_at).toLocaleTimeString()}`} />
              <MetaRow icon={Clock} label="最后更新" value={`${new Date(case_.updated_at).toLocaleDateString()} ${new Date(case_.updated_at).toLocaleTimeString()}`} />
              {riskScore != null && (
                <div className="pt-3 border-t border-border/60">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                      AI Risk · 风险评分
                    </span>
                    <span className={cn(
                      'text-[18px] font-serif tabular-nums',
                      riskTone === 'error'   && 'text-destructive',
                      riskTone === 'warning' && 'text-warning',
                      riskTone === 'success' && 'text-success',
                    )}>
                      {(riskScore * 100).toFixed(0)}/100
                    </span>
                  </div>
                  <div className="h-px bg-border relative">
                    <div
                      className={cn(
                        'absolute top-0 left-0 h-px transition-[width] duration-700',
                        riskTone === 'error'   && 'bg-destructive',
                        riskTone === 'warning' && 'bg-warning',
                        riskTone === 'success' && 'bg-success',
                      )}
                      style={{ width: `${riskScore * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </PanelSection>

          <PanelSection tracker="Tools · 工具" title="快捷法律工具">
            <div className="space-y-px">
              <SidebarBtn icon={FileText}      label="关联案件证据" />
              <SidebarBtn icon={MessageSquare} label="发起法律研讨" />
              <SidebarBtn icon={User}          label="指派承办律师" />
            </div>
          </PanelSection>
        </div>
      }
    >
      {/* 状态 chips */}
      <div className="flex items-center gap-4 mb-8 flex-wrap">
        <ToneTag tone={status.tone}   labelEn={status.labelEn}   label={status.label} />
        <ToneTag tone={priority.tone} labelEn={priority.labelEn} label={`${priority.label} 优先`} />
      </div>

      {/* 基本描述 */}
      <PanelSection tracker="Brief · 案情" title="案件基本描述">
        <p className="text-[15px] leading-[1.85] text-foreground/90 whitespace-pre-wrap">
          {case_.description || '暂无详细描述'}
        </p>
      </PanelSection>

      {/* AI 分析 */}
      {(analysis || analyzing) && (
        <PanelSection
          tracker="Insight · AI 分析"
          title="AI 智能分析报告"
          actions={analyzing && (
            <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.12em] text-primary">
              <Loader2 className="w-3 h-3 stroke-[1.5] animate-spin" />
              <span>正在构建决策树…</span>
            </span>
          )}
        >
          {analyzing ? (
            <div className="space-y-3">
              <div className="h-3 bg-surface-2 w-3/4 animate-pulse" />
              <div className="h-3 bg-surface-2 w-full animate-pulse" />
              <div className="h-3 bg-surface-2 w-5/6 animate-pulse" />
            </div>
          ) : (
            <div className="space-y-6">
              {summary && (
                <aside className="border-l-2 border-primary/60 pl-4 py-2">
                  <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-primary mb-1">
                    Summary · 摘要
                  </div>
                  <p className="text-[14px] italic text-foreground/90 leading-relaxed">{summary}</p>
                </aside>
              )}
              <div className="prose prose-sm max-w-none text-foreground prose-headings:font-serif prose-headings:font-medium">
                {report ? (
                  <ReactMarkdown>{report}</ReactMarkdown>
                ) : (
                  <p className="text-[13px] text-muted-foreground py-4 text-center border border-dashed border-border">
                    分析完成，但未生成结构化报告。请查看原始数据。
                  </p>
                )}
              </div>
              <div className="pt-4 border-t border-border/60">
                <button
                  type="button"
                  onClick={() => setShowRawAnalysis(!showRawAnalysis)}
                  className="inline-flex items-center gap-1 text-[11px] uppercase tracking-[0.12em] text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showRawAnalysis
                    ? <ChevronUp className="w-3 h-3 stroke-[1.5]" />
                    : <ChevronDown className="w-3 h-3 stroke-[1.5]" />}
                  {showRawAnalysis ? '隐藏原始分析数据' : '查看原始分析数据'}
                </button>
                {showRawAnalysis && (
                  <pre className="mt-3 p-3 bg-surface-2 border border-border text-[10px] font-mono overflow-auto max-h-60">
                    {JSON.stringify(analysis, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}
        </PanelSection>
      )}

      {/* 时间线 */}
      <PanelSection tracker="Timeline · 动态" title="案件动态时间线">
        {timeline.length === 0 ? (
          <div className="text-center py-10">
            <Clock className="w-10 h-10 stroke-[1] text-foreground/20 mx-auto mb-3" />
            <p className="text-[13px] text-muted-foreground">暂无事件记录</p>
          </div>
        ) : (
          <ol className="space-y-px">
            {timeline.map((event, index) => (
              <li key={event.id || index} className="flex items-start gap-6 py-4 border-b border-border/60 last:border-b-0">
                <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 tabular-nums pt-1">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-3 mb-1">
                    <p className="font-serif text-[16px] text-foreground">{event.title}</p>
                    <span className="text-[11px] tabular-nums text-muted-foreground shrink-0">
                      {new Date(event.event_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-[13px] text-muted-foreground leading-relaxed">{event.description}</p>
                  <p className="text-[11px] text-muted-foreground/60 mt-2 inline-flex items-center gap-1 tabular-nums">
                    <Calendar className="w-3 h-3 stroke-[1.5]" />
                    {new Date(event.event_time).toLocaleDateString()}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </PanelSection>
    </DetailPageTemplate>
  )
}

function MetaRow({ icon: Icon, label, value }: { icon: typeof Calendar; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="w-4 h-4 stroke-[1.5] text-muted-foreground shrink-0" />
      <div className="min-w-0">
        <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
        <div className="text-[13px] text-foreground mt-0.5 truncate">{value}</div>
      </div>
    </div>
  )
}

function SidebarBtn({ icon: Icon, label }: { icon: typeof FileText; label: string }) {
  return (
    <button
      type="button"
      className="w-full flex items-center gap-3 py-2.5 px-2 -mx-2 text-[13px] text-foreground hover:text-primary hover:bg-surface-2/40 border-b border-border/60 last:border-b-0 transition-colors text-left"
    >
      <Icon className="w-3.5 h-3.5 stroke-[1.5] text-muted-foreground" />
      <span>{label}</span>
    </button>
  )
}
