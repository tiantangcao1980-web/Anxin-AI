import { describe, expect, it } from 'vitest'
import { createWechatLoginClient } from './wechat'

describe('uni-mobile WeChat platform adapter', () => {
  it('blocks local mode before calling uni.login', async () => {
    let loginCalls = 0
    const client = createWechatLoginClient({
      getPrivacyMode: () => 'local',
      loginAdapter: {
        async login() {
          loginCalls += 1
          return { code: 'wx-code' }
        },
      },
      postCode: async () => ({
        access_token: 'token',
        token_type: 'bearer',
        user: { id: 'u1' },
      }),
    })

    await expect(client.loginWithWeixin()).rejects.toThrow('隐私模式')
    expect(loginCalls).toBe(0)
  })

  it('posts wx login code through code2session adapter', async () => {
    const postedCodes: string[] = []
    const client = createWechatLoginClient({
      getPrivacyMode: () => 'cloud',
      loginAdapter: {
        async login() {
          return { code: 'wx-code' }
        },
      },
      postCode: async (code) => {
        postedCodes.push(code)
        return {
          access_token: 'token',
          token_type: 'bearer',
          user: { id: 'u1' },
        }
      },
    })

    await expect(client.loginWithWeixin()).resolves.toMatchObject({ access_token: 'token' })
    expect(postedCodes).toEqual(['wx-code'])
  })
})
