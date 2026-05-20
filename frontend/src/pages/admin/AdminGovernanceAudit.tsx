import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { API_BASE_URL, buildApiHeaders } from '@/lib/api'
import { useGovernanceWS } from '@/hooks/useGovernanceWS'
import { decisionVariant, shouldShowEvent } from './adminGovernanceModel'
import { PageContainer } from '@/components/ui/PageContainer'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'

interface AuditEvent {
  event_id: string
  ts: string
  event_type: string
  actor: { id?: string; role?: string; tenant_id?: string }
  action?: string
  decision?: string
  outcome?: string
  duration_ms?: number
  trace_id?: string
  policy_snapshot_id?: string
  fingerprint?: string
}

const DECISIONS = ['', 'ALLOW', 'DENY', 'REQUIRE_STEP_UP', 'REQUIRE_CONFIRM']
const EVENT_TYPES = [
  '', 'authz.decide', 'skill.execute', 'data.access',
  'policy.change', 'lifecycle.change', 'external.send',
  'confirm.created', 'confirm.granted', 'confirm.denied',
  'shadow.started', 'shadow.finalized',
]


export default function AdminGovernanceAudit() {
  const [actorId, setActorId] = useState('')
  const [action, setAction] = useState('')
  const [decision, setDecision] = useState('')
  const [eventType, setEventType] = useState('')
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [source, setSource] = useState<'db' | 'jsonl' | 'empty' | null>(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<AuditEvent | null>(null)
  const [livePaused, setLivePaused] = useState(false)
  const [liveBuffer, setLiveBuffer] = useState(0)
  // 用 ref 持有最新 filter 值，避免 WS 回调闭包陈旧
  const filterRef = useRef({ actorId, action, decision, eventType })
  filterRef.current = { actorId, action, decision, eventType }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const headers = await buildApiHeaders()
      const params = new URLSearchParams()
      if (actorId) params.set('actor_id', actorId)
      if (action) params.set('action', action)
      if (decision) params.set('decision', decision)
      if (eventType) params.set('event_type', eventType)
      params.set('limit', '200')
      const r = await fetch(`${API_BASE_URL}/governance/audit?${params}`, { headers })
      if (!r.ok) {
        toast.error('审计查询失败')
        return
      }
      const j = await r.json()
      setEvents(j.events || [])
      setSource(j.source)
    } catch (e) {
      toast.error('请求异常')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [actorId, action, decision, eventType])

  useEffect(() => { void load() }, [load])

  // 实时事件流：把新事件追加到列表顶端；暂停态只计数
  useGovernanceWS((ev) => {
    const p = ev.payload as Record<string, unknown>
    // 把 WS payload 映射成 AuditEvent 形态（与 REST 返回一致）
    const e: AuditEvent = {
      event_id: String(p.event_id ?? `live_${Date.now()}`),
      ts: String(p.ts ?? ev.ts),
      event_type: ev.type,
      actor: (p.actor as AuditEvent['actor']) || {},
      action: p.action as string | undefined,
      decision: p.decision as string | undefined,
      outcome: p.outcome as string | undefined,
      trace_id: p.trace_id as string | undefined,
    }
    // 按当前 filter 过滤（共享纯函数，可 vitest 直测）
    if (!shouldShowEvent(e, {
      actorId: filterRef.current.actorId,
      action: filterRef.current.action,
      decision: filterRef.current.decision,
      eventType: filterRef.current.eventType,
    })) return
    if (livePaused) {
      setLiveBuffer(n => n + 1)
      return
    }
    setEvents(prev => [e, ...prev].slice(0, 500))
  })

  const resumeLive = useCallback(() => {
    setLivePaused(false)
    setLiveBuffer(0)
    void load()
  }, [load])

  return (
    <PageContainer
      title="审计时间线"
      description="JSONL 真相源 + DB 镜像；fingerprint 校验防篡改"
    >
      <Card className="mb-4">
        <CardContent className="p-5">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Input placeholder="actor id" value={actorId} onChange={e => setActorId(e.target.value)} />
            <Input placeholder="action（如 skill.contract.review）" value={action} onChange={e => setAction(e.target.value)} />
            <Select value={decision || 'ALL'} onValueChange={v => setDecision(v === 'ALL' ? '' : v)}>
              <SelectTrigger><SelectValue placeholder="决策" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部决策</SelectItem>
                {DECISIONS.filter(Boolean).map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={eventType || 'ALL'} onValueChange={v => setEventType(v === 'ALL' ? '' : v)}>
              <SelectTrigger><SelectValue placeholder="事件类型" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部事件</SelectItem>
                {EVENT_TYPES.filter(Boolean).map(e => <SelectItem key={e} value={e}>{e}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button onClick={load}>查询</Button>
          </div>
          {source && (
            <p className="text-xs text-muted-foreground mt-3">
              数据源：<code>{source}</code> · 共 {events.length} 条
            </p>
          )}
          {/* LIVE 状态条 */}
          <div className="flex items-center gap-3 mt-3 text-xs">
            {livePaused ? (
              <>
                <Badge variant="outline">PAUSED</Badge>
                <span className="text-muted-foreground">
                  实时已暂停{liveBuffer > 0 ? ` · 缓冲 ${liveBuffer} 条新事件` : ''}
                </span>
                <Button size="sm" variant="default" onClick={resumeLive}>
                  恢复实时（刷新列表）
                </Button>
              </>
            ) : (
              <>
                <Badge variant="default" className="bg-success text-success-foreground">LIVE</Badge>
                <span className="text-muted-foreground">
                  新事件自动追加到顶端（实时来自 governance WS）
                </span>
                <Button size="sm" variant="outline" onClick={() => setLivePaused(true)}>
                  暂停实时
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-5 space-y-2">
                {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-10" />)}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>时间</TableHead>
                    <TableHead>事件</TableHead>
                    <TableHead>主体</TableHead>
                    <TableHead>动作</TableHead>
                    <TableHead>决策</TableHead>
                    <TableHead>结果</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map(ev => (
                    <TableRow
                      key={ev.event_id}
                      className="cursor-pointer hover:bg-surface-2"
                      onClick={() => setSelected(ev)}
                    >
                      <TableCell className="text-xs">
                        {ev.ts ? new Date(ev.ts).toLocaleString() : '—'}
                      </TableCell>
                      <TableCell><code className="text-xs">{ev.event_type}</code></TableCell>
                      <TableCell className="text-xs">
                        <div>{ev.actor?.role || '—'}</div>
                        <div className="text-muted-foreground truncate max-w-[120px]">{ev.actor?.id}</div>
                      </TableCell>
                      <TableCell className="text-xs"><code>{ev.action || '—'}</code></TableCell>
                      <TableCell>
                        {ev.decision && <Badge variant={decisionVariant(ev.decision)} className="text-xs">{ev.decision}</Badge>}
                      </TableCell>
                      <TableCell className="text-xs">{ev.outcome || '—'}</TableCell>
                    </TableRow>
                  ))}
                  {events.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                        无匹配事件
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <h3 className="text-sm font-semibold mb-3">事件详情</h3>
            {selected ? (
              <div className="space-y-2 text-xs">
                <DetailRow k="event_id" v={selected.event_id} mono />
                <DetailRow k="trace_id" v={selected.trace_id} mono />
                <DetailRow k="fingerprint" v={selected.fingerprint} mono />
                <DetailRow k="policy_snapshot" v={selected.policy_snapshot_id} mono />
                <DetailRow k="duration_ms" v={String(selected.duration_ms ?? '')} />
                <DetailRow k="tenant_id" v={selected.actor?.tenant_id} />
                <pre className="bg-surface-2 rounded p-3 text-xs overflow-auto mt-3 max-h-[400px]">
                  {JSON.stringify(selected, null, 2)}
                </pre>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">点击左侧表格选择事件</p>
            )}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}

function DetailRow({ k, v, mono }: { k: string; v?: string; mono?: boolean }) {
  if (!v) return null
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-muted-foreground w-28">{k}</span>
      <span className={mono ? 'font-mono break-all' : 'break-all'}>{v}</span>
    </div>
  )
}
