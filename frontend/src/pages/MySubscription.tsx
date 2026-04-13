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
import { Skeleton } from'@/components/ui/skeleton'
import { Progress } from'@/components/ui/progress'
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

interface SubscriptionInfo {
 planName: string
 planId: string
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
 status:'paid' |'pending' |'refunded' |'refund_pending'
}

interface RefundRecord {
 id: string
 orderId: string
 amount: number
 reason: string
 status:'pending' |'approved' |'rejected'
 createdAt: string
}

const ORDER_STATUS_MAP: Record<string, { label: string; badge: string }> = {
 paid: { label:'已支付', badge: statusBadge.success },
 pending: { label:'待支付', badge: statusBadge.warning },
 refunded: { label:'已退款', badge: statusBadge.neutral },
 refund_pending: { label:'退款中', badge: statusBadge.info },
}

const REFUND_STATUS_MAP: Record<string, { label: string; badge: string }> = {
 pending: { label:'审批中', badge: statusBadge.warning },
 approved: { label:'已通过', badge: statusBadge.success },
 rejected: { label:'已拒绝', badge: statusBadge.error },
}

// ============ 主组件 ============

export default function MySubscription() {
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)
 const [sub, setSub] = useState<SubscriptionInfo | null>(null)
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

 // 订阅信息 - 适配不同返回结构
 if (subData) {
 const subscription = Array.isArray(subData) ? subData[0] : subData.subscription || subData
 if (subscription) {
 setSub({
 planName: subscription.plan_name || subscription.planName ||'未知套餐',
 planId: subscription.plan_id || subscription.planId ||'',
 expiresAt: subscription.expires_at || subscription.expiresAt ||'',
 autoRenew: subscription.auto_renew ?? subscription.autoRenew ?? false,
 aiUsed: subscription.ai_used ?? subscription.aiUsed ?? 0,
 aiTotal: subscription.ai_total ?? subscription.aiTotal ?? 0,
 storageUsedGB: subscription.storage_used_gb ?? subscription.storageUsedGB ?? 0,
 storageTotalGB: subscription.storage_total_gb ?? subscription.storageTotalGB ?? 0,
 })
 }

 // 订单可能嵌在订阅数据中
 const orderList = subscription?.orders || subData?.orders || []
 if (Array.isArray(orderList)) {
 setOrders(orderList)
 }
 }

 // 退款记录
 if (refundData) {
 const refundList = Array.isArray(refundData) ? refundData : refundData.refunds || []
 setRefunds(refundList.map((r: any) => ({
 id: r.id,
 orderId: r.order_id || r.orderId ||'',
 amount: r.amount || 0,
 reason: r.reason ||'',
 status: r.status ||'pending',
 createdAt: r.created_at || r.createdAt ||'',
 })))
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

 function handleAutoRenewToggle(val: boolean) {
 if (!sub) return
 setSub(prev => prev ? { ...prev, autoRenew: val } : prev)
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
 <Skeleton className="h-48 rounded-xl" />
 <Skeleton className="h-64 rounded-xl mt-4" />
 </PageContainer>
 )
 }

 if (error) {
 return (
 <PageContainer title="我的订阅">
 <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
 <icons.AlertCircle className={`${iconSize.xl} text-destructive mb-3`} />
 <p className={heading.section}>加载失败</p>
 <p className="text-sm text-muted-foreground mt-1">{error}</p>
 <Button className="mt-4" onClick={() => window.location.reload()}>重试</Button>
 </div>
 </PageContainer>
 )
 }

 if (!sub) {
 return (
 <PageContainer title="我的订阅" description="管理套餐、查看用量和订单记录">
 <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
 <icons.Box className={`${iconSize.xl} text-muted-foreground mb-3`} />
 <p className={heading.section}>暂无订阅</p>
 <p className="text-sm text-muted-foreground mt-1">您还没有订阅任何套餐</p>
 <Button className="mt-4" onClick={() => window.location.href ='/pricing'}>
 查看套餐
 </Button>
 </div>
 </PageContainer>
 )
 }

 const aiPercent = sub.aiTotal > 0 ? Math.round((sub.aiUsed / sub.aiTotal) * 100) : 0
 const storagePercent = sub.storageTotalGB > 0 ? Math.round((sub.storageUsedGB / sub.storageTotalGB) * 100) : 0

 return (
 <PageContainer title="我的订阅" description="管理套餐、查看用量和订单记录">
 {/* 当前套餐 */}
 <div className={cardStyle.highlight}>
 <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
 <div className="flex items-center gap-3">
 <div className="p-2.5 rounded-lg bg-primary/10">
 <icons.Zap className={`${iconSize.lg} text-primary`} />
 </div>
 <div>
 <div className="flex items-center gap-2">
 <h3 className={heading.section}>{sub.planName}</h3>
 <Badge className={statusBadge.info}>当前套餐</Badge>
 </div>
 <p className="text-sm text-muted-foreground mt-0.5">
 到期时间：{sub.expiresAt}
 </p>
 </div>
 </div>
 <div className="flex items-center gap-3">
 <div className="flex items-center gap-2">
 <span className="text-sm text-muted-foreground">自动续费</span>
 <Switch checked={sub.autoRenew} onCheckedChange={handleAutoRenewToggle} />
 </div>
 <Button variant="outline" size="sm" className="gap-1.5">
 <icons.TrendingUp className={iconSize.sm} />
 升级套餐
 </Button>
 </div>
 </div>

 {/* 用量进度 */}
 <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
 <UsageBar
 label="AI 对话次数"
 used={sub.aiUsed}
 total={sub.aiTotal}
 unit="次"
 percent={aiPercent}
 />
 <UsageBar
 label="存储空间"
 used={sub.storageUsedGB}
 total={sub.storageTotalGB}
 unit="GB"
 percent={storagePercent}
 />
 </div>
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
