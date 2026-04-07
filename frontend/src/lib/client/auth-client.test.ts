import { describe, expect, it, vi } from 'vitest'
import { createAuthClient } from './auth-client'

describe('createAuthClient', () => {
  it('persists tokens after login and forwards desktop persistence', async () => {
    type AuthUser = {
      id: string
      email: string
      name: string
      role: string
    }

    const api = {
      login: vi.fn().mockResolvedValue({
        access_token: 'access-token',
        refresh_token: 'refresh-token',
        token_type: 'bearer',
        user: {
          id: 'u1',
          email: 'demo@anxin.com',
          name: 'Demo',
          role: 'admin',
        },
      }),
    }
    const storage = {
      setAccessToken: vi.fn(),
      setRefreshToken: vi.fn(),
    }
    const persistDesktopAuth = vi.fn().mockResolvedValue(undefined)
    const client = createAuthClient<AuthUser>({
      api,
      storage,
      persistDesktopAuth,
    })

    const result = await client.login({
      email: 'demo@anxin.com',
      password: 'secret',
    })

    expect(api.login).toHaveBeenCalledWith({
      email: 'demo@anxin.com',
      password: 'secret',
    })
    expect(storage.setAccessToken).toHaveBeenCalledWith('access-token')
    expect(storage.setRefreshToken).toHaveBeenCalledWith('refresh-token')
    expect(persistDesktopAuth).toHaveBeenCalledWith('access-token', 'refresh-token')
    expect(result.user.name).toBe('Demo')
  })
})
