/**
 * Leads · 案源/线索管理（Editorial Luxury 示范页 — Phase 1 模板验证）
 *
 * 2026-05-20 Reset 重写：原版使用 PageContainer + cardStyle.interactive（V2 SaaS 风格），
 * 改为 Editorial Luxury — 使用 ListPageTemplate / DetailPageTemplate / PanelSection 三个模板。
 *
 * 保留全部功能：
 *   - 列表 / Pipeline 双视图切换
 *   - Pipeline 5 阶段看板（new / contacted / qualified / proposal / won，lost 单独）
 *   - 详情内嵌（点击线索 → 进入详情子视图）
 *   - moveStage 状态推进（API + toast）
 *   - 加载 / 错误 / 空 三态
 *   - 跟进记录时间线
 *
 * 颜色：仅墨色 + status tone（success / warning / destructive），不用 V2 色块 chip
 * 文字：serif H1 + caption micro + body — 不用 font-bold
 */

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'

import { ListPageTemplate } from '@/components/ui/ListPageTemplate'
import { DetailPageTemplate, PanelSection } from '@/components/ui/PageTemplates'
import { leadsApi, type LeadItem } from '@/lib/api'
import { cn } from '@/components/ui/utils'

type LeadStage = 'new' | 'contacted' | 'qualified' | 'proposal' | 'won' | 'lost'

interface FollowUp {
  id: string
  date: string
  content: string
  type: '电话' | '面谈' | '邮件' | '微信'
}

interface Lead {
  id: string
  clientName: string
  contactInfo: string
  source: string
  caseType: string
  estimatedAmount: number
  stage: LeadStage
  assignee: string
  followUps: FollowUp[]
  createdAt: string
}

// 阶段元数据（仅文字 + 状态 tone，无背景色块）
const stageMeta: Record<LeadStage, { label: string; labelEn: string; tone: 'normal' | 'success' | 'warning' | 'error' }> = {
  new:       { label: '新线索',   labelEn: 'New',       tone: 'normal'  },
  contacted: { label: '已联系',   labelEn: 'Contacted', tone: 'normal'  },
  qualified: { label: '需求确认', labelEn: 'Qualified', tone: 'warning' },
  proposal:  { label: '报价中',   labelEn: 'Proposal',  tone: 'warning' },
  won:       { label: '已签约',   labelEn: 'Won',       tone: 'success' },
  lost:      { label: '已流失',   labelEn: 'Lost',      tone: 'error'   },
}

const STAGES_PIPELINE: LeadStage[] = ['new', 'contacted', 'qualified', 'proposal', 'won']

function apiToLead(item: LeadItem): Lead {
  return {
    id: item.id,
    clientName: item.clientName,
    contactInfo: item.contactInfo || '',
    source: item.source || '',
    caseType: item.caseType || '',
    estimatedAmount: item.estimatedAmount,
    stage: (item.stage as LeadStage) || 'new',
    assignee: item.assignee || '',
    followUps: (item.followUps || []) as FollowUp[],
    createdAt: item.createdAt?.split('T')[0] || '',
  }
}

function StageChip({ stage }: { stage: LeadStage }) {
  const meta = stageMeta[stage]
  const toneClass = {
    normal:  'text-muted-foreground',
    success: 'text-success',
    warning: 'text-warning',
    error:   'text-destructive',
  }[meta.tone]
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em]', toneClass)}>
      <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
      <span>{meta.labelEn}</span>
      <span className="text-foreground/30" aria-hidden>·</span>
      <span className="normal-case tracking-normal text-foreground/80">{meta.label}</span>
    </span>
  )
}

export default function Leads() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [viewMode, setViewMode] = useState<'pipeline' | 'list'>('pipeline')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadLeads = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await leadsApi.list({ page_size: 100 })
      setLeads((data.items || []).map(apiToLead))
    } catch (err) {
      setLeads([])
      setError(err instanceof Error ? err.message : '加载线索失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadLeads() }, [loadLeads])

  const moveStage = async (leadId: string, newStage: LeadStage) => {
    setLeads((prev) => prev.map((l) => (l.id === leadId ? { ...l, stage: newStage } : l)))
    if (selectedLead?.id === leadId) setSelectedLead({ ...selectedLead, stage: newStage })
    toast.success('线索状态已更新')
    try {
      await leadsApi.updateStage(leadId, newStage)
    } catch {
      // 静默失败 — 视为本地状态先行，等下次 list 同步
    }
  }

  const activeLeads = leads.filter((l) => l.stage !== 'lost')
  const totalAmount = activeLeads.reduce((sum, l) => sum + l.estimatedAmount, 0)

  // ============================================================
  // 详情视图
  // ============================================================
  if (selectedLead) {
    const stageIndex = STAGES_PIPELINE.indexOf(selectedLead.stage)
    const inFlow = selectedLead.stage !== 'won' && selectedLead.stage !== 'lost'
    return (
      <DetailPageTemplate
        tracker={['Leads', '线索详情', selectedLead.clientName]}
        title={selectedLead.clientName}
        description={`${selectedLead.caseType} · ${selectedLead.contactInfo}`}
        actions={
          <button
            type="button"
            onClick={() => setSelectedLead(null)}
            className="text-[13px] text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1.5"
          >
            <span>←</span>
            <span>返回列表</span>
          </button>
        }
      >
        {/* 进度条（5 段） */}
        <div className="mb-10">
          <div className="flex items-center justify-between mb-3">
            <StageChip stage={selectedLead.stage} />
            {selectedLead.stage !== 'lost' && (
              <span className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground tabular-nums">
                {Math.min(stageIndex + 1, STAGES_PIPELINE.length)} / {STAGES_PIPELINE.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {STAGES_PIPELINE.map((s, i) => (
              <div
                key={s}
                className={cn(
                  'flex-1 h-px',
                  i <= stageIndex && selectedLead.stage !== 'lost' ? 'bg-primary' : 'bg-border',
                )}
              />
            ))}
          </div>
        </div>

        {/* KPI 区 */}
        <div className="grid grid-cols-2 gap-px bg-border mb-10 border-t border-l border-border">
          <div className="bg-card px-5 py-4 border-r border-b border-border">
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">Estimated</div>
            <div className="font-serif text-[28px] leading-[1.1] text-foreground mt-1 tabular-nums">
              {selectedLead.estimatedAmount.toLocaleString()} <span className="text-[14px] text-muted-foreground">元</span>
            </div>
          </div>
          <div className="bg-card px-5 py-4 border-r border-b border-border">
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">Source</div>
            <div className="text-[18px] text-foreground mt-1">{selectedLead.source || '未指定'}</div>
          </div>
        </div>

        {/* 操作 */}
        {inFlow && (
          <div className="flex gap-3 mb-10">
            {stageIndex < STAGES_PIPELINE.length - 1 && (
              <button
                onClick={() => void moveStage(selectedLead.id, STAGES_PIPELINE[stageIndex + 1])}
                className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors inline-flex items-center gap-2"
              >
                <span>推进至 {stageMeta[STAGES_PIPELINE[stageIndex + 1]].label}</span>
                <span>→</span>
              </button>
            )}
            <button
              onClick={() => void moveStage(selectedLead.id, 'lost')}
              className="text-destructive border border-destructive/40 hover:bg-destructive/5 px-5 py-2.5 text-[14px] transition-colors"
            >
              标记流失
            </button>
          </div>
        )}

        {/* 跟进记录 */}
        <PanelSection
          tracker="Follow-ups"
          title="跟进记录"
          description={`共 ${selectedLead.followUps.length} 条`}
        >
          {selectedLead.followUps.length === 0 ? (
            <p className="text-[14px] text-muted-foreground py-2">暂无跟进记录</p>
          ) : (
            <ol className="space-y-px">
              {selectedLead.followUps.map((fu, i) => (
                <li key={fu.id} className="flex gap-4 py-4 border-b border-border/60 last:border-b-0">
                  <span className="font-serif text-[13px] text-muted-foreground w-8 shrink-0 tabular-nums pt-1">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-baseline gap-3 mb-1 flex-wrap">
                      <span className="text-[14px] font-medium text-foreground">{fu.date}</span>
                      <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                        {fu.type}
                      </span>
                    </div>
                    <p className="text-[14px] text-foreground/80 leading-relaxed">{fu.content}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </PanelSection>
      </DetailPageTemplate>
    )
  }

  // ============================================================
  // 列表视图（pipeline 看板 / list 平面）
  // ============================================================
  const viewSwitcher = (
    <div className="inline-flex items-center text-[13px] border border-border" role="tablist">
      <button
        onClick={() => setViewMode('pipeline')}
        role="tab"
        aria-selected={viewMode === 'pipeline'}
        className={cn(
          'px-3 py-1.5 transition-colors',
          viewMode === 'pipeline' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground',
        )}
      >
        看板
      </button>
      <button
        onClick={() => setViewMode('list')}
        role="tab"
        aria-selected={viewMode === 'list'}
        className={cn(
          'px-3 py-1.5 transition-colors border-l border-border',
          viewMode === 'list' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground',
        )}
      >
        列表
      </button>
    </div>
  )

  return (
    <ListPageTemplate
      tracker={['Growth', '案源管理']}
      title="案源 / 线索"
      description={`${activeLeads.length} 条活跃线索 · 预估总额 ${totalAmount.toLocaleString()} 元`}
      toolbarRight={viewSwitcher}
      loading={loading}
      error={error}
      empty={!loading && !error && leads.length === 0}
      emptyState={
        <div className="flex flex-col items-center text-center py-20 px-6">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-3">
            Empty
          </div>
          <h3 className="font-serif text-[24px] leading-[1.3] tracking-[-0.01em] font-medium text-foreground">
            暂无线索数据
          </h3>
          <p className="mt-3 text-[14px] text-foreground/70 max-w-[40ch]">
            运行种子数据后即可验证真实案源流程，或手动新建第一条线索。
          </p>
          <button
            onClick={() => void loadLeads()}
            className="mt-6 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
          >
            重新加载
          </button>
        </div>
      }
    >
      {viewMode === 'pipeline' ? (
        // 看板：5 stages 横向，每 stage 一列
        <li className="block">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-px bg-border border-l border-t border-border overflow-x-auto">
            {STAGES_PIPELINE.map((stage) => {
              const stageLeads = leads.filter((l) => l.stage === stage)
              const stageAmount = stageLeads.reduce((s, l) => s + l.estimatedAmount, 0)
              return (
                <section
                  key={stage}
                  className="bg-card border-r border-b border-border min-w-[180px] flex flex-col"
                >
                  <header className="px-3 py-3 border-b border-border/60 flex items-center justify-between gap-2">
                    <StageChip stage={stage} />
                    <span className="text-[11px] text-muted-foreground tabular-nums">
                      {stageAmount.toLocaleString()}
                    </span>
                  </header>
                  <div className="flex-1 divide-y divide-border/60">
                    {stageLeads.length === 0 ? (
                      <p className="px-3 py-6 text-[12px] text-muted-foreground/60 text-center">—</p>
                    ) : (
                      stageLeads.map((lead) => (
                        <button
                          key={lead.id}
                          onClick={() => setSelectedLead(lead)}
                          className="w-full text-left px-3 py-3 hover:bg-surface-2/40 transition-colors"
                        >
                          <h4 className="font-serif text-[15px] leading-tight text-foreground truncate">
                            {lead.clientName}
                          </h4>
                          <p className="text-[12px] text-muted-foreground mt-1 truncate">{lead.caseType}</p>
                          <div className="flex items-center justify-between mt-2 text-[11px] text-muted-foreground">
                            <span className="tabular-nums">{lead.estimatedAmount.toLocaleString()}</span>
                            <span className="truncate ml-2">{lead.assignee}</span>
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                </section>
              )
            })}
          </div>
        </li>
      ) : (
        // 列表：扁平
        leads.map((lead, i) => (
          <li key={lead.id}>
            <button
              type="button"
              onClick={() => setSelectedLead(lead)}
              className="w-full text-left flex items-start gap-6 py-5 px-3 -mx-3 border-b border-border/60 transition-colors hover:bg-surface-2/40"
            >
              <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 pt-1 tabular-nums">
                {String(i + 1).padStart(3, '0')}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-3 flex-wrap">
                  <h3 className="font-serif text-[18px] leading-tight text-foreground truncate">
                    {lead.clientName}
                  </h3>
                  <StageChip stage={lead.stage} />
                </div>
                <div className="text-[13px] text-muted-foreground mt-2 flex items-center gap-4 flex-wrap">
                  <span>{lead.caseType}</span>
                  {lead.source && <span>来源 · {lead.source}</span>}
                  {lead.assignee && <span>负责人 · {lead.assignee}</span>}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="font-serif text-[18px] text-foreground tabular-nums">
                  {lead.estimatedAmount.toLocaleString()}
                </div>
                <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground mt-0.5">CNY</div>
              </div>
            </button>
          </li>
        ))
      )}
    </ListPageTemplate>
  )
}
