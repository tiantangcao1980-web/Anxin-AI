/**
 * Pricing - 定价页面
 *
 * 3 列套餐卡片 + 月付/年付切换 + 功能对比表
 * 使用 design-tokens，推荐套餐用 cardStyle.highlight
 */

import { useState, useEffect } from'react'
import { icons } from'@/lib/icons'
import { toast } from'sonner'
import { cardStyle, heading, statusBadge, iconSize } from'@/lib/design-tokens'
import { PageContainer } from'@/components/ui/PageContainer'
import { ErrorState } from'@/components/common'
import { Button } from'@/components/ui/button'
import { Badge } from'@/components/ui/badge'
import { Switch } from'@/components/ui/switch'
import { Skeleton } from'@/components/ui/skeleton'
import { billingApi } from'@/lib/api'
import {
 Table,
 TableBody,
 TableCell,
 TableHead,
 TableHeader,
 TableRow,
} from'@/components/ui/table'

// ============ 类型定义 ============

interface PricingPlan {
 id: string
 name: string
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

// V2 架构：双端分组标签
type ClientTab = 'needer' | 'provider'
const CLIENT_TABS: { key: ClientTab; label: string; description: string }[] = [
  { key: 'needer', label: '个人/企业用户', description: '获取法律服务' },
  { key: 'provider', label: '律师/律所', description: '获客与案件管理' },
]

// 功能对比表 - 前端配置（后端暂不支持此结构化数据）
const FEATURE_COMPARE: FeatureRow[] = [
 { label:'AI 对话次数', basic:'50 次/月', pro:'200 次/月', enterprise:'不限' },
 { label:'存储空间', basic:'5GB', pro:'20GB', enterprise:'100GB' },
 { label:'合同审查', basic:'基础', pro:'高级', enterprise:'高级 + 定制' },
 { label:'找律师', basic: false, pro: true, enterprise: true },
 { label:'合规自检', basic: false, pro: true, enterprise: true },
 { label:'IM 消息', basic:'100 条/月', pro:'不限', enterprise:'不限' },
 { label:'团队协作', basic: false, pro: false, enterprise: true },
 { label:'API 接入', basic: false, pro: false, enterprise: true },
 { label:'专属顾问', basic: false, pro: false, enterprise: true },
]

// ============ 主组件 ============

export default function Pricing() {
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)
 const [annual, setAnnual] = useState(false)
 const [plans, setPlans] = useState<PricingPlan[]>([])
 // V2 架构：双端 Tab
 const [clientTab, setClientTab] = useState<ClientTab>('needer')

 useEffect(() => {
 let cancelled = false
 async function fetchPlans() {
 setLoading(true)
 setError(null)
 try {
 const data = await billingApi.listPlans()
 if (cancelled) return

 const planList = Array.isArray(data) ? data : data?.plans || []
 setPlans(planList.map((p: any) => ({
 id: p.id || p.code ||'',
 name: p.name ||'',
 monthlyPrice: p.monthly_price ?? p.monthlyPrice ?? 0,
 recommended: p.recommended ?? p.code ==='pro',
 features: p.features || [],
 highlight: p.highlight || (p.recommended ?'最受欢迎' : undefined),
 })))
 } catch (err: any) {
 if (!cancelled) {
 console.error('套餐加载失败:', err)
 setError(err?.message ||'数据加载失败，请稍后重试')
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

 function getPriceLabel(monthly: number): string {
 if (annual) {
 return `¥${getPrice(monthly).toLocaleString()}/年`
 }
 return `¥${monthly}/月`
 }

 async function handleSubscribe(planId: string) {
 try {
   const result = await billingApi.createV2Subscription({
     plan_id: planId,
     client_type: clientTab,
     payment_method:'wechat',
     billing_cycle: annual ?'yearly' :'monthly',
   })
   toast.success(`订阅创建成功，应付 ¥${result?.amount ?? 0}，正在跳转支付...`)
   // TODO: 跳转到支付页面 / 调用支付 SDK
   const paymentUrl = result?.payment_order?.payment_url
   if (paymentUrl) {
     setTimeout(() => { window.location.href = paymentUrl }, 800)
   } else {
     setTimeout(() => { window.location.href ='/my-subscription' }, 1200)
   }
 } catch (err: any) {
   const msg = err?.message ||''
   if (msg.includes('您在该客户端已有活跃订阅')) {
     toast.error('您已有活跃订阅，请先在账单中心取消或等待到期')
   } else if (msg.includes('不适用于')) {
     toast.error('该方案不适用于您选择的客户端类型')
   } else {
     toast.error(msg ||'订阅创建失败，请稍后重试')
   }
 }
 }

 if (loading) {
 return (
 <PageContainer title="选择套餐">
 <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
 {Array.from({ length: 3 }).map((_, i) => (
 <Skeleton key={i} className="h-96 rounded-xl" />
 ))}
 </div>
 </PageContainer>
 )
 }

 if (error) {
 return (
 <PageContainer title="选择套餐">
 <ErrorState title="加载失败" message={error} onRetry={() => window.location.reload()} />
 </PageContainer>
 )
 }

 if (plans.length === 0) {
 return (
 <PageContainer title="选择套餐" description="为您的法律服务需求选择最合适的方案">
 <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
 <icons.Box className={`${iconSize.xl} text-muted-foreground mb-3`} />
 <p className={heading.section}>暂无可用套餐</p>
 <p className="text-sm text-muted-foreground mt-1">套餐信息正在准备中，请稍后再来</p>
 </div>
 </PageContainer>
 )
 }

 return (
 <PageContainer title="选择套餐" description="为您的法律服务需求选择最合适的方案">
 {/* V2: 双端 Tab 切换 */}
 <div className="flex items-center justify-center gap-2 mb-6">
  {CLIENT_TABS.map(tab => (
    <button
      key={tab.key}
      onClick={() => setClientTab(tab.key)}
      className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
        clientTab === tab.key
          ? 'bg-primary text-primary-foreground shadow-sm'
          : 'bg-muted text-muted-foreground hover:bg-muted/80'
      }`}
    >
      <div>{tab.label}</div>
      <div className={`text-[10px] mt-0.5 ${clientTab === tab.key ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}>{tab.description}</div>
    </button>
  ))}
 </div>

 {/* 月付/年付切换 */}
 <div className="flex items-center justify-center gap-3 py-2">
 <span className={`text-sm font-medium ${!annual ?'text-foreground' :'text-muted-foreground'}`}>
 月付
 </span>
 <Switch checked={annual} onCheckedChange={setAnnual} />
 <span className={`text-sm font-medium ${annual ?'text-foreground' :'text-muted-foreground'}`}>
 年付
 </span>
 {annual && (
 <Badge className={statusBadge.success}>省 20%</Badge>
 )}
 </div>

 {/* 套餐卡片 */}
 <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
 {plans.map(plan => (
 <div
 key={plan.id}
 className={`relative ${
 plan.recommended
 ? `${cardStyle.highlight} ring-2 ring-primary/30`
 : cardStyle.interactive
 } flex flex-col`}
 >
 {/* 推荐标识 */}
 {plan.highlight && (
 <div className="absolute -top-3 left-1/2 -translate-x-1/2">
 <Badge className="bg-primary text-primary-foreground text-xs px-3">{plan.highlight}</Badge>
 </div>
 )}

 {/* 套餐名称 */}
 <h3 className={`${heading.section} text-center mt-2`}>{plan.name}</h3>

 {/* 价格 — 使用 title-display + num-tabular 保证精致与等宽 */}
 <div className="text-center py-4">
 <span className="title-display num-tabular text-[40px] text-foreground">
 ¥{annual ? Math.round(plan.monthlyPrice * 0.8) : plan.monthlyPrice}
 </span>
 <span className="text-sm text-foreground-tertiary ml-1.5">/月</span>
 {annual && (
 <p className="text-xs text-muted-foreground mt-1">
 年付 ¥{getPrice(plan.monthlyPrice).toLocaleString()}，
 <span className="text-success font-medium">
 省 ¥{Math.round(plan.monthlyPrice * 12 * 0.2).toLocaleString()}
 </span>
 </p>
 )}
 </div>

 {/* 功能列表 */}
 <ul className="space-y-2.5 flex-1 mb-6">
 {plan.features.map(f => (
 <li key={f} className="flex items-start gap-2 text-sm">
 <icons.Check className={`${iconSize.sm} text-success mt-0.5 shrink-0`} />
 <span className="text-foreground">{f}</span>
 </li>
 ))}
 </ul>

 {/* 按钮 */}
 <Button
 className="w-full"
 variant={plan.recommended ?'default' :'outline'}
 onClick={() => handleSubscribe(plan.id)}
 >
 立即开通
 </Button>
 </div>
 ))}
 </div>

 {/* 功能对比表 */}
 <div className="pt-4">
 <h2 className={`${heading.section} text-center mb-4`}>功能对比</h2>
 <div className={`${cardStyle.base} overflow-hidden`}>
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead className="w-40">功能</TableHead>
 <TableHead className="text-center">基础版</TableHead>
 <TableHead className="text-center bg-primary/5">
 专业版
 <Badge className="ml-1.5 text-[10px] bg-primary text-primary-foreground">推荐</Badge>
 </TableHead>
 <TableHead className="text-center">企业版</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {FEATURE_COMPARE.map(row => (
 <TableRow key={row.label}>
 <TableCell className="text-sm font-medium">{row.label}</TableCell>
 <TableCell className="text-center">
 <FeatureValue value={row.basic} />
 </TableCell>
 <TableCell className="text-center bg-primary/5">
 <FeatureValue value={row.pro} />
 </TableCell>
 <TableCell className="text-center">
 <FeatureValue value={row.enterprise} />
 </TableCell>
 </TableRow>
 ))}
 </TableBody>
 </Table>
 </div>
 </div>
 </PageContainer>
 )
}

// ============ 辅助组件 ============

function FeatureValue({ value }: { value: string | boolean }) {
 if (typeof value ==='boolean') {
 return value ? (
 <icons.Check className={`${iconSize.sm} text-success mx-auto`} />
 ) : (
 <icons.Minus className={`${iconSize.sm} text-muted-foreground/40 mx-auto`} />
 )
 }
 return <span className="text-sm text-foreground">{value}</span>
}
