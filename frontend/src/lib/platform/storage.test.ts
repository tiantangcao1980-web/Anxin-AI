import { beforeEach, describe, expect, it } from 'vitest'
import { createBrowserTokenStorage, createMemoryTokenStorage } from './storage'

describe('createMemoryTokenStorage', () => {
  beforeEach(async () => {
    const storage = createMemoryTokenStorage()
    await storage.clearAuth()
    await storage.clearBackendUrl()
  })

  it('reads and writes auth tokens through one interface', async () => {
    const storage = createMemoryTokenStorage()

    await storage.setAccessToken('token-123')
    await storage.setRefreshToken('refresh-123')

    await expect(storage.getAccessToken()).resolves.toBe('token-123')
    await expect(storage.getRefreshToken()).resolves.toBe('refresh-123')
  })

  it('clears tokens and backend url independently', async () => {
    const storage = createMemoryTokenStorage()

    await storage.setAccessToken('a')
    await storage.setRefreshToken('b')
    await storage.setBackendUrl('http://localhost:8001')
    await storage.clearAuth()

    await expect(storage.getAccessToken()).resolves.toBeNull()
    await expect(storage.getRefreshToken()).resolves.toBeNull()
    await expect(storage.getBackendUrl()).resolves.toBe('http://localhost:8001')
  })
})

function createFakeStore() {
  const values = new Map<string, string>()
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value)
    },
    removeItem: (key: string) => {
      values.delete(key)
    },
  }
}

describe('createBrowserTokenStorage', () => {
  beforeEach(async () => {
    await createMemoryTokenStorage().clearAuth()
  })

  it('keeps new browser access tokens in memory only', async () => {
    const store = createFakeStore()
    const storage = createBrowserTokenStorage(store)

    await storage.setAccessToken('access-token')
    await storage.setRefreshToken('refresh-token')

    await expect(storage.getAccessToken()).resolves.toBe('access-token')
    await expect(storage.getRefreshToken()).resolves.toBeNull()
    expect(store.getItem('access_token')).toBeNull()
    expect(store.getItem('refresh_token')).toBeNull()
  })

  it('migrates legacy localStorage tokens and strips persisted token fields', async () => {
    const store = createFakeStore()
    store.setItem('access_token', 'legacy-access')
    store.setItem('refresh_token', 'legacy-refresh')
    store.setItem('auth-storage', JSON.stringify({
      state: {
        user: { id: 'u1' },
        token: 'legacy-access',
        isAuthenticated: true,
      },
      version: 0,
    }))

    const storage = createBrowserTokenStorage(store)

    await expect(storage.getAccessToken()).resolves.toBe('legacy-access')
    await expect(storage.getRefreshToken()).resolves.toBe('legacy-refresh')
    expect(store.getItem('access_token')).toBeNull()
    expect(store.getItem('refresh_token')).toBeNull()

    const persisted = JSON.parse(store.getItem('auth-storage') ?? '{}')
    expect(persisted.state.user.id).toBe('u1')
    expect(persisted.state.token).toBeUndefined()
  })
})
