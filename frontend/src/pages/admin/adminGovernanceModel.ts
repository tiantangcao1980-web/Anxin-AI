/**
 * Governance dashboard 纯函数 — 与 React / DOM 无关，便于 vitest 直接单测。
 *
 * 抽取出来的函数：
 *   - decisionVariant(decision)  → Badge variant（ALLOW / DENY / STEP_UP / CONFIRM）
 *   - statusVariant(status)      → ConfirmTicket 状态 → variant
 *   - shadowVariant(status)      → ShadowRun 状态 → variant
 *   - aggregateBuckets(items)    → 累加 by_bucket_count 等汇总
 *   - shouldFilterEvent(...)     → 实时事件流是否符合当前 filter
 */
export type Variant = 'default' | 'destructive' | 'secondary' | 'outline'

export function decisionVariant(d?: string | null): Variant {
  if (d === 'ALLOW') return 'default'
  if (d === 'DENY') return 'destructive'
  if (d === 'REQUIRE_STEP_UP' || d === 'REQUIRE_CONFIRM') return 'secondary'
  return 'outline'
}

export function statusVariant(s: string): Variant {
  if (s === 'approved') return 'default'
  if (s === 'rejected' || s === 'expired') return 'destructive'
  if (s === 'pending') return 'secondary'
  return 'outline'
}

export function shadowVariant(s: string): Variant {
  if (s === 'passed') return 'default'
  if (s === 'failed') return 'destructive'
  if (s === 'running') return 'secondary'
  return 'outline'
}

export interface AuditFilter {
  actorId?: string
  action?: string
  decision?: string
  eventType?: string
}

export interface AuditEventLike {
  event_type: string
  actor?: { id?: string }
  action?: string
  decision?: string
}

/** 实时事件是否应被当前 filter 接收。任一不匹配返回 false。 */
export function shouldShowEvent(ev: AuditEventLike, f: AuditFilter): boolean {
  if (f.actorId && (ev.actor?.id ?? '') !== f.actorId) return false
  if (f.action && ev.action !== f.action) return false
  if (f.decision && ev.decision !== f.decision) return false
  if (f.eventType && ev.event_type !== f.eventType) return false
  return true
}

/** ShadowRun 错误率（保留 3 位小数）+ 是否超阈值 */
export function shadowErrorRate(run: {
  total_invocations: number
  review_errors: number
  max_error_rate: number
}): { rate: number; overThreshold: boolean } {
  const rate = run.total_invocations > 0
    ? run.review_errors / run.total_invocations
    : 0
  return { rate: Math.round(rate * 1000) / 1000, overThreshold: rate > run.max_error_rate }
}

/** Ticket SLA：根据 created_at + expires_at 算紧急程度 */
export type Urgency = 'expired' | 'critical' | 'warning' | 'normal'

export function ticketUrgency(opts: {
  created_at: string
  expires_at?: string | null
  now?: Date
}): Urgency {
  if (!opts.expires_at) return 'normal'
  const now = opts.now ?? new Date()
  const expires = new Date(opts.expires_at)
  const created = new Date(opts.created_at)
  if (Number.isNaN(expires.getTime()) || Number.isNaN(created.getTime())) return 'normal'

  const totalMs = expires.getTime() - created.getTime()
  const elapsedMs = now.getTime() - created.getTime()
  if (now >= expires) return 'expired'
  if (totalMs <= 0) return 'normal'
  const ratio = elapsedMs / totalMs
  if (ratio >= 0.9) return 'critical'
  if (ratio >= 0.7) return 'warning'
  return 'normal'
}
