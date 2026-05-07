import { beforeEach, describe, expect, it } from 'vitest'
import { buildApiHeaders, getApiPrivacyMode, setApiPrivacyMode } from './api'

describe('API privacy mode headers', () => {
  beforeEach(() => {
    setApiPrivacyMode('HYBRID')
  })

  it('adds the current privacy mode to API requests', () => {
    setApiPrivacyMode('CLOUD')

    const headers = buildApiHeaders()

    expect(getApiPrivacyMode()).toBe('cloud')
    expect(headers.get('X-Privacy-Mode')).toBe('cloud')
  })

  it('fails back to hybrid for invalid privacy modes', () => {
    setApiPrivacyMode('unknown')

    const headers = buildApiHeaders()

    expect(getApiPrivacyMode()).toBe('hybrid')
    expect(headers.get('X-Privacy-Mode')).toBe('hybrid')
  })

  it('preserves caller headers while adding auth and mode metadata', () => {
    const headers = buildApiHeaders(
      { Accept: 'application/json', 'Content-Type': 'text/plain' },
      { token: 'access-token', privacyMode: 'LOCAL' },
    )

    expect(headers.get('Accept')).toBe('application/json')
    expect(headers.get('Content-Type')).toBe('text/plain')
    expect(headers.get('Authorization')).toBe('Bearer access-token')
    expect(headers.get('X-Privacy-Mode')).toBe('local')
  })
})
