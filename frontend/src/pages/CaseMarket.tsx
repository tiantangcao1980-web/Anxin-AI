/**
 * CaseMarket — 案源市场（双端共用页面，根据 primary_client 渲染不同视图）
 *
 * V2 架构：
 * - 需求方（needer）：发布需求 + 查看我的需求 + 查看收到的投标
 * - 服务方（provider）：浏览市场 + 投标 + 查看我的投标
 */

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { useAuthStore } from '@/lib/store'
import { caseMarketApi } from '@/lib/api'
import { ConflictWarning, type ConflictWarningData } from '@/components/pro/ConflictWarning'

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

const URGENCY_CONFIG: Record<string, { label: string; color: string }> = {
  urgent: { label: '紧急', color: 'text-destructive' },
  normal: { label: '一般', color: 'text-foreground' },
  flexible: { label: '不急', color: 'text-muted-foreground' },
}

const LEGAL_AREAS = [
  '合同', '劳动人事', '知识产权', '诉讼', '公司法务',
  '婚姻家庭', '房产', '刑事辩护', '金融', '其他',
]

export default function CaseMarket() {
  const { user } = useAuthStore()
  const isProvider = user?.primary_client === 'provider' || user?.role === 'platform_lawyer'

  const [tab, setTab] = useState<Tab>(isProvider ? 'browse' : 'my-requests')
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<CaseRequestItem[]>([])
  const [myBids, setMyBids] = useState<BidItem[]>([])

  // 投标弹窗
  const [bidDialogOpen, setBidDialogOpen] = useState(false)
  const [bidTarget, setBidTarget] = useState<CaseRequestItem | null>(null)
  const [bidProposal, setBidProposal] = useState('')
  const [bidPrice, setBidPrice] = useState<string>('')
  const [bidDays, setBidDays] = useState<string>('')

  // 发布弹窗
  const [publishDialogOpen, setPublishDialogOpen] = useState(false)
  const [pubTitle, setPubTitle] = useState('')
  const [pubDesc, setPubDesc] = useState('')
  const [pubArea, setPubArea] = useState(LEGAL_AREAS[0])
  const [pubUrgency, setPubUrgency] = useState<'urgent' | 'normal' | 'flexible'>('normal')
  const [pubLocation, setPubLocation] = useState('')
  const [pubBudgetMin, setPubBudgetMin] = useState<string>('')
  const [pubBudgetMax, setPubBudgetMax] = useState<string>('')

  // 冲突警告
  const [conflictWarning, setConflictWarning] = useState<ConflictWarningData | null>(null)
  // 触发冲突警告的投标 id（用于"撤回投标"）
  const [conflictBidId, setConflictBidId] = useState<string | null>(null)

  const loadData = async () => {
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
  }

  useEffect(() => {
    if (tab !== 'publish') loadData()
  }, [tab])

  const handleSubmitBid = async () => {
    if (!bidTarget) return
    if (!bidProposal.trim() || bidProposal.length < 10) {
      toast.error('请填写方案说明（至少 10 字）')
      return
    }
    try {
      const result = await caseMarketApi.submitBid(bidTarget.id, {
        proposal: bidProposal,
        quoted_price: bidPrice ? Number(bidPrice) : undefined,
        estimated_days: bidDays ? Number(bidDays) : undefined,
      })
      // 检查冲突警告
      if (result?.conflict_warning) {
        setConflictWarning(result.conflict_warning)
        setConflictBidId(result?.id ?? result?.bid_id ?? null)
      }
      toast.success(result?.message || '投标已提交')
      setBidDialogOpen(false)
      setBidProposal(''); setBidPrice(''); setBidDays('')
      loadData()
    } catch (e: any) {
      toast.error(e?.message || '投标失败')
    }
  }

  const handleWithdrawBid = async (bidId: string | null) => {
    if (!bidId) {
      toast.error('未找到要撤回的投标')
      return
    }
    try {
      await caseMarketApi.withdrawBid(bidId)
      toast.success('投标已撤回')
      await loadData()
    } catch (e: any) {
      toast.error(e?.message || '撤回失败')
    }
  }

  const handlePublish = async () => {
    if (!pubTitle || pubTitle.length < 5) { toast.error('标题至少 5 字'); return }
    if (!pubDesc || pubDesc.length < 10) { toast.error('详细描述至少 10 字'); return }
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

  // 服务方端标签
  const providerTabs: { key: Tab; label: string; icon: keyof typeof icons }[] = [
    { key: 'browse', label: '案源市场', icon: 'Search' },
    { key: 'my-bids', label: '我的投标', icon: 'FileText' },
  ]

  // 需求方端标签
  const neederTabs: { key: Tab; label: string; icon: keyof typeof icons }[] = [
    { key: 'my-requests', label: '我的需求', icon: 'Briefcase' },
  ]

  const tabs = isProvider ? providerTabs : neederTabs

  return (
    <PageContainer
      title={isProvider ? '案源市场' : '法律需求'}
      description={isProvider ? '按专业领域、地域筛选优质案源' : '发布需求，让律师主动找您'}
      actions={
        !isProvider ? (
          <Button onClick={() => setPublishDialogOpen(true)}>
            <icons.Add className="w-4 h-4 mr-1.5" />
            发布新需求
          </Button>
        ) : null
      }
    >
      {/* Tab 切换 */}
      <div className="flex gap-2 mb-6 border-b border-border">
        {tabs.map((t) => {
          const Icon = icons[t.icon] || icons.FileText
          const active = tab === t.key
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2.5 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 ${
                active ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="w-4 h-4" />
              {t.label}
            </button>
          )
        })}
      </div>

      {/* 内容 */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
      ) : tab === 'my-bids' ? (
        <MyBidsList bids={myBids} onWithdraw={handleWithdrawBid} />
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <icons.Briefcase className="w-10 h-10 mx-auto text-muted-foreground/40 mb-3" />
          <p className="text-sm text-muted-foreground">
            {tab === 'browse' ? '暂无待接单的需求' : '您还没有发布需求'}
          </p>
          {tab === 'my-requests' && (
            <Button variant="link" onClick={() => setPublishDialogOpen(true)} className="mt-2">
              发布第一个需求 →
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map((item) => (
            <motion.div key={item.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="h-full hover:border-primary/40 transition-colors">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base line-clamp-2">{item.title}</CardTitle>
                    <Badge variant="outline" className={URGENCY_CONFIG[item.urgency]?.color}>
                      {URGENCY_CONFIG[item.urgency]?.label || item.urgency}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground line-clamp-3 mb-3">
                    {item.description}
                  </p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
                    <span className="flex items-center gap-1">
                      <icons.Briefcase className="w-3 h-3" /> {item.legal_area}
                    </span>
                    {item.location && (
                      <span className="flex items-center gap-1">
                        <icons.MapPin className="w-3 h-3" /> {item.location}
                      </span>
                    )}
                    {(item.budget_min || item.budget_max) && (
                      <span className="flex items-center gap-1 text-primary">
                        <icons.DollarSign className="w-3 h-3" />
                        {item.budget_min || 0} - {item.budget_max || '不限'}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] text-muted-foreground">
                      浏览 {item.view_count} · 投标 {item.bid_count}
                    </div>
                    {isProvider && tab === 'browse' ? (
                      <Button size="sm" onClick={() => { setBidTarget(item); setBidDialogOpen(true) }}>
                        立即投标
                      </Button>
                    ) : (
                      <Badge variant="secondary">{item.status}</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* 投标弹窗 */}
      <Dialog open={bidDialogOpen} onOpenChange={setBidDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>投标：{bidTarget?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="text-xs font-medium mb-1 block">方案说明（至少 10 字）</label>
              <textarea
                value={bidProposal}
                onChange={(e) => setBidProposal(e.target.value)}
                placeholder="请简述您的服务方案、执业经验、处理思路"
                rows={5}
                className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary/50"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium mb-1 block">报价（元）</label>
                <Input type="number" value={bidPrice} onChange={(e) => setBidPrice(e.target.value)} placeholder="可选" />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">预计完成（天）</label>
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
            <DialogTitle>发布法律需求</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2 max-h-[60vh] overflow-y-auto">
            <div>
              <label className="text-xs font-medium mb-1 block">标题 *</label>
              <Input value={pubTitle} onChange={(e) => setPubTitle(e.target.value)} placeholder="如：劳动合同起草咨询" />
            </div>
            <div>
              <label className="text-xs font-medium mb-1 block">详细描述 *</label>
              <textarea
                value={pubDesc}
                onChange={(e) => setPubDesc(e.target.value)}
                rows={5}
                className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:border-primary/50"
                placeholder="请详细说明您遇到的法律问题"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium mb-1 block">法律领域</label>
                <select
                  value={pubArea}
                  onChange={(e) => setPubArea(e.target.value)}
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm"
                >
                  {LEGAL_AREAS.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">紧急度</label>
                <select
                  value={pubUrgency}
                  onChange={(e) => setPubUrgency(e.target.value as any)}
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm"
                >
                  <option value="urgent">紧急</option>
                  <option value="normal">一般</option>
                  <option value="flexible">不急</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium mb-1 block">所在城市</label>
              <Input value={pubLocation} onChange={(e) => setPubLocation(e.target.value)} placeholder="如：北京（可选）" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium mb-1 block">预算下限（元）</label>
                <Input type="number" value={pubBudgetMin} onChange={(e) => setPubBudgetMin(e.target.value)} placeholder="可选" />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">预算上限（元）</label>
                <Input type="number" value={pubBudgetMax} onChange={(e) => setPubBudgetMax(e.target.value)} placeholder="可选" />
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              💡 发布后您的需求将进入案源市场，平台律师可投标。默认匿名发布，联系方式仅在您接受投标后对该律师可见。
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPublishDialogOpen(false)}>取消</Button>
            <Button onClick={handlePublish}>发布</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 利益冲突警告 */}
      <ConflictWarning
        warning={conflictWarning}
        onConfirmAnyway={() => { setConflictWarning(null); setConflictBidId(null); toast.info('已记录您的知情同意') }}
        onWithdraw={async () => {
          const bidId = conflictBidId
          setConflictWarning(null)
          setConflictBidId(null)
          await handleWithdrawBid(bidId)
        }}
        onClose={() => { setConflictWarning(null); setConflictBidId(null) }}
      />
    </PageContainer>
  )
}

function MyBidsList({ bids, onWithdraw }: { bids: BidItem[]; onWithdraw: (bidId: string) => void | Promise<void> }) {
  if (bids.length === 0) {
    return (
      <div className="text-center py-16">
        <icons.FileText className="w-10 h-10 mx-auto text-muted-foreground/40 mb-3" />
        <p className="text-sm text-muted-foreground">您还没有投标记录</p>
      </div>
    )
  }
  const statusColor = (s: string) => {
    if (s === 'accepted') return 'text-success'
    if (s === 'rejected') return 'text-destructive'
    if (s === 'withdrawn') return 'text-muted-foreground'
    return 'text-warning'
  }
  const statusLabel = (s: string) => ({
    pending: '待审核', accepted: '已接受', rejected: '已拒绝', withdrawn: '已撤回',
  }[s] || s)
  return (
    <div className="space-y-3">
      {bids.map((bid) => (
        <Card key={bid.id}>
          <CardContent className="p-4">
            <div className="flex items-start justify-between gap-3 mb-2">
              <p className="text-sm text-foreground line-clamp-2 flex-1">{bid.proposal}</p>
              <Badge variant="outline" className={statusColor(bid.status)}>
                {statusLabel(bid.status)}
              </Badge>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              {bid.quoted_price !== undefined && (
                <span>报价：¥{bid.quoted_price}</span>
              )}
              {bid.estimated_days !== undefined && (
                <span>工期：{bid.estimated_days} 天</span>
              )}
              <span className="ml-auto">{new Date(bid.created_at).toLocaleDateString()}</span>
            </div>
            {bid.status === 'pending' && (
              <div className="mt-3 flex justify-end">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onWithdraw(bid.id)}
                >
                  <icons.X className="w-3.5 h-3.5 mr-1" />
                  撤回投标
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
