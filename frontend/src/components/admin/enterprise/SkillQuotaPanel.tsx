/**
 * Skill 沙箱配额面板 —— 后台 → 企业 → Skill 配额
 *
 * 显示 T0-T4 当日使用量 + 上限；T2-T4 可编辑上限（T0/T1 不计费）。
 * 后端见 backend/src/api/routes/skill_quota.py。
 */

import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { icons } from '@/lib/icons'
import { heading, iconSize } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface QuotaSpec {
  tier: string
  calls_per_day: number | null
  compute_ms_per_day: number | null
  concurrent_executions: number | null
}

interface QuotaTier {
  tier: string
  period_key: string
  calls: number
  compute_ms: number
  in_flight: number
  spec: QuotaSpec
}

interface QuotaSnapshot {
  tenant_id: string
  tiers: QuotaTier[]
}

const TIER_DESC: Record<string, { label: string; tone: string; editable: boolean }> = {
  T0: { label: 'Prompt-only', tone: 'text-emerald-600 dark:text-emerald-400', editable: false },
  T1: { label: 'In-process（受信）', tone: 'text-amber-600 dark:text-amber-400', editable: false },
  T2: { label: 'Subprocess 沙箱', tone: 'text-amber-600 dark:text-amber-400', editable: true },
  T3: { label: 'Container 沙箱', tone: 'text-orange-600 dark:text-orange-400', editable: true },
  T4: { label: 'Remote 沙箱', tone: 'text-red-600 dark:text-red-400', editable: true },
}

interface Props {
  orgId: string | null | undefined
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token') || ''
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const resp = await fetch(`/api/v1${path}`, { ...init, headers })
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      detail = body.detail ?? body.message ?? JSON.stringify(body)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return resp.json() as Promise<T>
}

export function SkillQuotaPanel({ orgId }: Props) {
  const [snapshot, setSnapshot] = useState<QuotaSnapshot | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    if (!orgId) return
    setLoading(true)
    setError(null)
    try {
      const data = await api<QuotaSnapshot>(`/skill-sandbox/quota/tenants/${orgId}`)
      setSnapshot(data)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId])

  if (!orgId) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
        当前账号未关联组织，无法查看 Skill 配额。
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className={heading.section}>Skill 沙箱配额</h3>
          <p className="text-sm text-muted-foreground mt-1">
            每租户每 tier 每日上限。T0/T1 不计费；T2-T4 可编辑限额。
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={() => void refresh()} disabled={loading}>
          <icons.RefreshCw className={`${iconSize.sm} mr-1`} />
          刷新
        </Button>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {snapshot && (
        <div className="space-y-2">
          {snapshot.tiers.map((t) => (
            <TierRow key={t.tier} tier={t} orgId={orgId} onSaved={() => void refresh()} />
          ))}
        </div>
      )}
    </div>
  )
}

function TierRow({
  tier,
  orgId,
  onSaved,
}: {
  tier: QuotaTier
  orgId: string
  onSaved: () => void
}) {
  const desc = TIER_DESC[tier.tier] ?? { label: tier.tier, tone: '', editable: false }
  const [calls, setCalls] = useState<string>(
    tier.spec.calls_per_day == null ? '' : String(tier.spec.calls_per_day)
  )
  const [computeMs, setComputeMs] = useState<string>(
    tier.spec.compute_ms_per_day == null ? '' : String(tier.spec.compute_ms_per_day)
  )
  const [concurrent, setConcurrent] = useState<string>(
    tier.spec.concurrent_executions == null ? '' : String(tier.spec.concurrent_executions)
  )
  const [saving, setSaving] = useState(false)

  const onSave = async () => {
    setSaving(true)
    try {
      const body = {
        calls_per_day: calls.trim() === '' ? null : Number(calls),
        compute_ms_per_day: computeMs.trim() === '' ? null : Number(computeMs),
        concurrent_executions: concurrent.trim() === '' ? null : Number(concurrent),
      }
      await api(`/skill-sandbox/quota/tenants/${orgId}/tiers/${tier.tier}`, {
        method: 'PUT',
        body: JSON.stringify(body),
      })
      toast.success(`${tier.tier} 配额已更新`)
      onSaved()
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const callsPct =
    tier.spec.calls_per_day != null && tier.spec.calls_per_day > 0
      ? Math.min(100, (tier.calls / tier.spec.calls_per_day) * 100)
      : null

  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div className="flex items-center gap-3">
          <span className={`font-mono font-semibold ${desc.tone}`}>{tier.tier}</span>
          <span className="text-sm">{desc.label}</span>
          <span className="text-xs text-muted-foreground">周期 {tier.period_key}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>当前 in-flight: <span className="font-mono text-foreground">{tier.in_flight}</span></span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3 text-sm">
        <UsageBar
          label="calls 今日"
          used={tier.calls}
          spec={tier.spec.calls_per_day}
          pct={callsPct}
        />
        <UsageBar
          label="compute_ms 今日"
          used={tier.compute_ms}
          spec={tier.spec.compute_ms_per_day}
          pct={
            tier.spec.compute_ms_per_day != null && tier.spec.compute_ms_per_day > 0
              ? Math.min(100, (tier.compute_ms / tier.spec.compute_ms_per_day) * 100)
              : null
          }
        />
        <div className="rounded-xl bg-muted/50 p-3">
          <div className="text-xs text-muted-foreground mb-1">并发上限</div>
          <div className="font-mono">
            {tier.spec.concurrent_executions == null ? '不限' : tier.spec.concurrent_executions}
          </div>
        </div>
      </div>

      {desc.editable && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-3 border-t border-border">
          <div className="space-y-1">
            <Label className="text-xs">calls / 日</Label>
            <Input
              value={calls}
              onChange={(e) => setCalls(e.target.value)}
              placeholder="留空 = 不限"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">compute_ms / 日</Label>
            <Input
              value={computeMs}
              onChange={(e) => setComputeMs(e.target.value)}
              placeholder="留空 = 不限"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">并发上限</Label>
            <Input
              value={concurrent}
              onChange={(e) => setConcurrent(e.target.value)}
              placeholder="留空 = 不限"
            />
          </div>
          <div className="flex items-end">
            <Button size="sm" className="w-full" onClick={() => void onSave()} disabled={saving}>
              {saving ? '保存中…' : '保存'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function UsageBar({
  label,
  used,
  spec,
  pct,
}: {
  label: string
  used: number
  spec: number | null
  pct: number | null
}) {
  return (
    <div className="rounded-xl bg-muted/50 p-3 space-y-1.5">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span className="font-mono text-foreground">
          {used}
          {spec != null ? ` / ${spec}` : ' / ∞'}
        </span>
      </div>
      {pct != null ? (
        <div className="h-1.5 bg-background rounded">
          <div
            className={`h-full rounded ${
              pct >= 90 ? 'bg-destructive' : pct >= 70 ? 'bg-amber-500' : 'bg-primary'
            }`}
            style={{ width: `${pct.toFixed(1)}%` }}
          />
        </div>
      ) : (
        <div className="h-1.5 bg-background rounded opacity-50" />
      )}
    </div>
  )
}

export default SkillQuotaPanel
