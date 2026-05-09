import { describe, expect, it } from 'vitest'
import { createApiClient, type UniRequestAdapter } from './api'
import { storageKeys, type UniStorageAdapter } from './storage'

function memoryStorage(seed: Record<string, unknown> = {}): UniStorageAdapter {
  const store = new Map(Object.entries(seed))
  return {
    get: (key) => store.get(key),
    set: (key, value) => store.set(key, value),
    remove: (key) => store.delete(key),
  }
}

describe('uni-mobile api client', () => {
  it('blocks local/top-secret modes before network I/O', async () => {
    const calls: unknown[] = []
    const client = createApiClient({
      storage: memoryStorage(),
      getPrivacyMode: () => 'top-secret',
      request: async (options) => {
        calls.push(options)
        return { statusCode: 200, data: { code: 200, data: {} } }
      },
    })

    await expect(client.get('/knowledge')).rejects.toThrow('隐私模式')
    expect(calls).toHaveLength(0)
  })

  it('sends bearer, route token, and privacy headers', async () => {
    const calls: Parameters<UniRequestAdapter>[0][] = []
    const client = createApiClient({
      baseUrl: 'https://staging.example/api/v1',
      storage: memoryStorage({ [storageKeys.accessToken]: 'access-1' }),
      getPrivacyMode: () => 'hybrid',
      request: async (options) => {
        calls.push(options)
        return { statusCode: 200, data: { code: 200, data: { ok: true } } }
      },
    })

    await expect(client.post('/sync/remote-control/commands', { command_type: 'desktop.status_probe' }, 'rt-1'))
      .resolves.toEqual({ ok: true })
    expect(calls[0].header).toMatchObject({
      Authorization: 'Bearer access-1',
      'X-Privacy-Mode': 'hybrid',
      'X-Route-Token': 'rt-1',
    })
  })

  it('refreshes once on auth expiry and retries with the new token', async () => {
    const calls: Parameters<UniRequestAdapter>[0][] = []
    const storage = memoryStorage({
      [storageKeys.accessToken]: 'old-token',
      [storageKeys.refreshToken]: 'refresh-1',
    })
    const client = createApiClient({
      baseUrl: 'https://staging.example/api/v1',
      storage,
      getPrivacyMode: () => 'cloud',
      request: async (options) => {
        calls.push(options)
        if (options.url.endsWith('/auth/refresh')) {
          return {
            statusCode: 200,
            data: { code: 200, data: { access_token: 'new-token', refresh_token: 'refresh-2' } },
          }
        }
        if (calls.length === 1) {
          return { statusCode: 401, data: { code: 401, data: null, message: 'expired' } }
        }
        return { statusCode: 200, data: { code: 200, data: { ok: true } } }
      },
    })

    await expect(client.get('/me')).resolves.toEqual({ ok: true })
    expect(calls.map((call) => call.url)).toEqual([
      'https://staging.example/api/v1/me',
      'https://staging.example/api/v1/auth/refresh',
      'https://staging.example/api/v1/me',
    ])
    expect(storage.get(storageKeys.accessToken)).toBe('new-token')
    expect(storage.get(storageKeys.refreshToken)).toBe('refresh-2')
  })
})
