/**
 * MySubscription - 我的订阅页面
 *
 * 当前套餐信息 + 用量进度条 + 订单历史 + 退款申请
 * 使用 PageContainer + design-tokens
 */

import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, heading, statusBadge, iconSize } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

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
  status: 'paid' | 'pending' | 'refunded' | 'refund_pending'
}

interface RefundRecord {
  id: string
  orderId: string
  amount: number
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  createdAt: string
}

// ============ Mock 数据 ============

// @mock-data FALLBACK: 后端就绪后从 API 获取
const MOCK_SUB: SubscriptionInfo = {
  planName: '专业版',
  planId: 'pro',
  expiresAt: '2026-04-28',
  autoRenew: true,
  aiUsed: 142,
  aiTotal: 200,
  storageUsedGB: 8.5,
  storageTotalGB: 20,
}

// @mock-data FALLBACK: 后端就绪后从 API 获取
const MOCK_ORDERS: OrderRecord[] = [
  { id: 'ORD-20260328001', date: '2026-03-28', description: '专业版月度订阅', amount: 299, status: 'paid' },
  { id: 'ORD-20260228001', date: '2026-02-28', description: '专业版月度订阅', amount: 299, status: 'paid' },
  { id: 'ORD-20260128001', date: '2026-01-28', description: '专业版月度订阅', amount: 299, status: 'paid' },
  { id: 'ORD-20251228001', date: '2025-12-28', description: '基础版月度订阅', amount: 99, status: 'paid' },
  { id: 'ORD-20251128001', date: '2025-11-28', description: '基础版月度订阅', amount: 99, status: 'refunded' },
]

// @mock-data FALLBACK: 后端就绪后从 API 获取
const MOCK_REFUNDS: RefundRecord[] = [
  {
    id: 'REF-001',
    orderId: 'ORD-20251128001',
    amount: 99,
    reason: '升级到专业版，基础版未用完',
    status: 'approved',
    createdAt: '2025-12-01',
  },
]

const ORDER_STATUS_MAP: Record<string, { label: string; badge: string }> = {
  paid: { label: '已支付', badge: statusBadge.success },
  pending: { label: '待支付', badge: statusBadge.warning },
  refunded: { label: '已退款', badge: statusBadge.neutral },
  refund_pending: { label: '退款中', badge: statusBadge.info },
}

const REFUND_STATUS_MAP: Record<string, { label: string; badge: string }> = {
  pending: { label: '审批中', badge: statusBadge.warning },
  approved: { label: '已通过', badge: statusBadge.success },
  rejected: { label: '已拒绝', badge: statusBadge.error },
}

// ============ 主组件 ============

export default function MySubscription() {
  const [loading, setLoading] = useState(true)
  const [sub, setSub] = useState<SubscriptionInfo>(MOCK_SUB)
  const [orders, setOrders] = useState<OrderRecord[]>([])
  const [refunds, setRefunds] = useState<RefundRecord[]>([])

  useEffect(() => {
    // @mock-data FALLBACK: 后端就绪后从 API 获取
    const timer = setTimeout(() => {
      setSub(MOCK_SUB)
      setOrders(MOCK_ORDERS)
      setRefunds(MOCK_REFUNDS)
      setLoading(false)
    }, 600)
    return () => clearTimeout(timer)
  }, [])

  function handleAutoRenewToggle(val: boolean) {
    setSub(prev => ({ ...prev, autoRenew: val }))
    toast.success(val ? '已开启自动续费' : '已关闭自动续费')
  }

  function handleRefundRequest(orderId: string) {
    // @mock-data FALLBACK: 后端就绪后调用 API
    const order = orders.find(o => o.id === orderId)
    if (!order) return
    setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'refund_pending' as const } : o))
    setRefunds(prev => [
      ...prev,
      {
        id: `REF-${Date.now()}`,
        orderId,
        amount: order.amount,
        reason: '用户申请退款',
        status: 'pending' as const,
        createdAt: new Date().toISOString().slice(0, 10),
      },
    ])
    toast.success('退款申请已提交')
  }

  if (loading) {
    return (
      <PageContainer title="我的订阅">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-64 rounded-xl mt-4" />
      </PageContainer>
    )
  }

  const aiPercent = Math.round((sub.aiUsed / sub.aiTotal) * 100)
  const storagePercent = Math.round((sub.storageUsedGB / sub.storageTotalGB) * 100)

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
                      <Badge className={`text-xs px-2 py-0.5 ${ORDER_STATUS_MAP[order.status].badge}`}>
                        {ORDER_STATUS_MAP[order.status].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {order.status === 'paid' && (
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
                      <Badge className={`text-xs px-2 py-0.5 ${REFUND_STATUS_MAP[r.status].badge}`}>
                        {REFUND_STATUS_MAP[r.status].label}
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
        <span className={`font-medium ${isHigh ? 'text-amber-600' : 'text-foreground'}`}>
          {used} / {total} {unit}
        </span>
      </div>
      <Progress value={percent} className={`h-2 ${isHigh ? '[&>div]:bg-amber-500' : ''}`} />
      {isHigh && (
        <p className="text-xs text-amber-600">用量接近上限，建议升级套餐</p>
      )}
    </div>
  )
}
