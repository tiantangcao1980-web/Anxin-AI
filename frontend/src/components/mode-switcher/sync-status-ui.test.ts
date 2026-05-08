import { describe, expect, it } from 'vitest'

import {
  SYNC_CONFLICT_BUTTON_CLASS,
  SYNC_CONFLICT_COUNT_CLASS,
  SYNC_STATUS_BUTTON_CLASS,
  SYNC_STATUS_LABEL_CLASS,
  SYNC_STATUS_TIME_CLASS,
  syncToolbarStatusLabel,
} from './sync-status-ui'

function classes(value: string) {
  return value.split(/\s+/)
}

describe('sync status toolbar UI contract', () => {
  it('keeps the sync button large and stable enough for desktop toolbar use', () => {
    const button = classes(SYNC_STATUS_BUTTON_CLASS)

    expect(button).toContain('min-h-9')
    expect(button).toContain('min-w-9')
    expect(button).toContain('shrink-0')
    expect(button).toContain('px-3')
  })

  it('keeps status labels from wrapping into the surrounding toolbar', () => {
    expect(classes(SYNC_STATUS_LABEL_CLASS)).toContain('whitespace-nowrap')
    expect(classes(SYNC_STATUS_TIME_CLASS)).toContain('whitespace-nowrap')
  })

  it('keeps conflict entry compact without falling back to a tiny text button', () => {
    const button = classes(SYNC_CONFLICT_BUTTON_CLASS)
    const count = classes(SYNC_CONFLICT_COUNT_CLASS)

    expect(button).toContain('min-h-9')
    expect(button).toContain('shrink-0')
    expect(button).toContain('px-3')
    expect(count).toContain('tabular-nums')
  })

  it('normalizes the busy label for compact toolbar display', () => {
    expect(syncToolbarStatusLabel(true, '同步中...')).toBe('同步中')
    expect(syncToolbarStatusLabel(false, '已同步')).toBe('已同步')
    expect(syncToolbarStatusLabel(false, '同步中...')).toBe('同步中')
  })
})
