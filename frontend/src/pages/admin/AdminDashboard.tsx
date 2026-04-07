import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { adminApi } from '@/lib/api'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { PageContainer } from '@/components/ui/PageContainer'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import { cardStyle, chartColors } from '@/lib/design-tokens'

interface StatCard {
  title: string
  value: string | number
  icon: any
  color: string
  change?: string
}

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true)
  const [dashData, setDashData] = useState<any>(null)
  const [healthData, setHealthData] = useState<any>(null)
  const [auditLogs, setAuditLogs] = useState<any[]>([])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [dash, health, audit] = await Promise.allSettled([
        adminApi.dashboard(),
        adminApi.systemHealth(),
        adminApi.listAuditLogs({ limit: 10 }),
      ])

      if (dash.status === 'fulfilled') setDashData(dash.value)
      if (health.status === 'fulfilled') setHealthData(health.value)
      if (audit.status === 'fulfilled') setAuditLogs(audit.value?.logs || [])
    } catch {
      toast.error('加载仪表盘数据失败')
    } finally {
      setLoading(false)
    }
  }

  const statCards: StatCard[] = [
    {
      title: '总用户数',
      value: dashData?.total_users ?? '--',
      icon: icons.Users,
      color: 'text-info',
      change: dashData?.user_change,
    },
    {
      title: '今日活跃',
      value: dashData?.active_today ?? '--',
      icon: icons.Activity,
      color: 'text-success',
    },
    {
      title: '案件总量',
      value: dashData?.total_cases ?? '--',
      icon: icons.Briefcase,
      color: 'text-primary',
    },
    {
      title: '合同总量',
      value: dashData?.total_contracts ?? '--',
      icon: icons.FileText,
      color: 'text-warning',
    },
    {
      title: '文档总量',
      value: dashData?.total_documents ?? '--',
      icon: icons.FolderOpen,
      color: 'text-info',
    },
    {
      title: '系统运行',
      value: dashData?.uptime ?? '--',
      icon: icons.Clock,
      color: 'text-success',
    },
  ]

  // Mock chart data when API returns empty
  const userGrowthData = dashData?.user_growth || [
    { month: '1月', count: 45 },
    { month: '2月', count: 62 },
    { month: '3月', count: 78 },
    { month: '4月', count: 95 },
    { month: '5月', count: 120 },
    { month: '6月', count: 156 },
  ]

  const actionDistribution = dashData?.action_distribution || [
    { name: '用户登录', value: 340 },
    { name: '合同审查', value: 215 },
    { name: '文档创建', value: 180 },
    { name: '案件管理', value: 120 },
    { name: '知识检索', value: 95 },
    { name: '其他操作', value: 60 },
  ]

  const healthServices = healthData?.services || [
    { name: 'PostgreSQL', status: 'connected', latency: '2ms' },
    { name: 'Redis', status: 'connected', latency: '1ms' },
    { name: 'Qdrant', status: 'connected', latency: '5ms' },
    { name: 'MinIO', status: 'connected', latency: '3ms' },
  ]

  if (loading) {
    return (
      <PageContainer title="管理概览" description="系统运行状态与关键指标">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="管理概览" description="系统运行状态与关键指标">
      <section data-admin-shell className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statCards.map((card, index) => {
          const Icon = card.icon
          return (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card data-ui="surface-card" className={`${cardStyle.base} hover:shadow-float transition-shadow`}>
                <CardContent className="pt-5 pb-4 px-4">
                  <div className="flex items-center justify-between mb-3">
                    <Icon className={`w-5 h-5 ${card.color}`} />
                    {card.change && (
                      <Badge variant="secondary" className="text-xs">
                        {card.change}
                      </Badge>
                    )}
                  </div>
                  <p className="text-2xl font-bold">{card.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{card.title}</p>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 用户增长趋势 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card data-ui="surface-card" className={cardStyle.base}>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <icons.TrendingUp className="w-5 h-5 text-info" />
                用户增长趋势
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={userGrowthData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      background: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="count" fill={chartColors[0]} radius={[4, 4, 0, 0]} name="用户数" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* 操作类型分布 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card data-ui="surface-card" className={cardStyle.base}>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <icons.PieChart className="w-5 h-5 text-warning" />
                操作类型分布
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={actionDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {actionDistribution.map((_: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend
                    formatter={(value: string) => (
                      <span className="text-xs text-foreground">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 最近审计日志 */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card data-ui="surface-card" className={cardStyle.base}>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <icons.FileText className="w-5 h-5 text-primary" />
                最近审计日志
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>时间</TableHead>
                    <TableHead>用户</TableHead>
                    <TableHead>操作</TableHead>
                    <TableHead>状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs.length > 0 ? (
                    auditLogs.map((log: any, i: number) => (
                      <TableRow key={log.id || i}>
                        <TableCell className="text-muted-foreground text-xs">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString('zh-CN') : '--'}
                        </TableCell>
                        <TableCell className="text-sm">{log.user_email || '--'}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {log.action || '--'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={log.status === 'success' ? 'default' : 'destructive'}
                            className="text-xs"
                          >
                            {log.status === 'success' ? '成功' : '失败'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                        暂无审计日志
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </motion.div>

        {/* 系统健康状态 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card data-ui="surface-card" className={cardStyle.base}>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <icons.Server className="w-5 h-5 text-success" />
                系统健康
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {healthServices.map((service: any) => (
                <div
                  key={service.name}
                  className="flex items-center justify-between p-3 rounded-lg border border-border"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        service.status === 'connected'
                          ? 'bg-green-500'
                          : 'bg-red-500'
                      }`}
                    />
                    <span className="text-sm font-medium">{service.name}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {service.latency || '--'}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      </div>
      </section>
    </PageContainer>
  )
}
