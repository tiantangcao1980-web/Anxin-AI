/**
 * MySubscription - 我的订阅页面
 *
 * 当前套餐信息 + 用量进度条 + 订单历史 + 退款申请
 * 使用 PageContainer + design-tokens
 */

import { useState, useEffect } from'react'
import { icons } from'@/lib/icons'
import { toast } from'sonner'
import { cardStyle, heading, statusBadge, iconSize } from'@/lib/design-tokens'
import { PageContainer, PageSection } from'@/components/ui/PageContainer'
import { Button } from'@/components/ui/button'
import { Badge } from'@/components/ui/badge'
import { Switch } from'@/components/ui/switch'
import { Progress } from'@/components/ui/progress'
import { billingApi } from'@/lib/api'
import { ErrorState, LoadingState } from'@/components/ui-unified'
import {
 Table,
 TableBody,
 TableCell,
 TableHead,
 TableHeader,
 TableRow,
} from'@/components/ui/table'

// ============ 类型定义 ============

interface SubscriptionInfo {
 id: string
 clientType: ClientType
 planName: string
 planId: string
 status: string
 expiresAt: string
 autoRenew: boolean
 aiUsed: number
 aiTotal: number
 storageUsedGB: number
 storageTotalGB: number
}

interface OrderRecord {
 id: string
 date: string
 description: string
 amount: number
 status: string
}

interface RefundRecord {
 id: string
 orderId: string
 amount: number
 reason: string
 status: string
 createdAt: string
}

type ClientType = 'needer' | 'provider'

const CLIENTS: { type: ClientType; label: string; description: string; icon: typeof icons.User }[] = [
 { type:'needer', label:'需求方端', description:'个人与企业法务需求', icon: icons.User },
 { type:'provider', label:'服务方端', description:'律师与服务机构工作台', icon: icons.Briefcase },
]

const SUBSCRIPTION_STATUS_MAP: Record<string, { label: string; badge: string }> = {
 pending: { label:'待支付', badge: statusBadge.warning },
 trial: { label:'试用中', badge: statusBadge.info },
 active: { label:'生效中', badge: statusBadge.success },
 past_due: { label:'待续费', badge: statusBadge.warning },
 cancelled: { label:'已取消', badge: statusBadge.neutral },
 expired: { label:'已过期', badge: statusBadge.error },
}

const ORDER_STATUS_MAP: Record<string, { label: string; badge: string }> = {
 paid: { label:'已支付', badge: statusBadge.success },
 pending: { label:'待支付', badge: statusBadge.warning },
 refunded: { label:'已退款', badge: statusBadge.neutral },
 refund_pending: { label:'退款中', badge: statusBadge.info },
 failed: { label:'支付失败', badge: statusBadge.error },
 cancelled: { label:'已关闭', badge: statusBadge.neutral },
}

const REFUND_STATUS_MAP: Record<string, { label: string; badge: string }> = {
 pending: { label:'审批中', badge: statusBadge.warning },
 approved: { label:'已通过', badge: statusBadge.success },
 rejected: { label:'已拒绝', badge: statusBadge.error },
 processed: { label:'已处理', badge: statusBadge.success },
}

export function normalizeSubscriptionData(raw: any): SubscriptionInfo[] {
 const list = Array.isArray(raw)
 ? raw
 : Array.isArray(raw?.subscriptions)
 ? raw.subscriptions
 : raw?.subscription
 ? [raw.subscription]
 : raw
 ? [raw]
 : []

 return list
 .filter(Boolean)
 .map((subscription: any) => {
 const plan = subscription.plan || {}
 return {
 id: subscription.id || subscription.subscription_id ||'',
 clientType: normalizeClientType(subscription.client_type || subscription.clientType),
 planName: plan.name || subscription.plan_name || subscription.planName ||'未知套餐',
 planId: subscription.plan_id || subscription.planId || plan.id ||'',
 status: subscription.status ||'pending',
 expiresAt:
 subscription.current_period_end
 || subscription.expires_at
 || subscription.expiresAt
 || subscription.trial_ends_at
 ||'',
 autoRenew: subscription.auto_renew ?? subscription.autoRenew ?? false,
 aiUsed: subscription.ai_used ?? subscription.aiUsed ?? 0,
 aiTotal: subscription.ai_total ?? subscription.aiTotal ?? plan.ai_quota ?? 0,
 storageUsedGB: subscription.storage_used_gb ?? subscription.storageUsedGB ?? 0,
 storageTotalGB:
 subscription.storage_total_gb
 ?? subscription.storageTotalGB
 ?? plan.storage_gb
 ?? 0,
 }
 })
}

export function normalizeOrderData(raw: any): OrderRecord[] {
 const subscriptions = Array.isArray(raw)
 ? raw
 : Array.isArray(raw?.subscriptions)
 ? raw.subscriptions
 : raw?.subscription
 ? [raw.subscription]
 : []
 const nestedOrders = subscriptions.flatMap((subscription: any) => (
 Array.isArray(subscription?.orders) ? subscription.orders : []
 ))
 const orderList = [
 ...(Array.isArray(raw?.orders) ? raw.orders : []),
 ...nestedOrders,
 ]
 return orderList.map((order: any) => ({
 id: order.id,
 date: order.date || order.created_at || order.createdAt ||'',
 description: order.description || order.order_type ||'订阅订单',
 amount: Number(order.amount || 0),
 status: order.status ||'pending',
 }))
}

export function normalizeRefundData(raw: any): RefundRecord[] {
 const refundList = Array.isArray(raw) ? raw : raw?.refunds || []
 return refundList.map((r: any) => ({
 id: r.id,
 orderId: r.order_id || r.orderId ||'',
 amount: r.amount || 0,
 reason: r.reason ||'',
 status: r.status ||'pending',
 createdAt: r.created_at || r.createdAt ||'',
 }))
}

function pickSubscriptionForClient(
 subscriptions: SubscriptionInfo[],
 clientType: ClientType
): SubscriptionInfo | null {
 const statusRank: Record<string, number> = {
 active: 0,
 trial: 1,
 past_due: 2,
 pending: 3,
 cancelled: 4,
 expired: 5,
 }
 const candidates = subscriptions.filter(sub => sub.clientType === clientType)
 if (candidates.length === 0) return null
 return [...candidates].sort((a, b) => {
 const statusDelta = (statusRank[a.status] ?? 99) - (statusRank[b.status] ?? 99)
 if (statusDelta !== 0) return statusDelta
 return String(b.expiresAt).localeCompare(String(a.expiresAt))
 })[0]
}

function normalizeClientType(value: unknown): ClientType {
 return value ==='provider' ?'provider' :'needer'
}

// ============ 主组件 ============

export default function MySubscription() {
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)
 const [subscriptions, setSubscriptions] = useState<SubscriptionInfo[]>([])
 const [orders, setOrders] = useState<OrderRecord[]>([])
 const [refunds, setRefunds] = useState<RefundRecord[]>([])

 useEffect(() => {
 let cancelled = false
 async function fetchData() {
 setLoading(true)
 setError(null)
 try {
 const [subData, refundData] = await Promise.all([
 billingApi.getMySubscriptions(),
 billingApi.listRefunds(),
 ])
 if (cancelled) return

 setSubscriptions(normalizeSubscriptionData(subData))
 setOrders(normalizeOrderData(subData))

 // 退款记录
 if (refundData) {
 setRefunds(normalizeRefundData(refundData))
 }
 } catch (err: any) {
 if (!cancelled) {
 console.error('订阅数据加载失败:', err)
 setError(err?.message ||'数据加载失败，请稍后重试')
 }
 } finally {
 if (!cancelled) setLoading(false)
 }
 }
 fetchData()
 return () => { cancelled = true }
 }, [])

 function handleAutoRenewToggle(clientType: ClientType, val: boolean) {
 setSubscriptions(prev => prev.map(sub => (
 sub.clientType === clientType ? { ...sub, autoRenew: val } : sub
 )))
 toast.success(val ?'已开启自动续费' :'已关闭自动续费')
 }

 async function handleRefundRequest(orderId: string) {
 const order = orders.find(o => o.id === orderId)
 if (!order) return
 try {
 await billingApi.requestRefund({
 order_id: orderId,
 amount: order.amount,
 reason:'用户申请退款',
 })
 setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status:'refund_pending' as const } : o))
 setRefunds(prev => [
 ...prev,
 {
 id: `REF-${Date.now()}`,
 orderId,
 amount: order.amount,
 reason:'用户申请退款',
 status:'pending' as const,
 createdAt: new Date().toISOString().slice(0, 10),
 },
 ])
 toast.success('退款申请已提交')
 } catch (err: any) {
 toast.error(err?.message ||'退款申请失败，请稍后重试')
 }
 }

 if (loading) {
 return (
 <PageContainer title="我的订阅">
 <LoadingState variant="skeleton" rows={4} />
 </PageContainer>
 )
 }

 if (error) {
 return (
 <PageContainer title="我的订阅">
 <ErrorState title="加载失败" message={error} onRetry={() => window.location.reload()} />
 </PageContainer>
 )
 }

 const subscriptionsByClient = {
 needer: pickSubscriptionForClient(subscriptions, 'needer'),
 provider: pickSubscriptionForClient(subscriptions, 'provider'),
 }

 return (
 <PageContainer title="我的订阅" description="管理套餐、查看用量和订单记录">
 <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
 {CLIENTS.map(client => (
 <SubscriptionPanel
 key={client.type}
 client={client}
 subscription={subscriptionsByClient[client.type]}
 onAutoRenewToggle={handleAutoRenewToggle}
 />
 ))}
 </div>

 {/* 订单历史 */}
 <PageSection title="订单历史">
 <div className={`${cardStyle.base} overflow-hidden`}>
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>日期</TableHead>
 <TableHead>描述</TableHead>
 <TableHead>金额</TableHead>
 <TableHead>状态</TableHead>
 <TableHead className="text-right">操作</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {orders.length === 0 ? (
 <TableRow>
 <TableCell colSpan={5} className="text-center py-8">
 <p className={heading.muted}>暂无订单记录</p>
 </TableCell>
 </TableRow>
 ) : (
 orders.map(order => (
 <TableRow key={order.id}>
 <TableCell className="text-sm">{order.date}</TableCell>
 <TableCell className="text-sm">{order.description}</TableCell>
 <TableCell className="text-sm font-medium">¥{order.amount}</TableCell>
 <TableCell>
 <Badge className={`text-xs px-2 py-0.5 ${ORDER_STATUS_MAP[order.status]?.badge || statusBadge.neutral}`}>
 {ORDER_STATUS_MAP[order.status]?.label || order.status}
 </Badge>
 </TableCell>
 <TableCell className="text-right">
 {order.status ==='paid' && (
 <Button
 size="sm"
 variant="ghost"
 className="h-7 text-xs"
 onClick={() => handleRefundRequest(order.id)}
 >
 申请退款
 </Button>
 )}
 </TableCell>
 </TableRow>
 ))
 )}
 </TableBody>
 </Table>
 </div>
 </PageSection>

 {/* 退款记录 */}
 <PageSection title="退款记录">
 {refunds.length === 0 ? (
 <div className={`${cardStyle.flat} text-center py-8`}>
 <p className={heading.muted}>暂无退款记录</p>
 </div>
 ) : (
 <div className="space-y-3">
 {refunds.map(r => (
 <div key={r.id} className={cardStyle.compact}>
 <div className="flex items-center justify-between">
 <div>
 <div className="flex items-center gap-2 mb-1">
 <span className="text-sm font-medium text-foreground">退款 ¥{r.amount}</span>
 <Badge className={`text-xs px-2 py-0.5 ${REFUND_STATUS_MAP[r.status]?.badge || statusBadge.neutral}`}>
 {REFUND_STATUS_MAP[r.status]?.label || r.status}
 </Badge>
 </div>
 <p className="text-xs text-muted-foreground">
 订单号：{r.orderId} | 申请时间：{r.createdAt}
 </p>
 <p className="text-xs text-muted-foreground mt-0.5">原因：{r.reason}</p>
 </div>
 </div>
 </div>
 ))}
 </div>
 )}
 </PageSection>
 </PageContainer>
 )
}

// ============ 辅助组件 ============

function SubscriptionPanel({
 client,
 subscription,
 onAutoRenewToggle,
}: {
 client: (typeof CLIENTS)[number]
 subscription: SubscriptionInfo | null
 onAutoRenewToggle: (clientType: ClientType, value: boolean) => void
}) {
 const Icon = client.icon
 const aiPercent = subscription?.aiTotal
 ? Math.round((subscription.aiUsed / subscription.aiTotal) * 100)
 : 0
 const storagePercent = subscription?.storageTotalGB
 ? Math.round((subscription.storageUsedGB / subscription.storageTotalGB) * 100)
 : 0

 if (!subscription) {
 return (
 <div className={`${cardStyle.base} flex min-h-[260px] flex-col justify-between`}>
 <div>
 <div className="flex items-center gap-3">
 <div className="p-2.5 rounded-lg bg-muted">
 <Icon className={`${iconSize.lg} text-muted-foreground`} />
 </div>
 <div>
 <h3 className={heading.section}>{client.label}</h3>
 <p className="text-sm text-muted-foreground mt-0.5">{client.description}</p>
 </div>
 </div>
 <div className="mt-8 text-center">
 <icons.Box className={`${iconSize.xl} text-muted-foreground mx-auto mb-3`} />
 <p className="text-sm font-medium text-foreground">未订阅</p>
 <p className="text-xs text-muted-foreground mt-1">当前端侧未开通套餐</p>
 </div>
 </div>
 <Button className="mt-6 w-full" onClick={() => window.location.href ='/pricing'}>
 查看套餐
 </Button>
 </div>
 )
 }

 const status = SUBSCRIPTION_STATUS_MAP[subscription.status] || {
 label: subscription.status,
 badge: statusBadge.neutral,
 }

 return (
 <div className={cardStyle.highlight}>
 <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-5">
 <div className="flex items-center gap-3">
 <div className="p-2.5 rounded-lg bg-primary/10">
 <Icon className={`${iconSize.lg} text-primary`} />
 </div>
 <div>
 <div className="flex flex-wrap items-center gap-2">
 <h3 className={heading.section}>{client.label}</h3>
 <Badge className={`text-xs px-2 py-0.5 ${status.badge}`}>{status.label}</Badge>
 </div>
 <p className="text-sm text-muted-foreground mt-0.5">{subscription.planName}</p>
 <p className="text-xs text-muted-foreground mt-1">
 到期时间：{subscription.expiresAt ||'未设置'}
 </p>
 </div>
 </div>
 <Button variant="outline" size="sm" className="gap-1.5 shrink-0">
 <icons.TrendingUp className={iconSize.sm} />
 升级套餐
 </Button>
 </div>

 <div className="flex items-center justify-between border-y border-border/60 py-3 mb-5">
 <span className="text-sm text-muted-foreground">自动续费</span>
 <Switch
 checked={subscription.autoRenew}
 onCheckedChange={value => onAutoRenewToggle(subscription.clientType, value)}
 />
 </div>

 <div className="space-y-4">
 <UsageBar
 label="AI 对话次数"
 used={subscription.aiUsed}
 total={subscription.aiTotal}
 unit="次"
 percent={aiPercent}
 />
 <UsageBar
 label="存储空间"
 used={subscription.storageUsedGB}
 total={subscription.storageTotalGB}
 unit="GB"
 percent={storagePercent}
 />
 </div>
 </div>
 )
}

function UsageBar({
 label,
 used,
 total,
 unit,
 percent,
}: {
 label: string
 used: number
 total: number
 unit: string
 percent: number
}) {
 const isHigh = percent >= 80
 return (
 <div className="space-y-2">
 <div className="flex items-center justify-between text-sm">
 <span className="text-muted-foreground">{label}</span>
 <span className={`font-medium ${isHigh ?'text-warning' :'text-foreground'}`}>
 {used} / {total} {unit}
 </span>
 </div>
 <Progress value={percent} className={`h-2 ${isHigh ?'[&>div]:bg-warning' :''}`} />
 {isHigh && (
 <p className="text-xs text-warning">用量接近上限，建议升级套餐</p>
 )}
 </div>
 )
}
