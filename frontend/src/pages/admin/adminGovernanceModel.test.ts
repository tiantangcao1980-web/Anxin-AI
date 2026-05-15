import { describe, expect, it } from 'vitest'
import {
  decisionVariant,
  shadowErrorRate,
  shadowVariant,
  shouldShowEvent,
  statusVariant,
  ticketUrgency,
} from './adminGovernanceModel'

describe('adminGovernanceModel', () => {
  describe('decisionVariant', () => {
    it('maps each decision to expected variant', () => {
      expect(decisionVariant('ALLOW')).toBe('default')
      expect(decisionVariant('DENY')).toBe('destructive')
      expect(decisionVariant('REQUIRE_STEP_UP')).toBe('secondary')
      expect(decisionVariant('REQUIRE_CONFIRM')).toBe('secondary')
      expect(decisionVariant('UNKNOWN')).toBe('outline')
      expect(decisionVariant(undefined)).toBe('outline')
      expect(decisionVariant(null)).toBe('outline')
    })
  })

  describe('statusVariant', () => {
    it('handles every ticket status', () => {
      expect(statusVariant('approved')).toBe('default')
      expect(statusVariant('pending')).toBe('secondary')
      expect(statusVariant('rejected')).toBe('destructive')
      expect(statusVariant('expired')).toBe('destructive')
      expect(statusVariant('cancelled')).toBe('outline')
    })
  })

  describe('shadowVariant', () => {
    it('passed / failed / running map correctly', () => {
      expect(shadowVariant('passed')).toBe('default')
      expect(shadowVariant('failed')).toBe('destructive')
      expect(shadowVariant('running')).toBe('secondary')
      expect(shadowVariant('cancelled')).toBe('outline')
    })
  })

  describe('shouldShowEvent', () => {
    const ev = {
      event_type: 'skill.execute',
      actor: { id: 'u1' },
      action: 'skill.contract-steward.review',
      decision: 'ALLOW',
    }

    it('no filter passes through', () => {
      expect(shouldShowEvent(ev, {})).toBe(true)
    })

    it('actorId mismatch rejects', () => {
      expect(shouldShowEvent(ev, { actorId: 'u2' })).toBe(false)
      expect(shouldShowEvent(ev, { actorId: 'u1' })).toBe(true)
    })

    it('all filter dimensions are checked', () => {
      expect(shouldShowEvent(ev, {
        actorId: 'u1', action: 'skill.contract-steward.review',
        decision: 'ALLOW', eventType: 'skill.execute',
      })).toBe(true)
      // 任一不匹配
      expect(shouldShowEvent(ev, { decision: 'DENY' })).toBe(false)
      expect(shouldShowEvent(ev, { eventType: 'authz.decide' })).toBe(false)
    })

    it('missing actor handles gracefully', () => {
      const e = { event_type: 'system.boot' }
      expect(shouldShowEvent(e, { actorId: 'u1' })).toBe(false)
      expect(shouldShowEvent(e, {})).toBe(true)
    })
  })

  describe('shadowErrorRate', () => {
    it('returns 0 when no invocations', () => {
      expect(shadowErrorRate({
        total_invocations: 0, review_errors: 0, max_error_rate: 0.05,
      })).toEqual({ rate: 0, overThreshold: false })
    })

    it('flags overThreshold correctly', () => {
      // 6/100 = 6% > 5%
      const r = shadowErrorRate({
        total_invocations: 100, review_errors: 6, max_error_rate: 0.05,
      })
      expect(r.rate).toBe(0.06)
      expect(r.overThreshold).toBe(true)
    })

    it('passes at boundary (rate == max → not strictly over)', () => {
      const r = shadowErrorRate({
        total_invocations: 100, review_errors: 5, max_error_rate: 0.05,
      })
      expect(r.rate).toBe(0.05)
      expect(r.overThreshold).toBe(false)
    })
  })

  describe('ticketUrgency', () => {
    const created = '2026-05-15T00:00:00Z'
    const expires = '2026-05-18T00:00:00Z'   // 3-day window

    it('normal in early window', () => {
      // 第 1 天 < 70% → normal
      expect(ticketUrgency({
        created_at: created, expires_at: expires,
        now: new Date('2026-05-15T12:00:00Z'),
      })).toBe('normal')
    })

    it('warning at 70%+ elapsed', () => {
      // 70% of 3 days ≈ 2.1 day mark
      expect(ticketUrgency({
        created_at: created, expires_at: expires,
        now: new Date('2026-05-17T06:00:00Z'),   // 2.25 d
      })).toBe('warning')
    })

    it('critical at 90%+ elapsed', () => {
      // 90% of 3 days ≈ 2.7 day
      expect(ticketUrgency({
        created_at: created, expires_at: expires,
        now: new Date('2026-05-17T18:00:00Z'),
      })).toBe('critical')
    })

    it('expired past expires_at', () => {
      expect(ticketUrgency({
        created_at: created, expires_at: expires,
        now: new Date('2026-05-18T00:00:01Z'),
      })).toBe('expired')
    })

    it('handles missing expires_at as normal', () => {
      expect(ticketUrgency({ created_at: created })).toBe('normal')
    })

    it('handles malformed dates gracefully', () => {
      expect(ticketUrgency({
        created_at: 'invalid', expires_at: 'also-bad',
      })).toBe('normal')
    })
  })
})
