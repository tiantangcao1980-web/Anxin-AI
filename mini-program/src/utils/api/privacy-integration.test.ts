/**
 * 隐私守门 × 网络入口集成测试
 *
 * 覆盖 commit 0949c127 的接入契约：
 *   utils/api/client.ts rawRequest    敏感模式下 Taro.request 永不被调用
 *   utils/auth/refresh.ts             敏感模式下 token refresh 不发请求
 *   utils/api/auth.ts  wechatLogin    敏感模式下 Taro.login 也不被调用
 *
 * 设计：用 vi.spyOn 替换 Taro.request / Taro.login，确认守门生效时
 *       这两个 API 的调用次数为 0；standard 模式下被调用。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Taro, { __storage } from '../../../tests/stubs/taro'
import { setStoredPrivacyMode } from '../privacy'
import { isMiniProgramPrivacyNetworkBlockedError } from '../privacy'

// 拦截 baseUrl 解析
vi.mock('../api/baseUrl', () => ({
  resolveBaseUrl: () => 'http://test.anxinagent.com/api/v1',
}))
// 与上同路径，因为 import 是相对 utils/api/，此处保留兼容
vi.mock('./baseUrl', () => ({
  resolveBaseUrl: () => 'http://test.anxinagent.com/api/v1',
}))

afterEach(() => {
  __storage.reset()
  vi.restoreAllMocks()
})

describe('client.ts rawRequest × privacy', () => {
  beforeEach(() => {
    setStoredPrivacyMode('standard')
  })

  it('standard 模式：Taro.request 被调用 1 次', async () => {
    const reqSpy = vi.spyOn(Taro, 'request').mockResolvedValue({
      data: { code: 200, data: { ok: true } },
      statusCode: 200,
      header: {},
    } as never)
    const { apiClient } = await import('./client')
    await apiClient.get('/probe').catch(() => {})
    expect(reqSpy).toHaveBeenCalledTimes(1)
  })

  it('local 模式：Taro.request 永不被调用 + throw Privacy 错误', async () => {
    setStoredPrivacyMode('local')
    const reqSpy = vi.spyOn(Taro, 'request')
    const { apiClient } = await import('./client')
    let caught: unknown = null
    try {
      await apiClient.get('/probe')
    } catch (e) {
      caught = e
    }
    expect(reqSpy).not.toHaveBeenCalled()
    expect(isMiniProgramPrivacyNetworkBlockedError(caught)).toBe(true)
  })

  it('top-secret 模式：Taro.request 永不被调用 + throw Privacy 错误', async () => {
    setStoredPrivacyMode('top-secret')
    const reqSpy = vi.spyOn(Taro, 'request')
    const { apiClient } = await import('./client')
    let caught: unknown = null
    try {
      await apiClient.get('/probe')
    } catch (e) {
      caught = e
    }
    expect(reqSpy).not.toHaveBeenCalled()
    expect(isMiniProgramPrivacyNetworkBlockedError(caught)).toBe(true)
  })

  it('standard 出站请求附 X-Privacy-Mode header', async () => {
    let capturedHeader: Record<string, string> | undefined
    vi.spyOn(Taro, 'request').mockImplementation(((opts: { header?: Record<string, string> }) => {
      capturedHeader = opts.header
      return Promise.resolve({
        data: { code: 200, data: { ok: true } },
        statusCode: 200,
        header: {},
      })
    }) as never)
    const { apiClient } = await import('./client')
    await apiClient.get('/probe').catch(() => {})
    expect(capturedHeader?.['X-Privacy-Mode']).toBe('standard')
  })
})

describe('auth.ts wechatMiniprogramLogin × privacy', () => {
  it('local 模式：Taro.login 永不被调用 + throw Privacy 错误', async () => {
    setStoredPrivacyMode('local')
    const loginSpy = vi.spyOn(Taro, 'login')
    const { wechatMiniprogramLogin } = await import('./auth')
    let caught: unknown = null
    try {
      await wechatMiniprogramLogin()
    } catch (e) {
      caught = e
    }
    expect(loginSpy).not.toHaveBeenCalled()
    expect(isMiniProgramPrivacyNetworkBlockedError(caught)).toBe(true)
  })
})

describe('refresh.ts refreshAccessToken × privacy', () => {
  it('local 模式：不发 Taro.request、抛 Privacy 错误、并清空 token（fail-closed）', async () => {
    const { tokenStorage } = await import('../auth/token')
    tokenStorage.setAccessToken('stale-access')
    tokenStorage.setRefreshToken('stale-refresh')

    setStoredPrivacyMode('local')
    const reqSpy = vi.spyOn(Taro, 'request')

    const { refreshAccessToken, __resetRefreshState } = await import('../auth/refresh')
    __resetRefreshState()

    let caught: unknown = null
    try {
      await refreshAccessToken()
    } catch (e) {
      caught = e
    }

    expect(reqSpy).not.toHaveBeenCalled()
    expect(isMiniProgramPrivacyNetworkBlockedError(caught)).toBe(true)
    // token 已被清空 → 调用方据此跳登录，不会无限重试
    expect(tokenStorage.getAccessToken()).toBeFalsy()
    expect(tokenStorage.getRefreshToken()).toBeFalsy()
  })
})
