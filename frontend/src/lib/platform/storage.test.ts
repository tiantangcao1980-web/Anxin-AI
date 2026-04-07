import { beforeEach, describe, expect, it } from 'vitest'
import { createMemoryTokenStorage } from './storage'

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
