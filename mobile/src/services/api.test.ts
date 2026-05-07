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
  logout: vi.fn(),
  syncAuth: vi.fn(),
}))

vi.mock('react-native', () => ({
  Platform: { OS: 'ios' },
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
    globalThis.fetch = vi.fn() as unknown as typeof fetch
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
