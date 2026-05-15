import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { API_BASE_URL, buildApiHeaders } from '@/lib/api'
import { useGovernanceWS } from '@/hooks/useGovernanceWS'
import { PageContainer } from '@/components/ui/PageContainer'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { icons } from '@/lib/icons'
import { Link } from 'react-router-dom'

interface PolicyCurrent {
  snapshot_id: string
  loaded_at: string
  files: string[]
  summary: {
    roles: string[]
    data_levels: string[]
    trust_levels: string[]
    skill_states: string[]
  }
}

interface AuditStats {
  window_days: number
  by_decision: Record<string, number>
  by_event_type: Record<string, number>
}

export default function AdminGovernance() {
  const [policy, setPolicy] = useState<PolicyCurrent | null>(null)
  const [stats, setStats] = useState<AuditStats | null>(null)
  const [pendingTickets, setPendingTickets] = useState<number>(0)
  const [revokedCount, setRevokedCount] = useState<number>(0)
  const [shadowRunning, setShadowRunning] = useState<number>(0)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const headers = await buildApiHeaders()
      const [polR, statsR, ticketsR, revokedR, shadowR] = await Promise.all([
        fetch(`${API_BASE_URL}/governance/policy/current`, { headers }),
        fetch(`${API_BASE_URL}/governance/audit/stats?days=7`, { headers }),
        fetch(`${API_BASE_URL}/governance/confirm-tickets?status=pending&limit=1`, { headers }),
        fetch(`${API_BASE_URL}/governance/revoked`, { headers }),
        fetch(`${API_BASE_URL}/governance/shadow-runs?status=running&limit=1`, { headers }),
      ])
      if (polR.ok) setPolicy(await polR.json())
      if (statsR.ok) setStats(await statsR.json())
      if (ticketsR.ok) {
        const j = await ticketsR.json()
        setPendingTickets(j.count ?? (j.items?.length ?? 0))
      }
      if (revokedR.ok) {
        const j = await revokedR.json()
        setRevokedCount((j.items ?? []).length)
      }
      if (shadowR.ok) {
        const j = await shadowR.json()
        setShadowRunning((j.items ?? []).length)
      }
    } catch (e) {
      toast.error('加载治理总览失败')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  // 实时推送：ticket / cookbook / lifecycle 变化都刷新总览
  useGovernanceWS((ev) => {
    if (
      ev.type.startsWith('ticket.') ||
      ev.type.startsWith('cookbook.') ||
      ev.type.startsWith('lifecycle.') ||
      ev.type.startsWith('shadow.')
    ) {
      void load()
    }
  })

  const reloadPolicy = async () => {
    try {
      const headers = await buildApiHeaders()
      const r = await fetch(`${API_BASE_URL}/governance/policy/reload`, {
        method: 'POST',
        headers,
      })
      if (!r.ok) {
        toast.error('热重载失败：' + (await r.text()))
        return
      }
      const j = await r.json()
      toast.success(`Policy 已重载：${j.snapshot_id}`)
      await load()
    } catch (e) {
      toast.error('热重载请求失败')
      console.error(e)
    }
  }

  return (
    <PageContainer title="治理总览" description="Policy 快照 / 审计统计 / 待 confirm / Shadow / 撤回">
      {/* Top stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={<icons.Shield className="w-5 h-5 text-primary" />}
          title="当前 Policy"
          value={policy?.snapshot_id ?? '—'}
          subtitle={policy?.loaded_at ? new Date(policy.loaded_at).toLocaleString() : ''}
          loading={loading}
        />
        <StatCard
          icon={<icons.Bell className="w-5 h-5 text-warning" />}
          title="待 Confirm"
          value={String(pendingTickets)}
          subtitle="人工审批中"
          loading={loading}
          link="/admin/governance/tickets"
        />
        <StatCard
          icon={<icons.Eye className="w-5 h-5 text-info" />}
          title="Shadow 中"
          value={String(shadowRunning)}
          subtitle="REVIEW→PUBLISHED 录制窗口"
          loading={loading}
        />
        <StatCard
          icon={<icons.AlertCircle className="w-5 h-5 text-destructive" />}
          title="已撤回 Skill"
          value={String(revokedCount)}
          subtitle="全网拒绝调用"
          loading={loading}
        />
      </div>

      {/* Policy meta */}
      <Card className="mb-6">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Policy Bundle</h2>
              <p className="text-sm text-muted-foreground mt-1">
                7 份 yaml + 单一真相源；变更通过 PR 合并后产生新快照。
              </p>
            </div>
            <div className="flex gap-2">
              <Link to="/admin/governance/policy">
                <Button variant="outline" size="sm">查看快照历史</Button>
              </Link>
              <Button size="sm" onClick={reloadPolicy}>热重载</Button>
            </div>
          </div>
          {loading ? (
            <Skeleton className="h-24" />
          ) : policy ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetaBox title="角色" items={policy.summary.roles} />
              <MetaBox title="数据分级" items={policy.summary.data_levels} />
              <MetaBox title="信任层级" items={policy.summary.trust_levels} />
              <MetaBox title="Skill 状态" items={policy.summary.skill_states} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">未加载</p>
          )}
        </CardContent>
      </Card>

      {/* Audit stats */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">最近 7 天审计概览</h2>
              <p className="text-sm text-muted-foreground mt-1">
                按决策 / 事件类型聚合；详细审计 →&nbsp;
                <Link to="/admin/governance/audit" className="text-primary hover:underline">审计时间线</Link>
              </p>
            </div>
          </div>
          {loading ? (
            <Skeleton className="h-32" />
          ) : stats ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Histogram title="按决策" data={stats.by_decision} />
              <Histogram title="按事件类型" data={stats.by_event_type} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">未加载</p>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  )
}

function StatCard({
  icon, title, value, subtitle, loading, link,
}: {
  icon: React.ReactNode
  title: string
  value: string
  subtitle?: string
  loading: boolean
  link?: string
}) {
  const Body = (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-muted-foreground mb-1">{title}</p>
            {loading
              ? <Skeleton className="h-7 w-24" />
              : <p className="text-xl font-semibold truncate max-w-[180px]" title={value}>{value}</p>}
            {subtitle ? <p className="text-xs text-muted-foreground mt-1">{subtitle}</p> : null}
          </div>
          <div className="rounded-md bg-surface-2 p-2">{icon}</div>
        </div>
      </CardContent>
    </Card>
  )
  if (link) return <Link to={link}>{Body}</Link>
  return Body
}

function MetaBox({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-2">{title}</p>
      <div className="flex flex-wrap gap-1">
        {(items ?? []).map(s => <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>)}
      </div>
    </div>
  )
}

function Histogram({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data ?? {}).sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...entries.map(e => e[1]))
  return (
    <div>
      <p className="text-sm font-medium mb-2">{title}</p>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">无数据（DB 未就绪 / 无事件）</p>
      ) : (
        <div className="space-y-2">
          {entries.map(([k, v]) => (
            <div key={k} className="flex items-center gap-2">
              <span className="text-xs w-32 truncate" title={k}>{k}</span>
              <div className="flex-1 h-2 bg-surface-2 rounded overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${(v / max) * 100}%` }} />
              </div>
              <span className="text-xs w-10 text-right tabular-nums">{v}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
