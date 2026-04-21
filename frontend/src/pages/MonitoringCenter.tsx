/**
 * 舆情中心 — 企业舆情监测大盘
 * v3.0 新模块：接入 sentimentApi 全套 CRUD
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Activity, Building2, Bell, TrendingUp, Plus, Search,
  ChevronRight, AlertCircle, Clock, Eye, X, Power,
  Trash2, ChevronLeft, Radio,
} from 'lucide-react'
import {
  sentimentApi,
  type SentimentMonitor,
  type SentimentStatistics,
  type SentimentRecord,
  type SentimentAlert,
} from '@/lib/api'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'
import { StatCard, StatGrid, StatCardSkeleton } from '@/components/ui-unified'
import { buttonStyle, inputStyle, iconSize } from '@/lib/design-tokens'

const riskColors = { low: 'text-success bg-success/10', medium: 'text-warning bg-warning/10', high: 'text-destructive bg-destructive/10' }
const riskLabels = { low: '低风险', medium: '中风险', high: '高风险' }

function getRiskLevel(monitor: SentimentMonitor): 'low' | 'medium' | 'high' {
  if (monitor.alert_count > 3 || monitor.negative_count > 10) return 'high'
  if (monitor.alert_count > 0 || monitor.negative_count > 3) return 'medium'
  return 'low'
}

function formatTime(iso?: string): string {
  if (!iso) return '暂无'
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

// ========== 添加监测对话框 ==========
function AddMonitorDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (m: SentimentMonitor) => void }) {
  const [name, setName] = useState('')
  const [keywords, setKeywords] = useState('')
  const [creating, setCreating] = useState(false)

  const handleCreate = async () => {
    const trimName = name.trim()
    const kws = keywords.split(/[,，\n]/).map(s => s.trim()).filter(Boolean)
    if (!trimName) { toast.error('请输入监测对象名称'); return }
    if (kws.length === 0) { toast.error('请输入至少一个关键词'); return }

    setCreating(true)
    try {
      const monitor = await sentimentApi.createMonitor({ name: trimName, keywords: kws })
      toast.success('监测对象添加成功')
      onCreated(monitor)
    } catch {
      toast.error('添加失败，请稍后重试')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md bg-background rounded-2xl border shadow-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">添加监测对象</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-muted"><X className="h-4 w-4" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-foreground">企业/对象名称</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="如：腾讯科技"
              className="mt-1 w-full px-3 py-2.5 bg-muted/50 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground">监测关键词</label>
            <textarea
              value={keywords}
              onChange={e => setKeywords(e.target.value)}
              placeholder="多个关键词用逗号分隔，如：腾讯, 微信, 小程序"
              rows={3}
              className="mt-1 w-full px-3 py-2.5 bg-muted/50 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-2xl border hover:bg-muted transition-colors">取消</button>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 text-sm rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {creating ? '创建中...' : '确认添加'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ========== 监测详情面板 ==========
function MonitorDetailPanel({ monitor, onClose }: { monitor: SentimentMonitor; onClose: () => void }) {
  const [records, setRecords] = useState<SentimentRecord[]>([])
  const [alerts, setAlerts] = useState<SentimentAlert[]>([])
  const [loadingRecords, setLoadingRecords] = useState(true)
  const [loadingAlerts, setLoadingAlerts] = useState(true)
  const [tab, setTab] = useState<'records' | 'alerts'>('records')

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      // 用 monitor 的关键词加载记录和预警
      const keyword = monitor.keywords[0] || monitor.name

      try {
        const r = await sentimentApi.listRecords({ keyword, page_size: 20 })
        if (!cancelled) setRecords(r.items ?? [])
      } catch {
        if (!cancelled) setRecords([])
      } finally {
        if (!cancelled) setLoadingRecords(false)
      }

      try {
        const a = await sentimentApi.listAlerts({ page_size: 20 })
        if (!cancelled) setAlerts(a.items ?? [])
      } catch {
        if (!cancelled) setAlerts([])
      } finally {
        if (!cancelled) setLoadingAlerts(false)
      }
    }

    void load()
    return () => { cancelled = true }
  }, [monitor])

  const handleMarkRead = async (alertId: string) => {
    try {
      await sentimentApi.markAlertRead(alertId)
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_read: true } : a))
    } catch {
      toast.error('操作失败')
    }
  }

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-lg bg-background border-l shadow-xl flex flex-col">
      <div className="flex items-center gap-3 px-6 py-4 border-b">
        <button onClick={onClose} className="p-1 rounded-lg hover:bg-muted">
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div>
          <h2 className="text-lg font-semibold">{monitor.name}</h2>
          <p className="text-xs text-muted-foreground">关键词: {monitor.keywords.join(', ')}</p>
        </div>
      </div>

      <div className="flex border-b">
        <button
          onClick={() => setTab('records')}
          className={`flex-1 py-2.5 text-sm font-medium text-center transition-colors ${
            tab === 'records' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          舆情记录 ({records.length})
        </button>
        <button
          onClick={() => setTab('alerts')}
          className={`flex-1 py-2.5 text-sm font-medium text-center transition-colors ${
            tab === 'alerts' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          预警 ({alerts.length})
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {tab === 'records' ? (
          loadingRecords ? (
            <div className="space-y-3">{[1, 2, 3].map(i => <div key={i} className="h-16 rounded-lg bg-muted animate-pulse" />)}</div>
          ) : records.length === 0 ? (
            <div className="text-center py-12 text-sm text-muted-foreground">暂无舆情记录</div>
          ) : (
            <div className="space-y-3">
              {records.map(r => (
                <div key={r.id} className="rounded-lg border p-3 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${
                      r.sentiment_type === 'negative' ? 'bg-destructive/10 text-destructive'
                        : r.sentiment_type === 'positive' ? 'bg-success/10 text-success'
                          : 'bg-muted text-muted-foreground'
                    }`}>
                      {r.sentiment_type === 'negative' ? '负面' : r.sentiment_type === 'positive' ? '正面' : '中性'}
                    </span>
                    {r.source && <span className="text-[11px] text-muted-foreground">{r.source}</span>}
                    <span className="text-[11px] text-muted-foreground ml-auto">{formatTime(r.created_at)}</span>
                  </div>
                  <p className="text-sm font-medium">{r.title || r.keyword}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{r.content}</p>
                </div>
              ))}
            </div>
          )
        ) : (
          loadingAlerts ? (
            <div className="space-y-3">{[1, 2, 3].map(i => <div key={i} className="h-16 rounded-lg bg-muted animate-pulse" />)}</div>
          ) : alerts.length === 0 ? (
            <div className="text-center py-12 text-sm text-muted-foreground">暂无预警</div>
          ) : (
            <div className="space-y-3">
              {alerts.map(a => (
                <div key={a.id} className={`rounded-lg border p-3 space-y-1.5 ${a.is_read ? 'opacity-60' : ''}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${
                      a.alert_level === 'high' ? 'bg-destructive/10 text-destructive'
                        : a.alert_level === 'medium' ? 'bg-warning/10 text-warning'
                          : 'bg-muted text-muted-foreground'
                    }`}>
                      {a.alert_level === 'high' ? '高危' : a.alert_level === 'medium' ? '中危' : '低危'}
                    </span>
                    <span className="text-xs text-muted-foreground ml-auto">{formatTime(a.created_at)}</span>
                  </div>
                  <p className="text-sm font-medium">{a.title}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{a.message}</p>
                  {!a.is_read && (
                    <button
                      onClick={() => handleMarkRead(a.id)}
                      className="text-xs text-primary hover:underline"
                    >
                      标记已读
                    </button>
                  )}
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  )
}

// ========== 主组件 ==========
export default function MonitoringCenter() {
  const [searchQuery, setSearchQuery] = useState('')
  const [monitors, setMonitors] = useState<SentimentMonitor[]>([])
  const [statistics, setStatistics] = useState<SentimentStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [selectedMonitor, setSelectedMonitor] = useState<SentimentMonitor | null>(null)

  // 加载数据
  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setLoading(true)
      const [monitorResult, statsResult] = await Promise.allSettled([
        sentimentApi.listMonitors({ page_size: 50 }),
        sentimentApi.getStatistics(7),
      ])

      if (!cancelled) {
        setMonitors(monitorResult.status === 'fulfilled' ? monitorResult.value.items ?? [] : [])
        setStatistics(statsResult.status === 'fulfilled' ? statsResult.value : null)
        setLoading(false)
      }
    }

    void load()
    return () => { cancelled = true }
  }, [])

  // 删除监测对象
  const handleDelete = useCallback(async (id: string) => {
    if (!window.confirm('确定删除该监测对象？')) return
    try {
      await sentimentApi.deleteMonitor(id)
      setMonitors(prev => prev.filter(m => m.id !== id))
      toast.success('已删除')
    } catch {
      toast.error('删除失败')
    }
  }, [])

  // 启停监测
  const handleToggle = useCallback(async (id: string, isActive: boolean) => {
    try {
      await sentimentApi.toggleMonitor(id, !isActive)
      setMonitors(prev => prev.map(m => m.id === id ? { ...m, is_active: !isActive } : m))
      toast.success(isActive ? '已暂停监测' : '已恢复监测')
    } catch {
      toast.error('操作失败')
    }
  }, [])

  // 统计计算（使用 UnifiedStatCard tone 体系）
  const stats: {
    label: string
    value: number | string
    icon: typeof Building2
    tone: 'primary' | 'success' | 'destructive' | 'warning'
    hint: string
  }[] = [
    {
      label: '监测对象',
      value: monitors.length,
      icon: Building2,
      tone: 'primary',
      hint: '已订阅',
    },
    {
      label: '今日舆情',
      value: statistics?.total_records ?? monitors.reduce((s, m) => s + m.total_records, 0),
      icon: Activity,
      tone: 'success',
      hint: '24 小时内',
    },
    {
      label: '风险预警',
      value: statistics?.alerts?.total ?? monitors.reduce((s, m) => s + m.alert_count, 0),
      icon: Bell,
      tone: 'destructive',
      hint: '待处理告警',
    },
    {
      label: '负面舆情',
      value: statistics?.sentiment_distribution?.negative ?? monitors.reduce((s, m) => s + m.negative_count, 0),
      icon: TrendingUp,
      tone: 'warning',
      hint: '需关注',
    },
  ]

  // 搜索过滤
  const filteredMonitors = searchQuery
    ? monitors.filter(m => m.name.toLowerCase().includes(searchQuery.toLowerCase()) || m.keywords.some(k => k.includes(searchQuery)))
    : monitors

  return (
    <PageContainer
      title="舆情中心"
      description="实时监测企业舆情动态，智能预警风险事件"
      actions={
        <button
          onClick={() => setShowAddDialog(true)}
          className={`${buttonStyle.primary} inline-flex items-center gap-2`}
        >
          <Plus className={iconSize.sm} />
          添加监测对象
        </button>
      }
      toolbar={
        <div className="relative flex-1">
          <Search className={`${iconSize.sm} absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground`} />
          <input
            type="text"
            placeholder="搜索监测对象或关键词..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className={`${inputStyle.search} pl-10`}
          />
        </div>
      }
    >
      {/* 统计卡片 — 接入 StatGrid 与全站一致 */}
      {loading ? (
        <StatCardSkeleton count={4} />
      ) : (
        <StatGrid cols={4}>
          {stats.map((stat, index) => (
            <StatCard
              key={stat.label}
              index={index}
              icon={stat.icon}
              tone={stat.tone}
              label={stat.label}
              value={stat.value}
              hint={stat.hint}
            />
          ))}
        </StatGrid>
      )}

      {/* 监测对象列表 */}
      <div className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">
          监测对象 ({filteredMonitors.length})
        </h2>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />)}
          </div>
        ) : filteredMonitors.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <Radio className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
            <p className="text-sm font-medium">{searchQuery ? '未找到匹配的监测对象' : '暂无监测对象'}</p>
            <p className="text-xs mt-1">点击"添加监测对象"开始监测企业舆情</p>
          </div>
        ) : (
          filteredMonitors.map(monitor => {
            const risk = getRiskLevel(monitor)
            return (
              <div
                key={monitor.id}
                className={`bg-card border rounded-xl p-4 hover:shadow-sm hover:border-primary/20 transition-[border-color,box-shadow] group ${
                  !monitor.is_active ? 'opacity-60' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setSelectedMonitor(monitor)}
                    className="flex items-center gap-4 text-left flex-1 min-w-0"
                  >
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Building2 className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-medium group-hover:text-primary transition-colors truncate">{monitor.name}</h3>
                      <p className="text-xs text-muted-foreground truncate">
                        {monitor.keywords.join(', ')}
                        {!monitor.is_active && ' · 已暂停'}
                      </p>
                    </div>
                  </button>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${riskColors[risk]}`}>
                      {riskLabels[risk]}
                    </span>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Eye className="h-3.5 w-3.5" />
                        {monitor.total_records}
                      </span>
                      {monitor.alert_count > 0 && (
                        <span className="flex items-center gap-1 text-destructive">
                          <AlertCircle className="h-3.5 w-3.5" />
                          {monitor.alert_count}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" />
                        {formatTime(monitor.last_scan_at)}
                      </span>
                    </div>
                    {/* 操作按钮 */}
                    <div className="hidden group-hover:flex items-center gap-1">
                      <button
                        onClick={e => { e.stopPropagation(); handleToggle(monitor.id, monitor.is_active) }}
                        className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                        title={monitor.is_active ? '暂停监测' : '恢复监测'}
                      >
                        <Power className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); handleDelete(monitor.id) }}
                        className="p-1.5 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                        title="删除"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <button
                      onClick={() => setSelectedMonitor(monitor)}
                      className="p-1"
                    >
                      <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* 添加对话框 */}
      {showAddDialog && (
        <AddMonitorDialog
          onClose={() => setShowAddDialog(false)}
          onCreated={m => {
            setMonitors(prev => [m, ...prev])
            setShowAddDialog(false)
          }}
        />
      )}

      {/* 详情面板 */}
      {selectedMonitor && (
        <MonitorDetailPanel
          monitor={selectedMonitor}
          onClose={() => setSelectedMonitor(null)}
        />
      )}
    </PageContainer>
  )
}
