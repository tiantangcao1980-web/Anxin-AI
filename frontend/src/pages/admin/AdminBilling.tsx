/**
 * AdminBilling - 计费管理后台
 *
 * 3 个 Tab：套餐管理 / 订阅统计 / 退款审批
 * 使用 PageContainer + design-tokens + recharts + ConfirmDialog
 */

import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, complianceScoreColors, heading, statusBadge, iconSize, chartColors } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { billingApi } from '@/lib/api'
import { ErrorState } from '@/components/common'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

// ============ 类型定义 ============

interface PlanConfig {
  id: string
  name: string
  code: string
  billingMode: 'monthly' | 'yearly' | 'both'
  monthlyPrice: number
  yearlyPrice: number
  enabled: boolean
}

interface SubscriptionStats {
  activeCount: number
  mrr: number
  churnRate: number
  avgRevenue: number
}

interface GrowthPoint {
  month: string
  subscriptions: number
  revenue: number
}

interface RefundRequest {
  id: string
  userId: string
  userName: string
  orderId: string
  amount: number
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  createdAt: string
}

const BILLING_MODE_MAP: Record<string, string> = {
  monthly: '仅月付',
  yearly: '仅年付',
  both: '月付 + 年付',
}

const REFUND_STATUS_MAP: Record<string, { label: string; badge: string }> = {
  pending: { label: '待审批', badge: statusBadge.warning },
  approved: { label: '已通过', badge: statusBadge.success },
  rejected: { label: '已拒绝', badge: statusBadge.error },
}

// ============ 主组件 ============

export default function AdminBilling() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [plans, setPlans] = useState<PlanConfig[]>([])
  const [stats, setStats] = useState<SubscriptionStats>({ activeCount: 0, mrr: 0, churnRate: 0, avgRevenue: 0 })
  const [growth, setGrowth] = useState<GrowthPoint[]>([])
  const [refunds, setRefunds] = useState<RefundRequest[]>([])

  // Dialog 状态
  const [editDialog, setEditDialog] = useState<{ open: boolean; plan: PlanConfig | null }>({ open: false, plan: null })
  const [approveDialog, setApproveDialog] = useState<{ open: boolean; id: string }>({ open: false, id: '' })
  const [rejectDialog, setRejectDialog] = useState<{ open: boolean; id: string }>({ open: false, id: '' })

  useEffect(() => {
    let cancelled = false
    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const [plansData, reportData, refundsData] = await Promise.all([
          billingApi.listPlans(),
          billingApi.getSubscriptionReport(),
          billingApi.listRefunds({ status: 'pending' }),
        ])
        if (cancelled) return

        // 套餐列表
        const planList = Array.isArray(plansData) ? plansData : plansData?.plans || []
        setPlans(planList.map((p: any) => ({
          id: p.id || '',
          name: p.name || '',
          code: p.code || '',
          billingMode: p.billing_mode || p.billingMode || 'both',
          monthlyPrice: p.monthly_price ?? p.monthlyPrice ?? 0,
          yearlyPrice: p.yearly_price ?? p.yearlyPrice ?? 0,
          enabled: p.enabled ?? true,
        })))

        // 订阅报表
        if (reportData) {
          setStats({
            activeCount: reportData.active_count ?? reportData.activeCount ?? 0,
            mrr: reportData.mrr ?? 0,
            churnRate: reportData.churn_rate ?? reportData.churnRate ?? 0,
            avgRevenue: reportData.avg_revenue ?? reportData.avgRevenue ?? 0,
          })
          const growthData = reportData.growth || reportData.trend || []
          if (Array.isArray(growthData)) {
            setGrowth(growthData)
          }
        }

        // 退款列表
        const refundList = Array.isArray(refundsData) ? refundsData : refundsData?.refunds || []
        setRefunds(refundList.map((r: any) => ({
          id: r.id || '',
          userId: r.user_id || r.userId || '',
          userName: r.user_name || r.userName || '',
          orderId: r.order_id || r.orderId || '',
          amount: r.amount || 0,
          reason: r.reason || '',
          status: r.status || 'pending',
          createdAt: r.created_at || r.createdAt || '',
        })))
      } catch (err: any) {
        if (!cancelled) {
          console.error('计费数据加载失败:', err)
          setError(err?.message || '数据加载失败，请稍后重试')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchData()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <PageContainer title="计费管理">
        <Skeleton className="h-10 w-80 mb-4" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </PageContainer>
    )
  }

  if (error) {
    return (
      <PageContainer title="计费管理">
        <ErrorState title="加载失败" message={error} onRetry={() => window.location.reload()} />
      </PageContainer>
    )
  }

  return (
    <PageContainer title="计费管理" description="套餐配置、订阅统计与退款审批">
      <Tabs defaultValue="plans" className="space-y-4">
        <TabsList className="w-full sm:w-auto overflow-x-auto scrollbar-hide">
          <TabsTrigger value="plans" className="flex items-center gap-1.5 text-xs sm:text-sm">
            <icons.Layers className={`${iconSize.sm} shrink-0`} />
            <span className="whitespace-nowrap">套餐管理</span>
          </TabsTrigger>
          <TabsTrigger value="stats" className="flex items-center gap-1.5 text-xs sm:text-sm">
            <icons.BarChart3 className={`${iconSize.sm} shrink-0`} />
            <span className="whitespace-nowrap">订阅统计</span>
          </TabsTrigger>
          <TabsTrigger value="refunds" className="flex items-center gap-1.5 text-xs sm:text-sm">
            <icons.RotateCcw className={`${iconSize.sm} shrink-0`} />
            <span className="whitespace-nowrap">退款审批</span>
            {refunds.filter(r => r.status === 'pending').length > 0 && (
              <Badge variant="destructive" className="text-[10px] px-1.5 py-0 h-4 ml-1">
                {refunds.filter(r => r.status === 'pending').length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: 套餐管理 */}
        <TabsContent value="plans" className="space-y-4">
          <PlansTab
            plans={plans}
            setPlans={setPlans}
            editDialog={editDialog}
            setEditDialog={setEditDialog}
          />
        </TabsContent>

        {/* Tab 2: 订阅统计 */}
        <TabsContent value="stats" className="space-y-4">
          <StatsTab stats={stats} growth={growth} />
        </TabsContent>

        {/* Tab 3: 退款审批 */}
        <TabsContent value="refunds" className="space-y-4">
          <RefundsTab
            refunds={refunds}
            setRefunds={setRefunds}
            approveDialog={approveDialog}
            setApproveDialog={setApproveDialog}
            rejectDialog={rejectDialog}
            setRejectDialog={setRejectDialog}
          />
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}

// ============ Tab 1: 套餐管理 ============

function PlansTab({
  plans,
  setPlans,
  editDialog,
  setEditDialog,
}: {
  plans: PlanConfig[]
  setPlans: React.Dispatch<React.SetStateAction<PlanConfig[]>>
  editDialog: { open: boolean; plan: PlanConfig | null }
  setEditDialog: React.Dispatch<React.SetStateAction<{ open: boolean; plan: PlanConfig | null }>>
}) {
  const [form, setForm] = useState<PlanConfig>({
    id: '',
    name: '',
    code: '',
    billingMode: 'both',
    monthlyPrice: 0,
    yearlyPrice: 0,
    enabled: true,
  })

  function openCreate() {
    setForm({ id: '', name: '', code: '', billingMode: 'both', monthlyPrice: 0, yearlyPrice: 0, enabled: true })
    setEditDialog({ open: true, plan: null })
  }

  function openEdit(plan: PlanConfig) {
    setForm({ ...plan })
    setEditDialog({ open: true, plan })
  }

  function handleSave() {
    if (!form.name || !form.code) {
      toast.error('请填写名称和代码')
      return
    }
    if (editDialog.plan) {
      // 编辑
      setPlans(prev => prev.map(p => (p.id === form.id ? form : p)))
      toast.success('套餐已更新')
    } else {
      // 新建
      setPlans(prev => [...prev, { ...form, id: `${Date.now()}` }])
      toast.success('套餐已创建')
    }
    setEditDialog({ open: false, plan: null })
  }

  function handleToggle(id: string, enabled: boolean) {
    setPlans(prev => prev.map(p => (p.id === id ? { ...p, enabled } : p)))
    toast.success(enabled ? '套餐已启用' : '套餐已停用')
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <h3 className={heading.section}>套餐列表</h3>
        <Button size="sm" onClick={openCreate} className="gap-1.5">
          <icons.Plus className={iconSize.sm} />
          新建套餐
        </Button>
      </div>

      <div className={`${cardStyle.base} overflow-hidden`}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead>代码</TableHead>
              <TableHead className="hidden sm:table-cell">计费模式</TableHead>
              <TableHead>月价</TableHead>
              <TableHead className="hidden md:table-cell">年价</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {plans.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <p className={heading.muted}>暂无套餐数据</p>
                </TableCell>
              </TableRow>
            ) : (
              plans.map(plan => (
                <TableRow key={plan.id}>
                  <TableCell className="text-sm font-medium">{plan.name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground font-mono">{plan.code}</TableCell>
                  <TableCell className="hidden sm:table-cell text-sm">{BILLING_MODE_MAP[plan.billingMode] || plan.billingMode}</TableCell>
                  <TableCell className="text-sm">¥{plan.monthlyPrice}</TableCell>
                  <TableCell className="hidden md:table-cell text-sm">¥{plan.yearlyPrice}</TableCell>
                  <TableCell>
                    <Switch
                      checked={plan.enabled}
                      onCheckedChange={v => handleToggle(plan.id, v)}
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" className="h-7 text-xs gap-1" onClick={() => openEdit(plan)}>
                      <icons.Edit className={iconSize.xs} />
                      编辑
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 创建/编辑 Dialog */}
      <Dialog open={editDialog.open} onOpenChange={open => setEditDialog({ ...editDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editDialog.plan ? '编辑套餐' : '新建套餐'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-sm font-medium">套餐名称</Label>
                <Input
                  value={form.name}
                  onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                  placeholder="例如：专业版"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-sm font-medium">套餐代码</Label>
                <Input
                  value={form.code}
                  onChange={e => setForm(p => ({ ...p, code: e.target.value }))}
                  placeholder="例如：pro"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-sm font-medium">计费模式</Label>
              <Select
                value={form.billingMode}
                onValueChange={v => setForm(p => ({ ...p, billingMode: v as PlanConfig['billingMode'] }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">仅月付</SelectItem>
                  <SelectItem value="yearly">仅年付</SelectItem>
                  <SelectItem value="both">月付 + 年付</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-sm font-medium">月价 (¥)</Label>
                <Input
                  type="number"
                  min={0}
                  value={form.monthlyPrice}
                  onChange={e => setForm(p => ({ ...p, monthlyPrice: Number(e.target.value) }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-sm font-medium">年价 (¥)</Label>
                <Input
                  type="number"
                  min={0}
                  value={form.yearlyPrice}
                  onChange={e => setForm(p => ({ ...p, yearlyPrice: Number(e.target.value) }))}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialog({ open: false, plan: null })}>取消</Button>
            <Button onClick={handleSave}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ============ Tab 2: 订阅统计 ============

function StatsTab({
  stats,
  growth,
}: {
  stats: SubscriptionStats
  growth: GrowthPoint[]
}) {
  return (
    <>
      {/* KPI 卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={icons.Users}
          label="活跃订阅数"
          value={stats.activeCount.toLocaleString()}
          color="text-primary"
          bgColor="bg-primary/5"
        />
        <StatCard
          icon={icons.DollarSign}
          label="月经常性收入(MRR)"
          value={`¥${stats.mrr.toLocaleString()}`}
          color="text-success"
          bgColor="bg-success/10 dark:bg-success/20"
        />
        <StatCard
          icon={icons.TrendingDown}
          label="流失率"
          value={`${stats.churnRate}%`}
          color="text-warning"
          bgColor="bg-warning/10 dark:bg-warning/20"
        />
        <StatCard
          icon={icons.Calculator}
          label="平均客单价"
          value={`¥${stats.avgRevenue}`}
          color="text-info"
          bgColor="bg-info/10 dark:bg-info/20"
        />
      </div>

      {/* 增长趋势 */}
      <div className={cardStyle.base}>
        <h4 className={`${heading.card} mb-4`}>订阅增长趋势</h4>
        {growth.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={growth}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis yAxisId="left" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="subscriptions"
                name="订阅数"
                stroke={chartColors[0]}
                strokeWidth={2}
                dot={{ r: 3, fill: chartColors[0] }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="revenue"
                name="收入(¥)"
                stroke={chartColors[1]}
                strokeWidth={2}
                dot={{ r: 3, fill: chartColors[1] }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">暂无趋势数据</div>
        )}
      </div>
    </>
  )
}

// ============ Tab 3: 退款审批 ============

function RefundsTab({
  refunds,
  setRefunds,
  approveDialog,
  setApproveDialog,
  rejectDialog,
  setRejectDialog,
}: {
  refunds: RefundRequest[]
  setRefunds: React.Dispatch<React.SetStateAction<RefundRequest[]>>
  approveDialog: { open: boolean; id: string }
  setApproveDialog: React.Dispatch<React.SetStateAction<{ open: boolean; id: string }>>
  rejectDialog: { open: boolean; id: string }
  setRejectDialog: React.Dispatch<React.SetStateAction<{ open: boolean; id: string }>>
}) {
  async function handleApprove() {
    try {
      await billingApi.adminApproveRefund(approveDialog.id)
      setRefunds(prev => prev.map(r => (r.id === approveDialog.id ? { ...r, status: 'approved' as const } : r)))
      setApproveDialog({ open: false, id: '' })
      toast.success('退款已通过')
    } catch (err: any) {
      toast.error(err?.message || '操作失败，请稍后重试')
    }
  }

  async function handleReject() {
    try {
      await billingApi.adminRejectRefund(rejectDialog.id, '管理员拒绝')
      setRefunds(prev => prev.map(r => (r.id === rejectDialog.id ? { ...r, status: 'rejected' as const } : r)))
      setRejectDialog({ open: false, id: '' })
      toast.success('退款已拒绝')
    } catch (err: any) {
      toast.error(err?.message || '操作失败，请稍后重试')
    }
  }

  return (
    <>
      <div className={`${cardStyle.base} overflow-hidden`}>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>用户</TableHead>
              <TableHead className="hidden sm:table-cell">订单号</TableHead>
              <TableHead>金额</TableHead>
              <TableHead className="hidden md:table-cell">原因</TableHead>
              <TableHead className="hidden sm:table-cell">申请时间</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {refunds.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <p className={heading.muted}>暂无退款申请</p>
                </TableCell>
              </TableRow>
            ) : (
              refunds.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="text-sm font-medium">{r.userName}</TableCell>
                  <TableCell className="hidden sm:table-cell text-sm text-muted-foreground font-mono">{r.orderId}</TableCell>
                  <TableCell className="text-sm font-medium">¥{r.amount}</TableCell>
                  <TableCell className="hidden md:table-cell text-sm text-muted-foreground max-w-48 truncate">{r.reason}</TableCell>
                  <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">{r.createdAt}</TableCell>
                  <TableCell>
                    <Badge className={`text-xs px-2 py-0.5 ${REFUND_STATUS_MAP[r.status]?.badge || statusBadge.neutral}`}>
                      {REFUND_STATUS_MAP[r.status]?.label || r.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {r.status === 'pending' && (
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="sm"
                          className="h-7 text-xs gap-1"
                          onClick={() => setApproveDialog({ open: true, id: r.id })}
                        >
                          <icons.Check className={iconSize.xs} />
                          通过
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          className="h-7 text-xs gap-1"
                          onClick={() => setRejectDialog({ open: true, id: r.id })}
                        >
                          <icons.X className={iconSize.xs} />
                          拒绝
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 通过确认 */}
      <ConfirmDialog
        open={approveDialog.open}
        onOpenChange={open => setApproveDialog({ ...approveDialog, open })}
        title="确认通过退款"
        description={`确认通过 ${refunds.find(r => r.id === approveDialog.id)?.userName || ''} 的退款申请（¥${refunds.find(r => r.id === approveDialog.id)?.amount || 0}）？`}
        confirmText="通过"
        onConfirm={handleApprove}
      />

      {/* 拒绝确认 */}
      <ConfirmDialog
        open={rejectDialog.open}
        onOpenChange={open => setRejectDialog({ ...rejectDialog, open })}
        title="确认拒绝退款"
        description={`确认拒绝 ${refunds.find(r => r.id === rejectDialog.id)?.userName || ''} 的退款申请？`}
        confirmText="拒绝"
        onConfirm={handleReject}
        destructive
      />
    </>
  )
}

// ============ 辅助组件 ============

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  bgColor,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  color: string
  bgColor: string
}) {
  return (
    <div className={cardStyle.base}>
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${bgColor}`}>
          <Icon className={`${iconSize.md} ${color}`} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-bold text-foreground">{value}</p>
        </div>
      </div>
    </div>
  )
}
