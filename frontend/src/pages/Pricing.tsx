/**
 * Pricing · 定价（Editorial Luxury 改造 · Phase 1.17）
 *
 * 旧版用 PageContainer + cardStyle.highlight ring 圆角卡片 + 药丸状端 Tab。
 * 新版：EditorialPageHeader + 1px hairline 套餐三栏 + Editorial 下划线端 Tab + 极简表格。
 *
 * 保留导出：normalizePricingPlans / filterPlansForClient（被 Pricing.test.ts 引用）
 */
import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Check, Minus, Package } from 'lucide-react'

import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import { ErrorState } from '@/components/common'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { billingApi } from '@/lib/api'
import { PaymentDialog } from '@/components/checkout/PaymentDialog'
import { cn } from '@/components/ui/utils'

interface PricingPlan {
  id: string
  name: string
  clientType: PlanClientType
  monthlyPrice: number
  recommended?: boolean
  features: string[]
  highlight?: string
}

interface FeatureRow {
  label: string
  basic: string | boolean
  pro: string | boolean
  enterprise: string | boolean
}

type ClientTab = 'needer' | 'provider'
type PlanClientType = ClientTab | 'both'

const CLIENT_TABS: { key: ClientTab; label: string; labelEn: string; description: string }[] = [
  { key: 'needer',   labelEn: 'Needer',   label: '个人/企业用户', description: '获取法律服务' },
  { key: 'provider', labelEn: 'Provider', label: '律师/律所',     description: '获客与案件管理' },
]

const FEATURE_COMPARE: FeatureRow[] = [
  { label: 'AI 对话次数', basic: '50 次/月', pro: '200 次/月', enterprise: '不限' },
  { label: '存储空间',    basic: '5GB',      pro: '20GB',      enterprise: '100GB' },
  { label: '合同审查',    basic: '基础',     pro: '高级',      enterprise: '高级 + 定制' },
  { label: '找律师',      basic: false,      pro: true,        enterprise: true },
  { label: '合规自检',    basic: false,      pro: true,        enterprise: true },
  { label: 'IM 消息',     basic: '100 条/月', pro: '不限',      enterprise: '不限' },
  { label: '团队协作',    basic: false,      pro: false,       enterprise: true },
  { label: 'API 接入',    basic: false,      pro: false,       enterprise: true },
  { label: '专属顾问',    basic: false,      pro: false,       enterprise: true },
]

export function normalizePricingPlans(raw: any): PricingPlan[] {
  const planList = Array.isArray(raw) ? raw : raw?.plans || []
  return planList.map((p: any) => ({
    id: p.id || p.code || '',
    name: p.name || '',
    clientType: normalizePlanClientType(p.client_type || p.clientType),
    monthlyPrice: p.monthly_price ?? p.monthlyPrice ?? p.base_price ?? 0,
    recommended: p.recommended ?? p.highlight ?? p.code === 'pro',
    features: normalizePlanFeatures(p.features),
    highlight: p.highlight || (p.recommended ? '最受欢迎' : undefined),
  }))
}

export function filterPlansForClient(plans: PricingPlan[], clientTab: ClientTab): PricingPlan[] {
  return plans.filter((plan) => plan.clientType === clientTab || plan.clientType === 'both')
}

function normalizePlanClientType(value: unknown): PlanClientType {
  return value === 'provider' || value === 'both' ? value : 'needer'
}

function normalizePlanFeatures(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String)
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .filter(([, enabled]) => Boolean(enabled))
      .map(([key]) => key)
  }
  return []
}

export default function Pricing() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [annual, setAnnual] = useState(false)
  const [plans, setPlans] = useState<PricingPlan[]>([])
  const [clientTab, setClientTab] = useState<ClientTab>('needer')
  const [paymentDialog, setPaymentDialog] = useState<{
    open: boolean
    order: { orderId: string; planName: string; amount: number; paymentMethod: 'wechat' | 'alipay' } | null
  }>({ open: false, order: null })

  useEffect(() => {
    let cancelled = false
    async function fetchPlans() {
      setLoading(true)
      setError(null)
      try {
        const data = await billingApi.listPlans()
        if (cancelled) return
        setPlans(normalizePricingPlans(data))
      } catch (err: any) {
        if (!cancelled) {
          console.error('套餐加载失败:', err)
          setError(err?.message || '数据加载失败，请稍后重试')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPlans()
    return () => { cancelled = true }
  }, [])

  function getPrice(monthly: number): number {
    return annual ? Math.round(monthly * 12 * 0.8) : monthly
  }

  async function handleSubscribe(planId: string) {
    try {
      const plan = plans.find((p) => p.id === planId)
      const result = await billingApi.createV2Subscription({
        plan_id: planId,
        client_type: clientTab,
        payment_method: 'wechat',
        billing_cycle: annual ? 'yearly' : 'monthly',
      })
      setPaymentDialog({
        open: true,
        order: {
          orderId: result?.payment_order?.order_id || `DEMO-${Date.now()}`,
          planName: plan?.name || '未知套餐',
          amount: result?.amount ?? getPrice(plan?.monthlyPrice ?? 0),
          paymentMethod: 'wechat',
        },
      })
    } catch (err: any) {
      const msg = err?.message || ''
      if (msg.includes('您在该客户端已有活跃订阅')) toast.error('您已有活跃订阅，请先在账单中心取消或等待到期')
      else if (msg.includes('不适用于')) toast.error('该方案不适用于您选择的客户端类型')
      else toast.error(msg || '订阅创建失败，请稍后重试')
    }
  }

  if (loading) {
    return (
      <Shell tracker={['Account', '选择套餐']} title="选择套餐" description="为您的法律服务需求选择最合适的方案。">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-border border-t border-l border-border">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-card border-r border-b border-border p-6">
              <Skeleton className="h-80 w-full" />
            </div>
          ))}
        </div>
      </Shell>
    )
  }

  if (error) {
    return (
      <Shell tracker={['Account', '选择套餐']} title="选择套餐" description="为您的法律服务需求选择最合适的方案。">
        <ErrorState title="加载失败" message={error} onRetry={() => window.location.reload()} />
      </Shell>
    )
  }

  if (plans.length === 0) {
    return (
      <Shell tracker={['Account', '选择套餐']} title="选择套餐" description="为您的法律服务需求选择最合适的方案。">
        <EmptyPlans title="暂无可用套餐" hint="套餐信息正在准备中，请稍后再来。" />
      </Shell>
    )
  }

  const visiblePlans = filterPlansForClient(plans, clientTab)

  return (
    <Shell tracker={['Account', '选择套餐']} title="选择套餐" description="为您的法律服务需求选择最合适的方案。">
      {/* 双端 Tab — Editorial 下划线 */}
      <nav className="flex justify-center items-end gap-12 border-b border-border mb-10" role="tablist" aria-label="客户端类型">
        {CLIENT_TABS.map((tab) => {
          const active = clientTab === tab.key
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setClientTab(tab.key)}
              className={cn(
                'relative pb-3 text-center transition-colors',
                active ? 'after:absolute after:left-0 after:right-0 after:bottom-0 after:h-px after:bg-primary' : '',
              )}
            >
              <div className={cn(
                'text-[11px] font-medium uppercase tracking-[0.16em]',
                active ? 'text-foreground' : 'text-muted-foreground',
              )}>
                {tab.labelEn} · {tab.label}
              </div>
              <div className={cn('text-[12px] mt-0.5', active ? 'text-foreground/70' : 'text-muted-foreground/60')}>
                {tab.description}
              </div>
            </button>
          )
        })}
      </nav>

      {/* 月付/年付切换 */}
      <div className="flex items-center justify-center gap-4 mb-12">
        <span className={cn('text-[12px] uppercase tracking-[0.12em]', !annual ? 'text-foreground' : 'text-muted-foreground')}>
          Monthly · 月付
        </span>
        <Switch checked={annual} onCheckedChange={setAnnual} />
        <span className={cn('text-[12px] uppercase tracking-[0.12em]', annual ? 'text-foreground' : 'text-muted-foreground')}>
          Yearly · 年付
        </span>
        {annual && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em] text-success ml-2">
            <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
            <span>Save 20%</span>
          </span>
        )}
      </div>

      {/* 套餐三栏 */}
      {visiblePlans.length === 0 ? (
        <EmptyPlans title="暂无适用套餐" hint="当前端侧套餐正在准备中。" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-border border-t border-l border-border mb-16">
          {visiblePlans.map((plan, i) => (
            <article
              key={plan.id}
              className={cn(
                'relative bg-card border-r border-b border-border p-8 flex flex-col',
                plan.recommended && 'bg-surface-2/30',
              )}
            >
              {plan.recommended && plan.highlight && (
                <span className="absolute top-0 left-0 right-0 h-px bg-primary" aria-hidden />
              )}
              <header className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground tabular-nums">
                    Plan · {String(i + 1).padStart(2, '0')}
                  </span>
                  {plan.recommended && plan.highlight && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em] text-primary">
                      <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
                      <span>{plan.highlight}</span>
                    </span>
                  )}
                </div>
                <h3 className="font-serif text-[24px] text-foreground">{plan.name}</h3>
              </header>

              {/* 价格 */}
              <div className="mb-6">
                <div className="flex items-baseline gap-1">
                  <span className="font-serif text-[40px] leading-none text-foreground tabular-nums">
                    ¥{annual ? Math.round(plan.monthlyPrice * 0.8) : plan.monthlyPrice}
                  </span>
                  <span className="text-[13px] text-muted-foreground">/月</span>
                </div>
                {annual ? (
                  <p className="text-[12px] text-muted-foreground mt-2">
                    年付 ¥{getPrice(plan.monthlyPrice).toLocaleString()} · 省{' '}
                    <span className="text-success">¥{Math.round(plan.monthlyPrice * 12 * 0.2).toLocaleString()}</span>
                  </p>
                ) : (
                  <p className="text-[12px] text-muted-foreground/60 mt-2">按月计费，无长期承诺。</p>
                )}
              </div>

              {/* 功能列表 */}
              <ul className="space-y-2.5 flex-1 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-[13px]">
                    <Check className="w-3.5 h-3.5 stroke-[1.5] text-success mt-0.5 shrink-0" />
                    <span className="text-foreground/90">{f}</span>
                  </li>
                ))}
              </ul>

              <button
                type="button"
                onClick={() => void handleSubscribe(plan.id)}
                className={cn(
                  'w-full py-2.5 text-[13px] font-medium transition-colors',
                  plan.recommended
                    ? 'bg-primary hover:bg-primary-700 text-primary-foreground'
                    : 'border border-border bg-background hover:bg-surface-2 text-foreground',
                )}
              >
                立即开通
              </button>
            </article>
          ))}
        </div>
      )}

      {/* 功能对比 */}
      <section>
        <header className="text-center mb-8">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Compare · 功能对比
          </div>
          <h2 className="font-serif text-[24px] text-foreground mt-1">逐项功能对比</h2>
        </header>
        <div className="border-t border-l border-r border-border">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-surface-2/40">
                <th className="text-left text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground px-5 py-3 w-1/3">
                  Feature · 功能
                </th>
                <th className="text-center text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground px-5 py-3">
                  基础版
                </th>
                <th className="text-center text-[11px] font-medium uppercase tracking-[0.16em] text-foreground px-5 py-3 bg-surface-2/60">
                  <span className="inline-flex items-center gap-2">
                    <span>专业版</span>
                    <span className="inline-flex items-center gap-1 text-[10px] text-primary">
                      <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
                      推荐
                    </span>
                  </span>
                </th>
                <th className="text-center text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground px-5 py-3">
                  企业版
                </th>
              </tr>
            </thead>
            <tbody>
              {FEATURE_COMPARE.map((row) => (
                <tr key={row.label} className="border-b border-border/60">
                  <td className="px-5 py-3 text-[14px] text-foreground">{row.label}</td>
                  <td className="px-5 py-3 text-center"><FeatureValue value={row.basic} /></td>
                  <td className="px-5 py-3 text-center bg-surface-2/30"><FeatureValue value={row.pro} /></td>
                  <td className="px-5 py-3 text-center"><FeatureValue value={row.enterprise} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <PaymentDialog
        open={paymentDialog.open}
        onOpenChange={(open) => setPaymentDialog({ ...paymentDialog, open })}
        order={paymentDialog.order}
      />
    </Shell>
  )
}

function Shell({
  tracker, title, description, children,
}: {
  tracker: string[]
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-10">
        <EditorialPageHeader tracker={tracker} title={title} description={description} />
        {children}
      </div>
    </div>
  )
}

function EmptyPlans({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="text-center py-20">
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
        Pricing · 空状态
      </div>
      <Package className="w-12 h-12 stroke-[1] text-foreground/20 mx-auto mb-4" />
      <p className="font-serif text-[20px] text-foreground mb-1">{title}</p>
      <p className="text-[13px] text-muted-foreground">{hint}</p>
    </div>
  )
}

function FeatureValue({ value }: { value: string | boolean }) {
  if (typeof value === 'boolean') {
    return value ? (
      <Check className="w-4 h-4 stroke-[1.5] text-success mx-auto" />
    ) : (
      <Minus className="w-4 h-4 stroke-[1.5] text-muted-foreground/40 mx-auto" />
    )
  }
  return <span className="text-[14px] text-foreground">{value}</span>
}
