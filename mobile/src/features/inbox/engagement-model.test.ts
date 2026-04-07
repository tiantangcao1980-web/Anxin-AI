import { describe, expect, it } from 'vitest'
import { getNotificationTargetRoute, normalizeBadgeCount } from './engagement-model'

describe('normalizeBadgeCount', () => {
  it('caps large counts and hides empty badges', () => {
    expect(normalizeBadgeCount(0)).toBeUndefined()
    expect(normalizeBadgeCount(8)).toBe(8)
    expect(normalizeBadgeCount(128)).toBe('99+')
  })
})

describe('getNotificationTargetRoute', () => {
  it('maps approval and chat notifications to dedicated mobile routes', () => {
    expect(getNotificationTargetRoute({ event_type: 'approval' })).toBe('/approvals')
    expect(getNotificationTargetRoute({ event_type: 'chat' })).toBe('/messages')
  })

  it('falls back to safe mobile destinations for other event types', () => {
    expect(getNotificationTargetRoute({ event_type: 'contract' })).toBe('/contracts')
    expect(getNotificationTargetRoute({ event_type: 'system' })).toBe('/notifications')
  })
})
