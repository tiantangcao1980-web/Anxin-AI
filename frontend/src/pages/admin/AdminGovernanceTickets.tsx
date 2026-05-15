import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { API_BASE_URL, buildApiHeaders } from '@/lib/api'
import { useGovernanceWS } from '@/hooks/useGovernanceWS'
import { statusVariant } from './adminGovernanceModel'
import { PageContainer } from '@/components/ui/PageContainer'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'

interface Ticket {
  id: string
  created_at: string
  expires_at?: string
  requester_id: string
  requester_role: string
  persona?: string
  skill_id?: string
  cookbook_name?: string
  action: string
  resource: Record<string, unknown>
  status: string
  approver_id?: string
  decision_at?: string
  decision_note?: string
  policy_snapshot_id?: string
}

const STATUSES = ['pending', 'approved', 'rejected', 'expired', 'cancelled']


export default function AdminGovernanceTickets() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [status, setStatus] = useState<string>('pending')
  const [persona, setPersona] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Ticket | null>(null)
  const [note, setNote] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const headers = await buildApiHeaders()
      const params = new URLSearchParams()
      if (status) params.set('status', status)
      if (persona) params.set('persona', persona)
      params.set('limit', '200')
      const r = await fetch(`${API_BASE_URL}/governance/confirm-tickets?${params}`, { headers })
      if (!r.ok) {
        toast.error('加载 ticket 失败')
        return
      }
      const j = await r.json()
      setTickets(j.items || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [status, persona])

  useEffect(() => { void load() }, [load])

  // 实时推送：任何 ticket 状态变化都触发列表刷新
  useGovernanceWS((ev) => {
    if (ev.type.startsWith('ticket.')) {
      void load()
    }
  })

  const approve = async () => {
    if (!selected) return
    setBusy(true)
    try {
      const headers = await buildApiHeaders()
      const r = await fetch(`${API_BASE_URL}/governance/confirm-tickets/${selected.id}/approve`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
      })
      if (!r.ok) {
        toast.error('批准失败：' + (await r.text()))
        return
      }
      toast.success('已批准')
      setSelected(null)
      setNote('')
      await load()
    } finally {
      setBusy(false)
    }
  }

  const reject = async () => {
    if (!selected || !reason.trim()) {
      toast.warning('请填写拒绝理由')
      return
    }
    setBusy(true)
    try {
      const headers = await buildApiHeaders()
      const r = await fetch(`${API_BASE_URL}/governance/confirm-tickets/${selected.id}/reject`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      })
      if (!r.ok) {
        toast.error('拒绝失败：' + (await r.text()))
        return
      }
      toast.success('已拒绝')
      setSelected(null)
      setReason('')
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <PageContainer
      title="待 Confirm 工单"
      description="PEP-4 — 所有外发 / 写 / 高敏动作的人工审批入口"
    >
      <Card className="mb-4">
        <CardContent className="p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-center">
            <Select value={status || 'ALL'} onValueChange={v => setStatus(v === 'ALL' ? '' : v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部状态</SelectItem>
                {STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={persona || 'ALL'} onValueChange={v => setPersona(v === 'ALL' ? '' : v)}>
              <SelectTrigger><SelectValue placeholder="persona" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部 persona</SelectItem>
                <SelectItem value="legal-advisor">法律顾问</SelectItem>
                <SelectItem value="contract-steward">合同管家</SelectItem>
                <SelectItem value="dd-expert">尽调专家</SelectItem>
                <SelectItem value="finance-tax-advisor">财税顾问</SelectItem>
                <SelectItem value="cross-border-ecom">跨境电商助手</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={load} variant="outline">刷新</Button>
            <div className="text-sm text-muted-foreground">
              共 <strong>{tickets.length}</strong> 条
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-5 space-y-2">
                {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-12" />)}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>创建</TableHead>
                    <TableHead>申请人</TableHead>
                    <TableHead>Persona</TableHead>
                    <TableHead>动作</TableHead>
                    <TableHead>状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tickets.map(t => (
                    <TableRow
                      key={t.id}
                      className={`cursor-pointer hover:bg-surface-2 ${selected?.id === t.id ? 'bg-primary-50' : ''}`}
                      onClick={() => setSelected(t)}
                    >
                      <TableCell className="text-xs">
                        {new Date(t.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-xs">
                        <div>{t.requester_role}</div>
                        <div className="text-muted-foreground truncate max-w-[120px]">{t.requester_id}</div>
                      </TableCell>
                      <TableCell className="text-xs">{t.persona || '—'}</TableCell>
                      <TableCell className="text-xs"><code>{t.action}</code></TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(t.status)} className="text-xs">{t.status}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                  {tickets.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-12">
                        当前没有 {status} 状态的 ticket
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
            <h3 className="text-sm font-semibold mb-3">Ticket 详情</h3>
            {selected ? (
              <div className="space-y-3 text-xs">
                <DetailRow k="id" v={selected.id} mono />
                <DetailRow k="action" v={selected.action} mono />
                <DetailRow k="skill" v={selected.skill_id} mono />
                <DetailRow k="cookbook" v={selected.cookbook_name} />
                <DetailRow k="申请人" v={`${selected.requester_role} / ${selected.requester_id}`} />
                <DetailRow k="创建" v={new Date(selected.created_at).toLocaleString()} />
                <DetailRow k="过期" v={selected.expires_at ? new Date(selected.expires_at).toLocaleString() : ''} />
                {selected.decision_at && (
                  <>
                    <DetailRow k="审批人" v={selected.approver_id} />
                    <DetailRow k="决策时" v={new Date(selected.decision_at).toLocaleString()} />
                    {selected.decision_note && <DetailRow k="备注" v={selected.decision_note} />}
                  </>
                )}
                <p className="text-muted-foreground mt-3 mb-1">资源 / 上下文：</p>
                <pre className="bg-surface-2 rounded p-2 text-xs overflow-auto max-h-[180px]">
                  {JSON.stringify(selected.resource, null, 2)}
                </pre>

                {selected.status === 'pending' && (
                  <div className="space-y-3 pt-3 border-t border-border">
                    <div>
                      <label className="text-xs text-muted-foreground">批准备注（可选）</label>
                      <Textarea
                        value={note}
                        onChange={e => setNote(e.target.value)}
                        rows={2}
                        placeholder="补充说明..."
                        className="mt-1"
                      />
                      <Button
                        size="sm"
                        className="mt-2 w-full"
                        onClick={approve}
                        disabled={busy}
                      >
                        ✓ 批准 + 执行
                      </Button>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">拒绝理由 <span className="text-destructive">*</span></label>
                      <Textarea
                        value={reason}
                        onChange={e => setReason(e.target.value)}
                        rows={2}
                        placeholder="必填..."
                        className="mt-1"
                      />
                      <Button
                        size="sm"
                        variant="destructive"
                        className="mt-2 w-full"
                        onClick={reject}
                        disabled={busy || !reason.trim()}
                      >
                        ✗ 拒绝
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">点击左侧表格选择 ticket</p>
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
    <div>
      <span className="text-muted-foreground">{k}：</span>
      <span className={mono ? 'font-mono break-all' : 'break-all'}>{v}</span>
    </div>
  )
}
