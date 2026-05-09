import { describe, expect, it } from 'vitest'
import { color, radius, spacing, touch } from './tokens'

describe('uni-mobile design tokens', () => {
  it('keeps mobile touch target and page rhythm explicit', () => {
    expect(touch.minTargetPx).toBeGreaterThanOrEqual(44)
    expect(touch.minTargetRpx).toBeGreaterThanOrEqual(88)
    expect(spacing.pageRpx).toBeGreaterThanOrEqual(32)
    expect(radius.cardRpx).toBeLessThanOrEqual(16)
  })

  it('uses a multi-role palette instead of one-note page colors', () => {
    expect(new Set(Object.values(color)).size).toBeGreaterThanOrEqual(8)
    expect(color.primary).not.toBe(color.background)
  })
})
