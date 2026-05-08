import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  storage: {
    getAccessToken: vi.fn(),
    setAccessToken: vi.fn(),
    getRefreshToken: vi.fn(),
    setRefreshToken: vi.fn(),
    getBackendUrl: vi.fn(),
    setBackendUrl: vi.fn(),
    clearBackendUrl: vi.fn(),
    clearAuth: vi.fn(),
  },
  asyncStorage: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  },
  logout: vi.fn(),
  syncAuth: vi.fn(),
}))

vi.mock('react-native', () => ({
  Platform: { OS: 'ios' },
}))

vi.mock('@react-native-async-storage/async-storage', () => ({
  default: mocks.asyncStorage,
}))

vi.mock('../lib/auth-storage', () => ({
  getAuthStorage: () => mocks.storage,
}))

vi.mock('../lib/store', () => ({
  useAuthStore: {
    getState: () => ({
      logout: mocks.logout,
      syncAuth: mocks.syncAuth,
    }),
  },
}))

const jsonResponse = (status: number, body: unknown) => ({
  status,
  ok: status >= 200 && status < 300,
  json: vi.fn().mockResolvedValue(body),
})

describe('mobile API refresh behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('__DEV__', true)
    mocks.storage.getAccessToken.mockResolvedValue('access-token')
    mocks.storage.getRefreshToken.mockResolvedValue('refresh-token')
    mocks.storage.getBackendUrl.mockResolvedValue('http://localhost:8001/api/v1')
    mocks.asyncStorage.getItem.mockResolvedValue('cloud')
    globalThis.fetch = vi.fn() as unknown as typeof fetch
  })

  it('sends the current privacy mode with mobile API requests', async () => {
    const { request } = await import('./api')
    mocks.asyncStorage.getItem.mockResolvedValue('hybrid')
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, { code: 200, data: { ok: true }, message: 'ok' }) as unknown as Response,
    )

    await expect(request<{ ok: boolean }>({ url: '/cases', retry: 0 })).resolves.toEqual({ ok: true })

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8001/api/v1/cases',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token',
          'X-Privacy-Mode': 'hybrid',
        }),
      }),
    )
  })

  it('requests remote desktop-control status through the governed sync endpoint', async () => {
    const { desktopControlApi } = await import('./api')
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, {
        code: 200,
        data: {
          available: false,
          status: 'not_configured',
          desktop_device_id: 'desktop-a',
          required_controls: ['device_pairing'],
          message: '尚未配置',
        },
        message: 'ok',
      }) as unknown as Response,
    )

    await expect(desktopControlApi.getStatus('desktop-a')).resolves.toMatchObject({
      available: false,
      status: 'not_configured',
    })

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8001/api/v1/sync/remote-control/status?desktop_device_id=desktop-a',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token',
          'X-Privacy-Mode': 'cloud',
        }),
      }),
    )
  })

  it('issues a short-lived route token for a confirmed remote-control pairing', async () => {
    const { desktopControlApi } = await import('./api')
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, {
        code: 200,
        data: {
          allowed: true,
          reason_code: 'issued',
          human_message: 'ok',
          route_token: 'route-token',
          route_id: 'route-a',
          pairing_id: 'pairing-a',
          required_scope: 'desktop:control',
          route_key: 'desktop-control',
          expires_at: '2026-05-08T10:00:00Z',
        },
        message: 'ok',
      }) as unknown as Response,
    )

    await expect(desktopControlApi.issueRouteToken({
      pairing_id: 'pairing-a',
      ttl_seconds: 300,
    })).resolves.toMatchObject({
      allowed: true,
      route_token: 'route-token',
      pairing_id: 'pairing-a',
    })

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8001/api/v1/sync/remote-control/route-token',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ pairing_id: 'pairing-a', ttl_seconds: 300 }),
        headers: expect.objectContaining({
          Authorization: 'Bearer access-token',
          'X-Privacy-Mode': 'cloud',
        }),
      }),
    )
  })

  it('enqueues only the governed desktop safe probe command from mobile', async () => {
    const { desktopControlApi } = await import('./api')
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, {
        code: 200,
        data: {
          command_id: 'command-a',
          pairing_id: 'pairing-a',
          desktop_device_id: 'desktop-a',
          command_type: 'desktop.status_probe',
          risk_level: 'l2',
          status: 'queued',
          route_id: 'route-a',
          route_consumer_id: 'pairing-a',
          route_scopes: ['desktop:control'],
          second_confirmed: false,
          expires_at: '2026-05-08T10:00:00Z',
          result_summary: {},
        },
        message: 'ok',
      }) as unknown as Response,
    )

    await expect(desktopControlApi.enqueueSafeProbeCommand({
      desktop_device_id: 'desktop-a',
      pairing_id: 'pairing-a',
      route_token: 'route-token',
      privacy_mode: 'hybrid',
    })).resolves.toMatchObject({
      command_id: 'command-a',
      command_type: 'desktop.status_probe',
      risk_level: 'l2',
      status: 'queued',
    })

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8001/api/v1/sync/remote-control/commands',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          desktop_device_id: 'desktop-a',
          pairing_id: 'pairing-a',
          route_token: 'route-token',
          privacy_mode: 'hybrid',
          command_type: 'desktop.status_probe',
          risk_level: 'l2',
          second_confirmed: false,
          expires_in_seconds: 120,
          payload: {
            probe: 'status',
            requested_from: 'mobile',
          },
        }),
      }),
    )
  })

  it('fails closed before desktop-control status network I/O in local privacy mode', async () => {
    const { desktopControlApi } = await import('./api')
    mocks.asyncStorage.getItem.mockResolvedValue('local')

    await expect(desktopControlApi.getStatus()).rejects.toThrow('本地模式下禁止连接云端服务')

    expect(fetch).not.toHaveBeenCalled()
  })

  it('fails closed before desktop-control command network I/O in local privacy mode', async () => {
    const { desktopControlApi } = await import('./api')
    mocks.asyncStorage.getItem.mockResolvedValue('local')

    await expect(desktopControlApi.enqueueSafeProbeCommand({
      desktop_device_id: 'desktop-a',
      pairing_id: 'pairing-a',
      route_token: 'route-token',
      privacy_mode: 'local',
    })).rejects.toThrow('本地模式下禁止连接云端服务')

    expect(fetch).not.toHaveBeenCalled()
  })

  it('requests remote-control pairing through the governed endpoint', async () => {
    const { desktopControlApi } = await import('./api')
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, {
        code: 200,
        data: {
          pairing_id: 'pairing-a',
          mobile_device_id: 'mobile-a',
          desktop_device_id: 'desktop-a',
          requested_scopes: ['desktop:control'],
          privacy_mode: 'hybrid',
          status: 'pending_desktop_confirmation',
          expires_at: '2026-05-08T10:00:00Z',
          confirmed_at: null,
        },
        message: 'ok',
      }) as unknown as Response,
    )

    await expect(desktopControlApi.requestPairing({
      mobile_device_id: 'mobile-a',
      desktop_device_id: 'desktop-a',
      requested_scopes: ['desktop:control'],
      privacy_mode: 'hybrid',
    })).resolves.toMatchObject({
      pairing_id: 'pairing-a',
      status: 'pending_desktop_confirmation',
    })

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8001/api/v1/sync/remote-control/pairings',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          mobile_device_id: 'mobile-a',
          desktop_device_id: 'desktop-a',
          requested_scopes: ['desktop:control'],
          privacy_mode: 'hybrid',
        }),
      }),
    )
  })

  it('fails closed before network I/O in local privacy mode', async () => {
    const { request } = await import('./api')
    mocks.asyncStorage.getItem.mockResolvedValue('local')

    await expect(request({ url: '/cases', retry: 0 })).rejects.toThrow('本地模式下禁止连接云端服务')

    expect(fetch).not.toHaveBeenCalled()
  })

  it('keeps the stored session when refresh fails because the network is unavailable', async () => {
    const { request } = await import('./api')
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { code: 401, message: 'expired' }) as unknown as Response)
      .mockRejectedValueOnce(new Error('Network request failed'))

    await expect(request({ url: '/cases', retry: 1 })).rejects.toThrow('暂时无法刷新登录状态')

    expect(mocks.storage.clearAuth).not.toHaveBeenCalled()
    expect(mocks.logout).not.toHaveBeenCalled()
  })

  it('clears auth only when the refresh endpoint confirms the session is expired', async () => {
    const { request } = await import('./api')
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(401, { code: 401, message: 'expired' }) as unknown as Response)
      .mockResolvedValueOnce(jsonResponse(401, { code: 401, message: 'refresh expired' }) as unknown as Response)

    await expect(request({ url: '/cases', retry: 1 })).rejects.toThrow('登录已过期')

    expect(mocks.storage.clearAuth).toHaveBeenCalledTimes(1)
    expect(mocks.logout).toHaveBeenCalledTimes(1)
  })
})
