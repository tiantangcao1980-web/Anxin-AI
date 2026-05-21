/**
 * CaseMarket · 案源市场（Editorial Luxury 改造 · Phase 1.13）
 *
 * 旧版用 PageContainer + Card grid + Badge variant + 表情符号提示。
 * 新版：ListPageTemplate + 1px hairline 卡 + tone-only status + 极简 Dialog。
 *
 * V2 架构：双端共用，按 primary_client 分发
 * - 服务方（provider）：browse 市场 + 投标
 * - 需求方（needer）：my-requests + publish
 */
import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import {
  Plus, Search, FileText, Briefcase, MapPin, DollarSign, Lightbulb,
} from 'lucide-react'

import { ListPageTemplate, ListPageStatus } from '@/components/ui/ListPageTemplate'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { useAuthStore } from '@/lib/store'
import { caseMarketApi } from '@/lib/api'
import { ConflictWarning, type ConflictWarningData } from '@/components/pro/ConflictWarning'
import { cn } from '@/components/ui/utils'

type Tab = 'browse' | 'my-bids' | 'my-requests' | 'publish'

interface CaseRequestItem {
  id: string
  title: string
  description: string
  legal_area: string
  urgency: string
  budget_min?: number
  budget_max?: number
  location?: string
  status: string
  view_count: number
  bid_count: number
  created_at: string
  expires_at?: string
  tags?: string[]
}

interface BidItem {
  id: string
  case_request_id: string
  lawyer_id: string
  proposal: string
  quoted_price?: number
  estimated_days?: number
  status: string
  created_at: string
}

const URGENCY_META: Record<string, { label: string; labelEn: string; tone: 'normal' | 'warning' | 'error' }> = {
  urgent:   { label: '紧急', labelEn: 'Urgent',   tone: 'error' },
  normal:   { label: '一般', labelEn: 'Normal',   tone: 'normal' },
  flexible: { label: '不急', labelEn: 'Flexible', tone: 'normal' },
}

const LEGAL_AREAS = [
  '合同', '劳动人事', '知识产权', '诉讼', '公司法务',
  '婚姻家庭', '房产', '刑事辩护', '金融', '其他',
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

export default function CaseMarket() {
  const { user } = useAuthStore()
  const isProvider = user?.primary_client === 'provider' || user?.role === 'platform_lawyer'

  const [tab, setTab] = useState<Tab>(isProvider ? 'browse' : 'my-requests')
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<CaseRequestItem[]>([])
  const [myBids, setMyBids] = useState<BidItem[]>([])

  const [bidDialogOpen, setBidDialogOpen] = useState(false)
  const [bidTarget, setBidTarget] = useState<CaseRequestItem | null>(null)
  const [bidProposal, setBidProposal] = useState('')
  const [bidPrice, setBidPrice] = useState('')
  const [bidDays, setBidDays] = useState('')

  const [publishDialogOpen, setPublishDialogOpen] = useState(false)
  const [pubTitle, setPubTitle] = useState('')
  const [pubDesc, setPubDesc] = useState('')
  const [pubArea, setPubArea] = useState(LEGAL_AREAS[0])
  const [pubUrgency, setPubUrgency] = useState<'urgent' | 'normal' | 'flexible'>('normal')
  const [pubLocation, setPubLocation] = useState('')
  const [pubBudgetMin, setPubBudgetMin] = useState('')
  const [pubBudgetMax, setPubBudgetMax] = useState('')

  const [conflictWarning, setConflictWarning] = useState<ConflictWarningData | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      if (tab === 'browse') {
        const result = await caseMarketApi.browseMarket({ limit: 50 })
        setItems(result?.items || [])
      } else if (tab === 'my-requests') {
        const result = await caseMarketApi.listMyRequests({ limit: 50 })
        setItems(result?.items || [])
      } else if (tab === 'my-bids') {
        const result = await caseMarketApi.listMyBids()
        setMyBids(Array.isArray(result) ? result : [])
      }
    } catch (e: any) {
      toast.error(e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => {
    if (tab !== 'publish') void loadData()
  }, [tab, loadData])

  const handleSubmitBid = async () => {
    if (!bidTarget) return
    if (!bidProposal.trim() || bidProposal.length < 10) { toast.error('请填写方案说明（至少 10 字）'); return }
    try {
      const result = await caseMarketApi.submitBid(bidTarget.id, {
        proposal: bidProposal,
        quoted_price: bidPrice ? Number(bidPrice) : undefined,
        estimated_days: bidDays ? Number(bidDays) : undefined,
      })
      if (result?.conflict_warning) setConflictWarning(result.conflict_warning)
      toast.success(result?.message || '投标已提交')
      setBidDialogOpen(false)
      setBidProposal(''); setBidPrice(''); setBidDays('')
      void loadData()
    } catch (e: any) {
      toast.error(e?.message || '投标失败')
    }
  }

  const handlePublish = async () => {
    if (!pubTitle || pubTitle.length < 5) { toast.error('标题至少 5 字'); return }
    if (!pubDesc || pubDesc.length < 10)  { toast.error('详细描述至少 10 字'); return }
    try {
      await caseMarketApi.publishRequest({
        title: pubTitle,
        description: pubDesc,
        legal_area: pubArea,
        urgency: pubUrgency,
        location: pubLocation || undefined,
        budget_min: pubBudgetMin ? Number(pubBudgetMin) : undefined,
        budget_max: pubBudgetMax ? Number(pubBudgetMax) : undefined,
      })
      toast.success('需求已发布，律师很快会看到')
      setPublishDialogOpen(false)
      setPubTitle(''); setPubDesc(''); setPubLocation(''); setPubBudgetMin(''); setPubBudgetMax('')
      setTab('my-requests')
    } catch (e: any) {
      toast.error(e?.message || '发布失败')
    }
  }

  const providerTabs: { key: Tab; label: string }[] = [
    { key: 'browse',  label: '案源市场' },
    { key: 'my-bids', label: '我的投标' },
  ]
  const neederTabs: { key: Tab; label: string }[] = [
    { key: 'my-requests', label: '我的需求' },
  ]
  const tabs = isProvider ? providerTabs : neederTabs

  return (
    <>
      <ListPageTemplate
        tracker={['Network', isProvider ? '案源市场' : '法律需求']}
        title={isProvider ? '案源市场' : '法律需求'}
        description={isProvider ? '按专业领域、地域筛选优质案源。' : '发布需求，让律师主动找您。'}
        actions={
          !isProvider ? (
            <button
              type="button"
              onClick={() => setPublishDialogOpen(true)}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              <Plus className="w-4 h-4 stroke-[1.5]" />
              <span>发布新需求</span>
            </button>
          ) : null
        }
        tabs={tabs.map((t) => ({ key: t.key, label: t.label }))}
        activeTab={tab}
        onTabChange={(k) => setTab(k as Tab)}
        loading={false}
        empty={false}
      >
        <li>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-border border-t border-l border-border">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-card border-r border-b border-border p-5">
                  <Skeleton className="h-32 w-full" />
                </div>
              ))}
            </div>
          ) : tab === 'my-bids' ? (
            <MyBidsList bids={myBids} />
          ) : items.length === 0 ? (
            <ListPageStatus
              tracker="Empty"
              title={tab === 'browse' ? '暂无待接单的需求' : '您还没有发布需求'}
              description={tab === 'browse' ? '稍后再来看看新案源。' : '发布第一个需求，律师将很快看到。'}
              action={tab === 'my-requests' && (
                <button
                  type="button"
                  onClick={() => setPublishDialogOpen(true)}
                  className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
                >
                  发布第一个需求
                </button>
              )}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-border border-t border-l border-border">
              {items.map((item, i) => {
                const urgency = URGENCY_META[item.urgency] || URGENCY_META.normal
                return (
                  <motion.article
                    key={item.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.02 }}
                    className="bg-card border-r border-b border-border p-5 flex flex-col group hover:bg-surface-2/40 transition-colors"
                  >
                    <header className="flex items-start justify-between gap-3 mb-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="font-serif text-[12px] text-muted-foreground tabular-nums">
                            {String(i + 1).padStart(2, '0')}
                          </span>
                          <ToneTag tone={urgency.tone} labelEn={urgency.labelEn} label={urgency.label} />
                        </div>
                        <h3 className="font-serif text-[17px] leading-tight text-foreground line-clamp-2">{item.title}</h3>
                      </div>
                    </header>
                    <p className="text-[13px] text-muted-foreground leading-relaxed line-clamp-3 mb-4">
                      {item.description}
                    </p>
                    <div className="flex items-center gap-3 text-[12px] text-muted-foreground mb-3 flex-wrap">
                      <span className="inline-flex items-center gap-1">
                        <Briefcase className="w-3 h-3 stroke-[1.5]" /> {item.legal_area}
                      </span>
                      {item.location && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="w-3 h-3 stroke-[1.5]" /> {item.location}
                        </span>
                      )}
                      {(item.budget_min || item.budget_max) && (
                        <span className="inline-flex items-center gap-1 text-primary">
                          <DollarSign className="w-3 h-3 stroke-[1.5]" />
                          {item.budget_min || 0} - {item.budget_max || '不限'}
                        </span>
                      )}
                    </div>
                    <footer className="mt-auto pt-3 border-t border-border/60 flex items-center justify-between">
                      <div className="text-[11px] text-muted-foreground uppercase tracking-[0.12em]">
                        Views {item.view_count} · Bids {item.bid_count}
                      </div>
                      {isProvider && tab === 'browse' ? (
                        <button
                          type="button"
                          onClick={() => { setBidTarget(item); setBidDialogOpen(true) }}
                          className="text-[11px] uppercase tracking-[0.12em] text-primary hover:text-primary-700 transition-colors"
                        >
                          立即投标 →
                        </button>
                      ) : (
                        <span className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                          {item.status}
                        </span>
                      )}
                    </footer>
                  </motion.article>
                )
              })}
            </div>
          )}
        </li>
      </ListPageTemplate>

      {/* 投标弹窗 */}
      <Dialog open={bidDialogOpen} onOpenChange={setBidDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-1">
              CaseMarket · Bid
            </div>
            <DialogTitle className="font-serif text-[20px]">
              投标：{bidTarget?.title}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
                Proposal · 方案说明（至少 10 字）
              </label>
              <textarea
                value={bidProposal}
                onChange={(e) => setBidProposal(e.target.value)}
                placeholder="请简述您的服务方案、执业经验、处理思路"
                rows={5}
                className="w-full px-3 py-2 bg-background border border-border text-[14px] focus:outline-none focus:border-primary transition-colors"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
                  Price · 报价（元）
                </label>
                <Input type="number" value={bidPrice} onChange={(e) => setBidPrice(e.target.value)} placeholder="可选" />
              </div>
              <div>
                <label className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
                  Days · 预计完成（天）
                </label>
                <Input type="number" value={bidDays} onChange={(e) => setBidDays(e.target.value)} placeholder="可选" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBidDialogOpen(false)}>取消</Button>
            <Button onClick={handleSubmitBid}>提交投标</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 发布需求弹窗 */}
      <Dialog open={publishDialogOpen} onOpenChange={setPublishDialogOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-1">
              CaseMarket · Publish
            </div>
            <DialogTitle className="font-serif text-[20px]">发布法律需求</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2 max-h-[60vh] overflow-y-auto">
            <Field label="Title · 标题 *">
              <Input value={pubTitle} onChange={(e) => setPubTitle(e.target.value)} placeholder="如：劳动合同起草咨询" />
            </Field>
            <Field label="Description · 详细描述 *">
              <textarea
                value={pubDesc}
                onChange={(e) => setPubDesc(e.target.value)}
                rows={5}
                className="w-full px-3 py-2 bg-background border border-border text-[14px] focus:outline-none focus:border-primary transition-colors"
                placeholder="请详细说明您遇到的法律问题"
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Area · 法律领域">
                <select
                  value={pubArea}
                  onChange={(e) => setPubArea(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border text-[14px] focus:outline-none focus:border-primary transition-colors"
                >
                  {LEGAL_AREAS.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </Field>
              <Field label="Urgency · 紧急度">
                <select
                  value={pubUrgency}
                  onChange={(e) => setPubUrgency(e.target.value as any)}
                  className="w-full px-3 py-2 bg-background border border-border text-[14px] focus:outline-none focus:border-primary transition-colors"
                >
                  <option value="urgent">紧急</option>
                  <option value="normal">一般</option>
                  <option value="flexible">不急</option>
                </select>
              </Field>
            </div>
            <Field label="City · 所在城市">
              <Input value={pubLocation} onChange={(e) => setPubLocation(e.target.value)} placeholder="如：北京（可选）" />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Budget Min · 预算下限（元）">
                <Input type="number" value={pubBudgetMin} onChange={(e) => setPubBudgetMin(e.target.value)} placeholder="可选" />
              </Field>
              <Field label="Budget Max · 预算上限（元）">
                <Input type="number" value={pubBudgetMax} onChange={(e) => setPubBudgetMax(e.target.value)} placeholder="可选" />
              </Field>
            </div>
            <aside className="border-l-2 border-primary/40 pl-3 py-1 flex items-start gap-2">
              <Lightbulb className="w-3.5 h-3.5 stroke-[1.5] text-primary mt-0.5 shrink-0" />
              <p className="text-[12px] text-muted-foreground leading-relaxed">
                发布后您的需求将进入案源市场，平台律师可投标。默认匿名发布，联系方式仅在您接受投标后对该律师可见。
              </p>
            </aside>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPublishDialogOpen(false)}>取消</Button>
            <Button onClick={handlePublish}>发布</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConflictWarning
        warning={conflictWarning}
        onConfirmAnyway={() => { setConflictWarning(null); toast.info('已记录您的知情同意') }}
        onWithdraw={() => {
          setConflictWarning(null)
          toast.success('投标已撤回')
          void loadData()
        }}
        onClose={() => setConflictWarning(null)}
      />
    </>
  )
}

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

function MyBidsList({ bids }: { bids: BidItem[] }) {
  if (bids.length === 0) {
    return (
      <ListPageStatus
        tracker="Empty"
        title="您还没有投标记录"
        description="去案源市场找一个适合的案件吧。"
      />
    )
  }
  const statusMeta = (s: string): { label: string; labelEn: string; tone: 'normal' | 'success' | 'warning' | 'error' } => {
    switch (s) {
      case 'accepted':  return { label: '已接受', labelEn: 'Accepted',  tone: 'success' }
      case 'rejected':  return { label: '已拒绝', labelEn: 'Rejected',  tone: 'error' }
      case 'withdrawn': return { label: '已撤回', labelEn: 'Withdrawn', tone: 'normal' }
      default:          return { label: '待审核', labelEn: 'Pending',   tone: 'warning' }
    }
  }
  return (
    <ol className="space-y-px">
      {bids.map((bid, i) => {
        const meta = statusMeta(bid.status)
        return (
          <li
            key={bid.id}
            className="flex items-start gap-6 py-5 px-3 -mx-3 border-b border-border/60"
          >
            <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 pt-1 tabular-nums">
              {String(i + 1).padStart(3, '0')}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <ToneTag tone={meta.tone} labelEn={meta.labelEn} label={meta.label} />
                <span className="text-[11px] text-muted-foreground tabular-nums">
                  {new Date(bid.created_at).toLocaleDateString()}
                </span>
              </div>
              <p className="text-[14px] text-foreground/90 line-clamp-2 leading-relaxed">{bid.proposal}</p>
              <div className="text-[12px] text-muted-foreground mt-2 flex items-center gap-4 flex-wrap">
                {bid.quoted_price !== undefined && <span>报价 · ¥{bid.quoted_price}</span>}
                {bid.estimated_days !== undefined && <span>工期 · {bid.estimated_days} 天</span>}
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
