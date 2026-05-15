import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { API_BASE_URL, buildApiHeaders } from '@/lib/api'
import { PageContainer } from '@/components/ui/PageContainer'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { shadowErrorRate, shadowVariant } from './adminGovernanceModel'

interface Revoked {
  skill_id: string
  version: string
  revoked_at: string
  reason: string
  revoked_by: string
  successor_version?: string
}

interface ShadowRun {
  id: string
  skill_id: string
  review_version: string
  baseline_version?: string
  status: string
  created_at: string
  ended_at?: string
  window_ends_at: string
  total_invocations: number
  review_errors: number
  baseline_errors: number
  divergences: number
  security_violations: number
  max_error_rate: number
}

export default function AdminGovernanceRevoked() {
  const [revoked, setRevoked] = useState<Revoked[]>([])
  const [shadows, setShadows] = useState<ShadowRun[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const headers = await buildApiHeaders()
      const [rR, sR] = await Promise.all([
        fetch(`${API_BASE_URL}/governance/revoked`, { headers }),
        fetch(`${API_BASE_URL}/governance/shadow-runs?limit=100`, { headers }),
      ])
      if (rR.ok) {
        const j = await rR.json()
        setRevoked(j.items || [])
      }
      if (sR.ok) {
        const j = await sR.json()
        setShadows(j.items || [])
      }
    } catch (e) {
      toast.error('加载失败')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  return (
    <PageContainer
      title="Skill 生命周期"
      description="撤回清单 + Shadow 24h 录制运行"
    >
      <Card className="mb-6">
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold">撤回的 Skill（全网拒绝调用）</h2>
              <p className="text-xs text-muted-foreground mt-1">
                来源：<code>.claude/builder-hub/revoked.json</code>
              </p>
            </div>
            <Badge variant="secondary">{revoked.length}</Badge>
          </div>
          {loading ? (
            <Skeleton className="h-32" />
          ) : revoked.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">尚无撤回记录</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Skill</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>撤回时间</TableHead>
                  <TableHead>原因</TableHead>
                  <TableHead>撤回人</TableHead>
                  <TableHead>替代版本</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {revoked.map((r, i) => (
                  <TableRow key={`${r.skill_id}-${r.version}-${i}`}>
                    <TableCell className="text-xs"><code>{r.skill_id}</code></TableCell>
                    <TableCell className="text-xs">{r.version}</TableCell>
                    <TableCell className="text-xs">{new Date(r.revoked_at).toLocaleString()}</TableCell>
                    <TableCell className="text-xs max-w-md truncate" title={r.reason}>{r.reason}</TableCell>
                    <TableCell className="text-xs">{r.revoked_by}</TableCell>
                    <TableCell className="text-xs">{r.successor_version || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold">Shadow 录制窗口</h2>
              <p className="text-xs text-muted-foreground mt-1">
                REVIEW → PUBLISHED 前的 24h 双跑录制；通过即解锁状态迁移
              </p>
            </div>
            <Badge variant="secondary">{shadows.length}</Badge>
          </div>
          {loading ? (
            <Skeleton className="h-32" />
          ) : shadows.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">尚无 shadow 运行</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Skill</TableHead>
                  <TableHead>REVIEW 版</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>调用</TableHead>
                  <TableHead>错误率</TableHead>
                  <TableHead>分歧</TableHead>
                  <TableHead>安全违规</TableHead>
                  <TableHead>窗口结束</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shadows.map(s => {
                  const { rate: errRate, overThreshold } = shadowErrorRate(s)
                  return (
                    <TableRow key={s.id}>
                      <TableCell className="text-xs"><code>{s.skill_id}</code></TableCell>
                      <TableCell className="text-xs">{s.review_version}</TableCell>
                      <TableCell><Badge variant={shadowVariant(s.status)} className="text-xs">{s.status}</Badge></TableCell>
                      <TableCell className="text-xs tabular-nums">{s.total_invocations}</TableCell>
                      <TableCell className="text-xs tabular-nums">
                        <span className={overThreshold ? 'text-destructive' : ''}>
                          {(errRate * 100).toFixed(1)}%
                        </span>
                        <span className="text-muted-foreground"> / {(s.max_error_rate * 100).toFixed(0)}%</span>
                      </TableCell>
                      <TableCell className="text-xs tabular-nums">{s.divergences}</TableCell>
                      <TableCell className="text-xs tabular-nums">
                        <span className={s.security_violations ? 'text-destructive font-semibold' : ''}>
                          {s.security_violations}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs">
                        {new Date(s.window_ends_at).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  )
}
