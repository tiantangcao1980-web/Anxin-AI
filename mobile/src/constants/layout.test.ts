import { describe, expect, it, vi } from 'vitest'

vi.mock('react-native', () => ({
  Dimensions: {
    get: () => ({ width: 390, height: 844 }),
  },
  Platform: {
    OS: 'ios',
  },
  StatusBar: {
    currentHeight: 24,
  },
}))

describe('Layout touch targets', () => {
  it('keeps mobile interactive targets at or above the 44pt baseline', async () => {
    const { Layout } = await import('./layout')

    expect(Layout.touchTarget.min).toBeGreaterThanOrEqual(44)
    expect(Layout.tabBarBaseHeight).toBeGreaterThanOrEqual(Layout.touchTarget.min)
    expect(Layout.headerHeight).toBeGreaterThanOrEqual(Layout.touchTarget.min)
  })

  it('keeps touch hit slop explicit for compact icon actions', async () => {
    const { Layout } = await import('./layout')

    expect(Layout.touchTarget.hitSlop).toBeGreaterThan(0)
  })
})
