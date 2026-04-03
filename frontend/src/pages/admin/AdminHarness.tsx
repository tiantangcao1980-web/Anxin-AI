import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

async function fetchHarness<T>(path: string): Promise<T> {
  const token = localStorage.getItem('access_token')
  const res = await fetch(`${API_BASE}/harness${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  const json = await res.json()
  if (json.status !== 'ok') throw new Error(json.message || 'Harness API error')
  return json.data
}

interface HarnessStats {
  cost?: { total_tokens: number; total_cost_usd: number; by_model: Record<string, number>; by_agent: Record<string, number> }
  tools?: { total_tools: number; requires_approval: string[]; total_calls: number }
  policy?: { total_checks: number; decisions: Record<string, number> }
  tasks?: { total_tasks: number; completed: number; failed: number; success_rate: number; avg_elapsed_seconds: number }
}

function StatCard({ title, value, subtitle, icon: Icon, color = 'text-blue-600' }: {
  title: string; value: string | number; subtitle?: string; icon?: any; color?: string
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          {Icon && <Icon className="h-8 w-8 text-muted-foreground/30" />}
        </div>
      </CardContent>
    </Card>
  )
}

export default function AdminHarness() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<HarnessStats | null>(null)
  const [policyLogs, setPolicyLogs] = useState<any[]>([])

  const loadData = async () => {
    try {
      setLoading(true)
      const [statsData, logsData] = await Promise.all([
        fetchHarness<HarnessStats>('/stats'),
        fetchHarness<any[]>('/policy/audit?limit=20'),
      ])
      setStats(statsData)
      setPolicyLogs(logsData)
    } catch (err: any) {
      toast.error(`Harness 数据加载失败: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  if (loading) {
    return (
      <PageContainer title="Harness 工程监控" description="AI 系统运行质量与治理">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </PageContainer>
    )
  }

  const cost = stats?.cost
  const tools = stats?.tools
  const policy = stats?.policy
  const tasks = stats?.tasks

  return (
    <PageContainer title="Harness 工程监控" description="AI 系统运行质量与治理">
      {/* 顶部概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Token 消耗"
          value={cost?.total_tokens?.toLocaleString() || '0'}
          subtitle={`$${cost?.total_cost_usd?.toFixed(4) || '0'} USD`}
          icon={icons.Zap}
          color="text-amber-600"
        />
        <StatCard
          title="任务总数"
          value={tasks?.total_tasks || 0}
          subtitle={`成功率 ${((tasks?.success_rate || 0) * 100).toFixed(1)}%`}
          icon={icons.CheckCircle}
          color="text-green-600"
        />
        <StatCard
          title="注册工具"
          value={tools?.total_tools || 0}
          subtitle={`${tools?.requires_approval?.length || 0} 个需审批`}
          icon={icons.Settings}
          color="text-blue-600"
        />
        <StatCard
          title="权限检查"
          value={policy?.total_checks || 0}
          subtitle={`拒绝 ${policy?.decisions?.DENY || 0} 次`}
          icon={icons.Shield}
          color="text-red-600"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 模型费用分布 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">模型费用分布</CardTitle>
          </CardHeader>
          <CardContent>
            {cost?.by_model && Object.keys(cost.by_model).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(cost.by_model)
                  .sort(([,a], [,b]) => b - a)
                  .map(([model, amount]) => (
                    <div key={model} className="flex items-center justify-between">
                      <span className="text-sm font-mono">{model}</span>
                      <Badge variant="secondary">${Number(amount).toFixed(4)}</Badge>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">暂无数据</p>
            )}
          </CardContent>
        </Card>

        {/* Agent 费用分布 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Agent 费用分布</CardTitle>
          </CardHeader>
          <CardContent>
            {cost?.by_agent && Object.keys(cost.by_agent).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(cost.by_agent)
                  .sort(([,a], [,b]) => b - a)
                  .map(([agent, amount]) => (
                    <div key={agent} className="flex items-center justify-between">
                      <span className="text-sm">{agent}</span>
                      <Badge variant="secondary">${Number(amount).toFixed(4)}</Badge>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">暂无数据</p>
            )}
          </CardContent>
        </Card>

        {/* 任务统计 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">任务执行统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{tasks?.completed || 0}</p>
                <p className="text-xs text-muted-foreground">已完成</p>
              </div>
              <div className="text-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <p className="text-2xl font-bold text-red-600">{tasks?.failed || 0}</p>
                <p className="text-xs text-muted-foreground">已失败</p>
              </div>
              <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">
                  {((tasks?.success_rate || 0) * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-muted-foreground">成功率</p>
              </div>
              <div className="text-center p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                <p className="text-2xl font-bold text-amber-600">
                  {tasks?.avg_elapsed_seconds?.toFixed(1) || '0'}s
                </p>
                <p className="text-xs text-muted-foreground">平均耗时</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 权限审计日志 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">权限审计日志（最近 20 条）</CardTitle>
          </CardHeader>
          <CardContent>
            {policyLogs.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {policyLogs.map((log, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm py-1 border-b last:border-0">
                    <Badge
                      variant={log.decision === 'ALLOW' ? 'default' : log.decision === 'DENY' ? 'destructive' : 'secondary'}
                      className="text-xs w-16 justify-center"
                    >
                      {log.decision}
                    </Badge>
                    <span className="font-mono text-xs truncate flex-1">
                      {log.agent} → {log.tool}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">暂无审计记录</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 刷新按钮 */}
      <div className="mt-6 flex justify-end">
        <Button variant="outline" onClick={loadData} disabled={loading}>
          刷新数据
        </Button>
      </div>
    </PageContainer>
  )
}
