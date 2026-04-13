/**
 * RiskAlertPanel — 风险预警面板
 * 汇总合同风险 + 舆情预警的统一风险视图
 */

import { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle, Shield, TrendingUp, Clock, CheckCircle2,
  FileText, Radio, ChevronDown, ChevronRight, Eye,
} from 'lucide-react'
import { contractsApi, sentimentApi, type Contract, type SentimentAlert } from '@/lib/api'
import { toast } from 'sonner'

// 统一风险项
interface RiskItem {
  id: string
  source: 'contract' | 'sentiment'
  level: 'high' | 'medium' | 'low'
  title: string
  description: string
  time: string
  handled: boolean
  sourceId: string
}

// 风险级别配置
const RISK_LEVEL_CONFIG = {
  high: { label: '高风险', color: 'bg-destructive/10 text-destructive border-destructive/20', dot: 'bg-destructive' },
  medium: { label: '中风险', color: 'bg-warning/10 text-warning border-warning/20', dot: 'bg-warning' },
  low: { label: '低风险', color: 'bg-success/10 text-success border-success/20', dot: 'bg-success' },
}

// 来源配置
const SOURCE_CONFIG = {
  contract: { label: '合同风险', icon: FileText, color: 'text-blue-600 bg-blue-50' },
  sentiment: { label: '舆情预警', icon: Radio, color: 'text-orange-600 bg-orange-50' },
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
    if (diff < 3600000) return `${Math.max(1, Math.floor(diff / 60000))} 分钟前`
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

  // 加载数据
  useEffect(() => {
    let cancelled = false

    const loadData = async () => {
      setLoading(true)
      const items: RiskItem[] = []

      // 并行加载合同和预警
      const [contractResult, alertResult] = await Promise.allSettled([
        contractsApi.list({ page_size: 50 }),
        sentimentApi.listAlerts({ page_size: 50 }),
      ])

      // 合同风险
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
            })
          }
        }
      }

      // 舆情预警
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

      // 按级别排序：high > medium > low
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

  // 处理预警
  const handleAlert = useCallback(async (item: RiskItem) => {
    if (item.source !== 'sentiment') return
    try {
      await sentimentApi.handleAlert(item.sourceId, '已确认处理')
      setRisks(prev => prev.map(r => r.id === item.id ? { ...r, handled: true } : r))
      toast.success('预警已处理')
    } catch {
      toast.error('处理失败')
    }
  }, [])

  // 统计
  const stats = {
    total: risks.length,
    high: risks.filter(r => r.level === 'high').length,
    thisWeek: risks.filter(r => {
      const d = new Date(r.time)
      const now = new Date()
      return now.getTime() - d.getTime() < 604800000
    }).length,
    pending: risks.filter(r => !r.handled).length,
  }

  // 过滤
  const filteredRisks = filter === 'all' ? risks : risks.filter(r => r.level === filter)

  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={AlertTriangle}
          label="总预警"
          value={stats.total}
          color="text-foreground"
          loading={loading}
        />
        <StatCard
          icon={Shield}
          label="高风险"
          value={stats.high}
          color="text-destructive"
          loading={loading}
        />
        <StatCard
          icon={TrendingUp}
          label="本周新增"
          value={stats.thisWeek}
          color="text-primary"
          loading={loading}
        />
        <StatCard
          icon={Clock}
          label="待处理"
          value={stats.pending}
          color="text-warning"
          loading={loading}
        />
      </div>

      {/* 筛选 */}
      <div className="flex items-center gap-2">
        {(['all', 'high', 'medium', 'low'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === f
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:text-foreground'
            }`}
          >
            {f === 'all' ? '全部' : RISK_LEVEL_CONFIG[f].label}
            {f !== 'all' && ` (${risks.filter(r => r.level === f).length})`}
          </button>
        ))}
      </div>

      {/* 风险列表 */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : filteredRisks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <CheckCircle2 className="h-12 w-12 mb-3 text-success" />
          <p className="text-sm font-medium">暂无风险预警</p>
          <p className="text-xs mt-1">系统将自动监测合同风险和舆情变化</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredRisks.map(item => {
            const levelCfg = RISK_LEVEL_CONFIG[item.level]
            const sourceCfg = SOURCE_CONFIG[item.source]
            const isExpanded = expandedId === item.id

            return (
              <div
                key={item.id}
                className={`rounded-xl border bg-card transition-all ${item.handled ? 'opacity-60' : ''}`}
              >
                <button
                  type="button"
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left"
                >
                  {/* 级别指示 */}
                  <div className={`h-2.5 w-2.5 rounded-full shrink-0 ${levelCfg.dot}`} />

                  {/* 来源标签 */}
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium shrink-0 ${sourceCfg.color}`}>
                    <sourceCfg.icon className="h-3 w-3" />
                    {sourceCfg.label}
                  </span>

                  {/* 标题 */}
                  <span className="text-sm font-medium truncate flex-1">{item.title}</span>

                  {/* 级别 */}
                  <span className={`px-2 py-0.5 rounded-md text-[11px] font-medium border shrink-0 ${levelCfg.color}`}>
                    {levelCfg.label}
                  </span>

                  {/* 时间 */}
                  <span className="text-xs text-muted-foreground shrink-0">{formatTime(item.time)}</span>

                  {/* 展开箭头 */}
                  {isExpanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                </button>

                {/* 展开详情 */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-border/50">
                    <p className="text-sm text-muted-foreground mt-3 leading-relaxed">{item.description}</p>
                    <div className="flex items-center gap-2 mt-3">
                      {item.source === 'sentiment' && !item.handled && (
                        <button
                          onClick={() => handleAlert(item)}
                          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                        >
                          标记已处理
                        </button>
                      )}
                      <button className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground bg-muted hover:text-foreground transition-colors flex items-center gap-1">
                        <Eye className="h-3 w-3" />
                        查看详情
                      </button>
                      {item.handled && (
                        <span className="text-xs text-success flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" />
                          已处理
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// 统计卡片
function StatCard({ icon: Icon, label, value, color, loading }: {
  icon: typeof AlertTriangle
  label: string
  value: number
  color: string
  loading: boolean
}) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${color}`} />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      {loading ? (
        <div className="h-8 w-16 rounded bg-muted animate-pulse" />
      ) : (
        <div className={`text-2xl font-semibold ${color}`}>{value}</div>
      )}
    </div>
  )
}

// 合同风险描述生成
function getContractRiskDescription(contract: Contract): string {
  const parts: string[] = []
  if (contract.risk_score !== undefined) {
    parts.push(`风险评分: ${contract.risk_score}`)
  }
  if (contract.expiry_date) {
    const expiry = new Date(contract.expiry_date)
    const now = new Date()
    const daysLeft = Math.ceil((expiry.getTime() - now.getTime()) / 86400000)
    if (daysLeft < 0) {
      parts.push('合同已过期')
    } else if (daysLeft < 30) {
      parts.push(`将于 ${daysLeft} 天后到期`)
    }
  }
  if (contract.contract_type) {
    parts.push(`类型: ${contract.contract_type}`)
  }
  return parts.length > 0 ? parts.join(' · ') : `合同 ${contract.title} 存在风险`
}
