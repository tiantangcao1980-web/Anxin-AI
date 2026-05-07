import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DataNetworkBlockedError,
  apiFetch,
  buildApiHeaders,
  getApiPrivacyMode,
  installDesktopDataNetworkGuard,
  resetDesktopDataNetworkGuardForTests,
  setApiPrivacyMode,
} from './api'

describe('API privacy mode headers', () => {
  beforeEach(() => {
    setApiPrivacyMode('HYBRID')
  })

  afterEach(() => {
    resetDesktopDataNetworkGuardForTests()
    setApiPrivacyMode('HYBRID')
    vi.restoreAllMocks()
  })

  it('adds the current privacy mode to API requests', () => {
    setApiPrivacyMode('CLOUD')

    const headers = buildApiHeaders()

    expect(getApiPrivacyMode()).toBe('cloud')
    expect(headers.get('X-Privacy-Mode')).toBe('cloud')
  })

  it('keeps top-secret as a blocking client mode while sending local metadata if headers are built', () => {
    setApiPrivacyMode('top-secret')

    const headers = buildApiHeaders()

    expect(getApiPrivacyMode()).toBe('top-secret')
    expect(headers.get('X-Privacy-Mode')).toBe('local')
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

  it('blocks unified API fetches in local-only mode before network I/O', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    setApiPrivacyMode('LOCAL')

    await expect(apiFetch('/api/v1/auth/me')).rejects.toBeInstanceOf(DataNetworkBlockedError)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('blocks WebView fetches when the desktop runtime is in top-secret mode', async () => {
    const previousWindow = (globalThis as any).window
    const fetchMock = vi.fn(async () => new Response('{}'))
    const invokeMock = vi.fn(async () => '"top-secret"')

    ;(globalThis as any).window = {
      fetch: fetchMock,
      WebSocket: class FakeWebSocket {},
      __TAURI_INTERNALS__: { invoke: invokeMock },
    }

    try {
      installDesktopDataNetworkGuard()

      await expect((globalThis as any).window.fetch('/api/v1/auth/me')).rejects.toBeInstanceOf(DataNetworkBlockedError)
      expect(invokeMock).toHaveBeenCalledWith('get_current_mode')
      expect(fetchMock).not.toHaveBeenCalled()
    } finally {
      resetDesktopDataNetworkGuardForTests()
      ;(globalThis as any).window = previousWindow
    }
  })

  it('fails closed for WebSocket connections until the desktop runtime mode is known', () => {
    const previousWindow = (globalThis as any).window
    const fetchMock = vi.fn(async () => new Response('{}'))
    const invokeMock = vi.fn(() => new Promise<string>(() => {}))
    const createdSockets: string[] = []

    ;(globalThis as any).window = {
      fetch: fetchMock,
      WebSocket: class FakeWebSocket {
        constructor(url: string | URL) {
          createdSockets.push(String(url))
        }
      },
      __TAURI_INTERNALS__: { invoke: invokeMock },
    }

    try {
      resetDesktopDataNetworkGuardForTests()
      installDesktopDataNetworkGuard()

      expect(() => new (globalThis as any).window.WebSocket('wss://api.example.test/chat')).toThrow(DataNetworkBlockedError)
      expect(createdSockets).toHaveLength(0)
    } finally {
      resetDesktopDataNetworkGuardForTests()
      ;(globalThis as any).window = previousWindow
    }
  })
})
