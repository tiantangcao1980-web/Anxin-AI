import { assertDataNetworkAllowed, type PrivacyMode } from '@/services/privacy'
import type { ApiResponse } from '@/services/api'

export interface WechatLoginAdapter {
  login(): Promise<{ code?: string }>
}

export interface WechatLoginClientOptions {
  loginAdapter?: WechatLoginAdapter
  postCode?: (code: string) => Promise<WechatCodeSessionResponse>
  getPrivacyMode: () => PrivacyMode
}

export interface WechatCodeSessionResponse {
  access_token: string
  refresh_token?: string
  token_type: string
  user: unknown
}

export function createUniWechatLoginAdapter(): WechatLoginAdapter {
  return {
    login: () =>
      new Promise((resolve, reject) => {
        uni.login({
          provider: 'weixin',
          success: resolve,
          fail: reject,
        })
      }),
  }
}

function unwrapCodeSession(body: ApiResponse<WechatCodeSessionResponse> | WechatCodeSessionResponse) {
  if ('code' in body && 'data' in body) {
    if (body.code !== 200) throw new Error(body.message || '微信登录失败')
    return body.data
  }
  return body
}

export function createWechatLoginClient(options: WechatLoginClientOptions) {
  const loginAdapter = options.loginAdapter ?? createUniWechatLoginAdapter()

  return {
    async loginWithWeixin(): Promise<WechatCodeSessionResponse> {
      assertDataNetworkAllowed(options.getPrivacyMode())
      const result = await loginAdapter.login()
      if (!result.code) throw new Error('微信登录未返回 code')
      if (!options.postCode) throw new Error('微信 code2session 未配置')
      return unwrapCodeSession(await options.postCode(result.code))
    },
  }
}
