import { describe, expect, it } from 'vitest'
import { nextBackoff, wsUrlFromApiBase } from './useGovernanceWS'

describe('useGovernanceWS pure helpers', () => {
  describe('wsUrlFromApiBase', () => {
    it('rewrites absolute http base to ws', () => {
      expect(wsUrlFromApiBase('http://localhost:8000/api/v1'))
        .toBe('ws://localhost:8000/api/v1/governance/ws')
    })

    it('rewrites absolute https base to wss', () => {
      expect(wsUrlFromApiBase('https://api.anxin.example/api/v1'))
        .toBe('wss://api.anxin.example/api/v1/governance/ws')
    })

    it('uses provided origin for relative path', () => {
      const url = wsUrlFromApiBase('/api/v1', {
        protocol: 'https:', host: 'app.anxin.example',
      })
      expect(url).toBe('wss://app.anxin.example/api/v1/governance/ws')
    })

    it('falls back to ws (no TLS) when origin is http', () => {
      const url = wsUrlFromApiBase('/api/v1', {
        protocol: 'http:', host: 'localhost:3000',
      })
      expect(url).toBe('ws://localhost:3000/api/v1/governance/ws')
    })
  })

  describe('nextBackoff', () => {
    it('doubles current delay', () => {
      expect(nextBackoff(1000)).toBe(2000)
      expect(nextBackoff(2000)).toBe(4000)
      expect(nextBackoff(4000)).toBe(8000)
    })

    it('caps at 30s', () => {
      expect(nextBackoff(20_000)).toBe(30_000)
      expect(nextBackoff(99_999)).toBe(30_000)
    })

    it('respects custom max', () => {
      expect(nextBackoff(5000, 8000)).toBe(8000)
      expect(nextBackoff(3000, 8000)).toBe(6000)
    })

    it('progression from 1s caps in 5 hops', () => {
      // 1000 → 2000 → 4000 → 8000 → 16000 → 30000 (cap)
      let d = 1000
      const series: number[] = []
      for (let i = 0; i < 6; i++) {
        d = nextBackoff(d)
        series.push(d)
      }
      expect(series).toEqual([2000, 4000, 8000, 16000, 30000, 30000])
    })
  })
})
