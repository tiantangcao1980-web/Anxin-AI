/**
 * RiskAlertPanel · 风险预警面板（Editorial Luxury 改造 · Phase 1.16）
 *
 * 旧版用 StatGrid + 多色 badge 色块 + 圆角药丸状筛选。
 * 新版：1px hairline KPI 网格 + tone-only ToneTag + 1px 风险分数线 + 极简筛选下划线。
 *
 * 汇总合同风险 + 舆情预警，提供统一风险视图。
 */
import { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle, Shield, TrendingUp, Clock, CheckCircle2,
  FileText, Radio, ChevronDown, ChevronRight, Eye,
} from 'lucide-react'
import { toast } from 'sonner'

import { contractsApi, sentimentApi, type Contract, type RiskFactor } from '@/lib/api'
import { cn } from '@/components/ui/utils'

interface RiskItem {
  id: string
  source: 'contract' | 'sentiment'
  level: 'high' | 'medium' | 'low'
  title: string
  description: string
  time: string
  handled: boolean
  sourceId: string
  factors?: RiskFactor[]
}

const LEVEL_META: Record<'high' | 'medium' | 'low', { label: string; labelEn: string; tone: 'success' | 'warning' | 'error' }> = {
  high:   { label: '高风险', labelEn: 'High',   tone: 'error' },
  medium: { label: '中风险', labelEn: 'Medium', tone: 'warning' },
  low:    { label: '低风险', labelEn: 'Low',    tone: 'success' },
}

const SOURCE_META = {
  contract:  { label: '合同风险', labelEn: 'Contract',  icon: FileText },
  sentiment: { label: '舆情预警', labelEn: 'Sentiment', icon: Radio },
}

function normalizeRiskLevel(level?: string): 'high' | 'medium' | 'low' {
  if (!level) return 'low'
  const l = level.toLowerCase()
  if (l === 'high' || l === '高') return 'high'
  if (l === 'medium' || l === '中') return 'medium'
  return 'low'
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    if (diff < 3600000)  return `${Math.max(1, Math.floor(diff / 60000))} 分钟前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
    return d.toLocaleDateString('zh-CN')
  } catch {
    return iso
  }
}

export function RiskAlertPanel() {
  const [risks, setRisks] = useState<RiskItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all')

  useEffect(() => {
    let cancelled = false
    const loadData = async () => {
      setLoading(true)
      const items: RiskItem[] = []
      const [contractResult, alertResult] = await Promise.allSettled([
        contractsApi.list({ page_size: 50 }),
        sentimentApi.listAlerts({ page_size: 50 }),
      ])
      if (contractResult.status === 'fulfilled') {
        const contracts = contractResult.value.items ?? []
        for (const c of contracts) {
          if (c.risk_level && c.risk_level !== 'none') {
            items.push({
              id: `contract-${c.id}`,
              source: 'contract',
              level: normalizeRiskLevel(c.risk_level),
              title: c.title,
              description: getContractRiskDescription(c),
              time: c.updated_at,
              handled: false,
              sourceId: c.id,
              factors: getContractRiskFactors(c),
            })
          }
        }
      }
      if (alertResult.status === 'fulfilled') {
        const alerts = alertResult.value.items ?? []
        for (const a of alerts) {
          items.push({
            id: `alert-${a.id}`,
            source: 'sentiment',
            level: normalizeRiskLevel(a.alert_level),
            title: a.title,
            description: a.message,
            time: a.created_at,
            handled: a.is_handled,
            sourceId: a.id,
          })
        }
      }
      items.sort((a, b) => {
        const order = { high: 0, medium: 1, low: 2 }
        return order[a.level] - order[b.level]
      })
      if (!cancelled) {
        setRisks(items)
        setLoading(false)
      }
    }
    void loadData()
    return () => { cancelled = true }
  }, [])

  const handleAlert = useCallback(async (item: RiskItem) => {
    if (item.source !== 'sentiment') return
    try {
      await sentimentApi.handleAlert(item.sourceId, '已确认处理')
      setRisks((prev) => prev.map((r) => r.id === item.id ? { ...r, handled: true } : r))
      toast.success('预警已处理')
    } catch {
      toast.error('处理失败')
    }
  }, [])

  const stats = {
    total: risks.length,
    high: risks.filter((r) => r.level === 'high').length,
    thisWeek: risks.filter((r) => {
      const d = new Date(r.time)
      return Date.now() - d.getTime() < 604800000
    }).length,
    pending: risks.filter((r) => !r.handled).length,
  }
  const filteredRisks = filter === 'all' ? risks : risks.filter((r) => r.level === filter)

  return (
    <div className="h-full overflow-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-10 space-y-8">
      {/* KPI 网格 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border border-t border-l border-border">
        <KpiCell tracker="Total"    label="总预警"   value={stats.total}    icon={AlertTriangle} />
        <KpiCell tracker="High"     label="高风险"   value={stats.high}     icon={Shield}        tone="error" />
        <KpiCell tracker="ThisWeek" label="本周新增" value={stats.thisWeek} icon={TrendingUp} />
        <KpiCell tracker="Pending"  label="待处理"   value={stats.pending}  icon={Clock}         tone="warning" />
      </div>

      {/* 筛选 — Editorial 下划线 */}
      <nav className="flex items-end gap-6 border-b border-border" role="tablist" aria-label="筛选">
        {(['all', 'high', 'medium', 'low'] as const).map((f) => {
          const isActive = filter === f
          const count = f === 'all' ? risks.length : risks.filter((r) => r.level === f).length
          return (
            <button
              key={f}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setFilter(f)}
              className={cn(
                'relative pb-2 text-[12px] font-medium uppercase tracking-[0.16em] transition-colors',
                isActive
                  ? 'text-foreground after:absolute after:left-0 after:right-0 after:bottom-0 after:h-px after:bg-primary'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {f === 'all' ? 'All · 全部' : `${LEVEL_META[f].labelEn} · ${LEVEL_META[f].label}`}
              <span className="ml-1.5 text-muted-foreground tabular-nums">({count})</span>
            </button>
          )
        })}
      </nav>

      {/* 列表 */}
      {loading ? (
        <div className="space-y-px">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 border-b border-border/60 bg-surface-2/40 animate-pulse" />
          ))}
        </div>
      ) : filteredRisks.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
            Risk · 空状态
          </div>
          <CheckCircle2 className="w-10 h-10 stroke-[1] text-success mx-auto mb-4" />
          <p className="font-serif text-[20px] text-foreground mb-1">暂无风险预警</p>
          <p className="text-[13px] text-muted-foreground">系统将自动监测合同风险和舆情变化。</p>
        </div>
      ) : (
        <ol className="space-y-px">
          {filteredRisks.map((item, i) => {
            const levelMeta = LEVEL_META[item.level]
            const sourceMeta = SOURCE_META[item.source]
            const SourceIcon = sourceMeta.icon
            const isExpanded = expandedId === item.id
            const levelToneClass = {
              success: 'text-success',
              warning: 'text-warning',
              error:   'text-destructive',
            }[levelMeta.tone]
            return (
              <li key={item.id} className={cn('border-b border-border/60', item.handled && 'opacity-60')}>
                <button
                  type="button"
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  className="w-full flex items-center gap-4 py-4 px-3 -mx-3 text-left transition-colors hover:bg-surface-2/40"
                >
                  <span className="font-serif text-[12px] text-muted-foreground w-8 shrink-0 tabular-nums">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', levelToneClass.replace('text-', 'bg-'))} aria-hidden />
                  <span className={cn('inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground shrink-0')}>
                    <SourceIcon className="w-3 h-3 stroke-[1.5]" />
                    <span>{sourceMeta.labelEn}</span>
                  </span>
                  <span className="text-[14px] text-foreground truncate flex-1">{item.title}</span>
                  <span className={cn('inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em] shrink-0', levelToneClass)}>
                    <span>{levelMeta.labelEn}</span>
                    <span className="text-foreground/30" aria-hidden>·</span>
                    <span className="normal-case tracking-normal">{levelMeta.label}</span>
                  </span>
                  <span className="text-[11px] text-muted-foreground tabular-nums shrink-0 hidden sm:inline">
                    {formatTime(item.time)}
                  </span>
                  {isExpanded
                    ? <ChevronDown className="w-4 h-4 stroke-[1.5] text-muted-foreground" />
                    : <ChevronRight className="w-4 h-4 stroke-[1.5] text-muted-foreground" />}
                </button>

                {isExpanded && (
                  <div className="px-3 pb-5 -mx-3 bg-surface-2/30">
                    <div className="pt-4 pl-12 space-y-4">
                      <p className="text-[14px] text-foreground/80 leading-relaxed">{item.description}</p>
                      {item.factors && item.factors.length > 0 && (
                        <div className="space-y-3">
                          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                            Risk Factors · 风险因子
                          </div>
                          {item.factors.slice(0, 5).map((factor) => (
                            <div key={factor.key} className="space-y-1.5">
                              <div className="flex items-center justify-between text-[12px]">
                                <span className="text-foreground truncate">{factor.name}</span>
                                <span className="text-muted-foreground shrink-0 tabular-nums">
                                  贡献 {Number(factor.contribution ?? 0).toFixed(1)}
                                </span>
                              </div>
                              <div className="h-px bg-border relative">
                                <div
                                  className="absolute top-0 left-0 h-px bg-primary"
                                  style={{ width: `${Math.min(100, Math.max(0, factor.score))}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center gap-3 pt-2">
                        {item.source === 'sentiment' && !item.handled && (
                          <button
                            type="button"
                            onClick={() => handleAlert(item)}
                            className="bg-primary hover:bg-primary-700 text-primary-foreground px-4 py-1.5 text-[12px] font-medium transition-colors"
                          >
                            标记已处理
                          </button>
                        )}
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 border border-border bg-card hover:bg-surface-2 px-3 py-1.5 text-[12px] text-foreground transition-colors"
                        >
                          <Eye className="w-3 h-3 stroke-[1.5]" />
                          <span>查看详情</span>
                        </button>
                        {item.handled && (
                          <span className="inline-flex items-center gap-1 text-[11px] uppercase tracking-[0.12em] text-success">
                            <CheckCircle2 className="w-3 h-3 stroke-[1.5]" />
                            已处理
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}

function KpiCell({
  tracker, label, value, icon: Icon, tone = 'normal',
}: {
  tracker: string
  label: string
  value: number
  icon: typeof Clock
  tone?: 'normal' | 'success' | 'warning' | 'error'
}) {
  const toneClass = {
    normal:  'text-foreground',
    success: 'text-success',
    warning: 'text-warning',
    error:   'text-destructive',
  }[tone]
  return (
    <div className="bg-card border-r border-b border-border px-5 py-4">
      <div className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        <Icon className="w-3 h-3 stroke-[1.5]" />
        <span>{tracker}</span>
        <span className="text-foreground/30" aria-hidden>·</span>
        <span className="normal-case tracking-normal text-foreground/70">{label}</span>
      </div>
      <div className={cn('font-serif text-[32px] leading-[1.1] mt-2 tabular-nums', toneClass)}>{value}</div>
    </div>
  )
}

function getContractRiskDescription(contract: Contract): string {
  const parts: string[] = []
  if (contract.risk_score !== undefined) parts.push(`风险评分: ${contract.risk_score}`)
  if (contract.risk_explain) parts.push(contract.risk_explain)
  if (contract.expiry_date) {
    const expiry = new Date(contract.expiry_date)
    const now = new Date()
    const daysLeft = Math.ceil((expiry.getTime() - now.getTime()) / 86400000)
    if (daysLeft < 0) parts.push('合同已过期')
    else if (daysLeft < 30) parts.push(`将于 ${daysLeft} 天后到期`)
  }
  if (contract.contract_type) parts.push(`类型: ${contract.contract_type}`)
  return parts.length > 0 ? parts.join(' · ') : `合同 ${contract.title} 存在风险`
}

function getContractRiskFactors(contract: Contract): RiskFactor[] {
  const flexible = contract as Contract & { factors?: RiskFactor[] }
  const factors = flexible.risk_factors ?? flexible.factors ?? []
  return factors.filter((factor) => (
    typeof factor?.key === 'string'
    && typeof factor?.name === 'string'
    && typeof factor?.score === 'number'
  ))
}
