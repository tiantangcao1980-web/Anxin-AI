/**
 * Contracts · 合同管理（Editorial Luxury 改造 · Phase 1.11）
 *
 * 旧版用 PageContainer + StatGrid + cardStyle.base divide-y + statusBadge 色块。
 * 新版：ListPageTemplate + tone-only StatusChip + 进度细线 + 极简弹窗。
 */
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import {
  Plus, Search, Upload, FileText, Eye, AlertTriangle, CheckCircle, Clock, Loader2, X,
} from 'lucide-react'

import { ListPageTemplate, ListPageStatus } from '@/components/ui/ListPageTemplate'
import { contractsApi, type Contract, type ContractCreate } from '@/lib/api'
import { ESignDialog } from '@/components/esign/ESignDialog'
import { cn } from '@/components/ui/utils'
import ContractReview from './ContractReview'

type StatusKey = 'draft' | 'pending_review' | 'under_review' | 'approved' | 'signed' | 'active' | 'expired'
type RiskKey = 'low' | 'medium' | 'high' | 'critical'

const STATUS_META: Record<StatusKey, { label: string; labelEn: string; tone: 'normal' | 'success' | 'warning' | 'error' }> = {
  draft:          { label: '草稿',   labelEn: 'Draft',    tone: 'normal' },
  pending_review: { label: '待审核', labelEn: 'Pending',  tone: 'warning' },
  under_review:   { label: '审核中', labelEn: 'Review',   tone: 'warning' },
  approved:       { label: '已批准', labelEn: 'Approved', tone: 'success' },
  signed:         { label: '已签署', labelEn: 'Signed',   tone: 'success' },
  active:         { label: '生效中', labelEn: 'Active',   tone: 'success' },
  expired:        { label: '已过期', labelEn: 'Expired',  tone: 'error' },
}

const RISK_META: Record<RiskKey, { label: string; labelEn: string; tone: 'success' | 'warning' | 'error'; icon: typeof CheckCircle }> = {
  low:      { label: '低风险',   labelEn: 'Low',      tone: 'success', icon: CheckCircle },
  medium:   { label: '中风险',   labelEn: 'Medium',   tone: 'warning', icon: Clock },
  high:     { label: '高风险',   labelEn: 'High',     tone: 'warning', icon: AlertTriangle },
  critical: { label: '极高风险', labelEn: 'Critical', tone: 'error',   icon: AlertTriangle },
}

const CONTRACT_TYPES = [
  { value: 'purchase',    label: '采购合同' },
  { value: 'sales',       label: '销售合同' },
  { value: 'service',     label: '服务协议' },
  { value: 'labor',       label: '劳动合同' },
  { value: 'lease',       label: '租赁合同' },
  { value: 'nda',         label: '保密协议' },
  { value: 'cooperation', label: '合作协议' },
  { value: 'other',       label: '其他' },
]

function ToneTag({ tone, label, labelEn }: { tone: 'normal' | 'success' | 'warning' | 'error'; label: string; labelEn: string }) {
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

export default function Contracts() {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page] = useState(1)
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [esignDialog, setEsignDialog] = useState<{ open: boolean; contract: Contract | null }>({ open: false, contract: null })

  const loadContracts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await contractsApi.list({ page, page_size: 20 })
      setContracts(response.items)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '合同数据加载失败'
      setContracts([])
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { void loadContracts() }, [loadContracts])

  // KPI 计算
  const counts = {
    pending: contracts.filter((c) => c.status === 'pending_review').length,
    review:  contracts.filter((c) => c.status === 'under_review').length,
    high:    contracts.filter((c) => c.risk_level === 'high' || c.risk_level === 'critical').length,
    done:    contracts.filter((c) => c.status === 'approved' || c.status === 'signed').length,
  }

  const kpiRow = (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border border-t border-l border-border mb-8">
      <KpiCell tracker="Pending"  label="待审核"  value={counts.pending} icon={Clock} />
      <KpiCell tracker="Review"   label="审核中"  value={counts.review}  icon={Loader2} />
      <KpiCell tracker="HighRisk" label="高风险" value={counts.high}    icon={AlertTriangle} tone="error" />
      <KpiCell tracker="Done"     label="已完成" value={counts.done}    icon={CheckCircle} tone="success" />
    </div>
  )

  return (
    <>
      <ListPageTemplate
        tracker={['Workspace', '合同管理']}
        title="合同管理"
        description="AI 智能审查合同 — 识别风险条款，全流程管控。"
        actions={
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground transition-colors"
            >
              <Plus className="w-4 h-4 stroke-[1.5]" />
              <span>新建合同</span>
            </button>
            <button
              type="button"
              onClick={() => setShowReviewModal(true)}
              className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground transition-colors"
            >
              <Search className="w-4 h-4 stroke-[1.5]" />
              <span>快捷审查</span>
            </button>
            <button
              type="button"
              onClick={() => setShowReviewModal(true)}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              <Upload className="w-4 h-4 stroke-[1.5]" />
              <span>完整审查</span>
            </button>
          </div>
        }
        beforeList={kpiRow}
        loading={loading}
        error={error}
        empty={!loading && !error && contracts.length === 0}
        emptyState={
          <ListPageStatus
            tracker="Empty"
            title="暂无合同"
            description="上传第一份合同，让 AI 完成全文风险审查。"
            action={
              <button
                type="button"
                onClick={() => setShowReviewModal(true)}
                className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
              >
                上传合同
              </button>
            }
          />
        }
      >
        {contracts.map((contract, i) => {
          const status = STATUS_META[contract.status as StatusKey] || STATUS_META.draft
          const risk = contract.risk_level ? RISK_META[contract.risk_level as RiskKey] : null
          const RiskIcon = risk?.icon
          const typeLabel = CONTRACT_TYPES.find((t) => t.value === contract.contract_type)?.label || contract.contract_type
          return (
            <li key={contract.id}>
              <button
                type="button"
                onClick={() => setShowReviewModal(true)}
                className="group w-full text-left flex items-start gap-6 py-6 px-3 -mx-3 border-b border-border/60 transition-colors hover:bg-surface-2/40"
              >
                <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 pt-1 tabular-nums">
                  {String(i + 1).padStart(3, '0')}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-4 flex-wrap mb-2">
                    <ToneTag tone={status.tone} labelEn={status.labelEn} label={status.label} />
                    {risk && RiskIcon && (
                      <span className={cn(
                        'inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em]',
                        risk.tone === 'success' && 'text-success',
                        risk.tone === 'warning' && 'text-warning',
                        risk.tone === 'error'   && 'text-destructive',
                      )}>
                        <RiskIcon className="w-3 h-3 stroke-[1.5]" />
                        <span>{risk.labelEn}</span>
                        <span className="text-foreground/30" aria-hidden>·</span>
                        <span className="normal-case tracking-normal text-foreground/80">{risk.label}</span>
                      </span>
                    )}
                  </div>
                  <h3 className="font-serif text-[18px] leading-tight text-foreground truncate">{contract.title}</h3>
                  <div className="text-[12px] text-muted-foreground mt-2 flex items-center gap-3 flex-wrap">
                    <span>{contract.contract_number || '—'}</span>
                    <span>· {typeLabel}</span>
                    {contract.amount && <span>· ¥{contract.amount.toLocaleString()}</span>}
                  </div>
                  {contract.risk_score !== null && contract.risk_score !== undefined && (
                    <div className="mt-3 flex items-center gap-3 max-w-md">
                      <span className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground shrink-0">Risk</span>
                      <div className="flex-1 h-px bg-border relative">
                        <div
                          className={cn(
                            'absolute top-0 left-0 h-px transition-[width]',
                            contract.risk_score >= 0.7 ? 'bg-destructive' :
                            contract.risk_score >= 0.3 ? 'bg-warning' :
                            'bg-success',
                          )}
                          style={{ width: `${Math.max(contract.risk_score * 100, contract.risk_score > 0 ? 2 : 0)}%` }}
                        />
                      </div>
                      <span className={cn(
                        'text-[11px] tabular-nums font-medium shrink-0',
                        contract.risk_score >= 0.7 ? 'text-destructive' :
                        contract.risk_score >= 0.3 ? 'text-warning' :
                        'text-success',
                      )}>
                        {(contract.risk_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
                <div
                  role="group"
                  onClick={(e) => e.stopPropagation()}
                  onKeyDown={(e) => e.stopPropagation()}
                  className="flex items-center gap-2 shrink-0 pt-1"
                >
                  {(contract.status === 'approved' || contract.status === 'active') && (
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setEsignDialog({ open: true, contract }) }}
                      className="inline-flex items-center gap-1.5 border border-border bg-card hover:bg-surface-2 px-3 py-1.5 text-[12px] text-foreground transition-colors"
                      title="发起电子签署"
                    >
                      <FileText className="w-3.5 h-3.5 stroke-[1.5]" />
                      <span>发起签署</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setShowReviewModal(true) }}
                    className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                    title="查看"
                  >
                    <Eye className="w-4 h-4 stroke-[1.5]" />
                  </button>
                </div>
              </button>
            </li>
          )
        })}
      </ListPageTemplate>

      {showReviewModal && <ReviewModal onClose={() => setShowReviewModal(false)} />}
      {showCreateModal && (
        <CreateContractModal
          onClose={() => setShowCreateModal(false)}
          onComplete={loadContracts}
        />
      )}
      <ESignDialog
        open={esignDialog.open}
        onOpenChange={(open) => setEsignDialog({ ...esignDialog, open })}
        contract={esignDialog.contract ? {
          id: esignDialog.contract.id,
          title: esignDialog.contract.title,
          contractType: esignDialog.contract.contract_type,
        } : null}
        onCompleted={loadContracts}
      />
    </>
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

/* ------------ 审查弹窗 ------------ */
function ReviewModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-foreground/40 flex items-center justify-center z-50">
      <div className="bg-background border border-border w-full max-w-6xl mx-4 h-[90vh] overflow-hidden flex flex-col">
        <header className="px-6 py-4 border-b border-border flex items-center justify-between">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Contracts · Review
            </div>
            <h2 className="font-serif text-[20px] mt-1">合同智能审查</h2>
          </div>
          <button onClick={onClose} className="p-1.5 text-muted-foreground hover:text-foreground transition-colors" title="关闭">
            <X className="w-5 h-5 stroke-[1.5]" />
          </button>
        </header>
        <div className="flex-1 min-h-0 overflow-auto">
          <ContractReview embedded />
        </div>
      </div>
    </div>
  )
}

/* ------------ 新建合同弹窗 ------------ */
function CreateContractModal({ onClose, onComplete }: { onClose: () => void; onComplete: () => void }) {
  const [formData, setFormData] = useState<ContractCreate>({ title: '', contract_type: 'other' })
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim()) { toast.error('请输入合同标题'); return }
    setSubmitting(true)
    try {
      await contractsApi.create(formData)
      toast.success('合同创建成功')
      onComplete()
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  const inputClass = 'w-full bg-background border border-border px-4 py-2.5 text-[14px] text-foreground placeholder:text-muted-foreground/70 transition-colors focus:outline-none focus:border-primary'

  return (
    <div className="fixed inset-0 bg-foreground/40 flex items-center justify-center z-50">
      <div className="bg-background border border-border w-full max-w-lg mx-4">
        <header className="px-6 py-5 border-b border-border">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Contracts · New
          </div>
          <h2 className="font-serif text-[20px] mt-1">新建合同</h2>
        </header>
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
              Title · 合同标题 *
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className={inputClass}
              placeholder="请输入合同标题"
            />
          </div>
          <div>
            <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
              Type · 合同类型
            </label>
            <select
              value={formData.contract_type}
              onChange={(e) => setFormData({ ...formData, contract_type: e.target.value })}
              className={inputClass}
            >
              {CONTRACT_TYPES.map((type) => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
              Amount · 合同金额
            </label>
            <input
              type="number"
              value={formData.amount || ''}
              onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || undefined })}
              className={inputClass}
              placeholder="请输入合同金额"
            />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="border border-border bg-card hover:bg-surface-2 px-5 py-2 text-[13px] text-foreground transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-primary hover:bg-primary-700 disabled:opacity-50 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              {submitting ? <Loader2 className="w-4 h-4 stroke-[1.5] animate-spin" /> : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
