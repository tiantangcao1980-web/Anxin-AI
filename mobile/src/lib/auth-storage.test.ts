import { beforeEach, describe, expect, it } from 'vitest'
import { createMemoryAuthStorage } from './auth-storage-memory'

describe('createMemoryAuthStorage', () => {
  beforeEach(async () => {
    const storage = createMemoryAuthStorage()
    await storage.clearAuth()
    await storage.clearBackendUrl()
  })

  it('stores access and refresh tokens with shared key semantics', async () => {
    const storage = createMemoryAuthStorage()

    await storage.setAccessToken('access-token')
    await storage.setRefreshToken('refresh-token')

    await expect(storage.getAccessToken()).resolves.toBe('access-token')
    await expect(storage.getRefreshToken()).resolves.toBe('refresh-token')
  })

  it('keeps backend url separate from auth state', async () => {
    const storage = createMemoryAuthStorage()

    await storage.setBackendUrl('http://10.0.2.2:8001/api/v1')
    await storage.setAccessToken('access-token')
    await storage.clearAuth()

    await expect(storage.getAccessToken()).resolves.toBeNull()
    await expect(storage.getBackendUrl()).resolves.toBe('http://10.0.2.2:8001/api/v1')
  })
})
