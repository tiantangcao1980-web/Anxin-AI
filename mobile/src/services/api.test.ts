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
