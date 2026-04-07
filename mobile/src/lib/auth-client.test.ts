import { describe, expect, it, vi } from 'vitest'
import { createAuthClient } from './auth-client'

describe('createAuthClient', () => {
  it('persists mobile auth session after login', async () => {
    type MobileUser = {
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
          email: 'mobile@anxin.com',
          name: '移动用户',
          role: 'client',
        },
      }),
    }
    const storage = {
      setAccessToken: vi.fn(),
      setRefreshToken: vi.fn(),
    }
    const client = createAuthClient<MobileUser>({
      api,
      storage,
    })

    const result = await client.login({
      email: 'mobile@anxin.com',
      password: 'secret',
    })

    expect(api.login).toHaveBeenCalledWith({
      email: 'mobile@anxin.com',
      password: 'secret',
    })
    expect(storage.setAccessToken).toHaveBeenCalledWith('access-token')
    expect(storage.setRefreshToken).toHaveBeenCalledWith('refresh-token')
    expect(result.user.name).toBe('移动用户')
  })
})
