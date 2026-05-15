// -*- coding: utf-8 -*-
/**
 * 401 Token Refresh 单飞器
 *
 * 多个并发请求遇到 401 时，只有第一个发起 /auth/refresh，其余排队等待结果，
 * 避免 refresh_token 被并发消耗（V2 → V3 的常见线上踩坑点）。
 */

import Taro from '@tarojs/taro'
import { tokenStorage } from './token'
import { resolveBaseUrl } from '../api/baseUrl'
import { assertMiniProgramDataNetworkAllowed, getStoredPrivacyMode } from '../privacy'

let inflight: Promise<string> | null = null

export async function refreshAccessToken(): Promise<string> {
  if (inflight) return inflight
  inflight = (async () => {
    try {
      // 隐私模式 fail-closed：refresh 也是数据网络，敏感模式下禁止出门
      const privacyMode = getStoredPrivacyMode()
      assertMiniProgramDataNetworkAllowed(privacyMode)

      const rt = tokenStorage.getRefreshToken()
      if (!rt) throw new Error('NO_REFRESH_TOKEN')

      const res = await Taro.request({
        url: `${resolveBaseUrl()}/auth/refresh`,
        method: 'POST',
        data: { refresh_token: rt },
        timeout: 10_000,
        header: {
          'Content-Type': 'application/json',
          'X-Privacy-Mode': privacyMode,
        },
      })

      // 兼容扁平 / ApiResponse 包装
      const body = res.data as Record<string, any>
      const payload = body?.data ?? body
      const accessToken: string | undefined = payload?.access_token
      const newRefresh: string | undefined = payload?.refresh_token
      if (!accessToken) throw new Error('REFRESH_NO_ACCESS_TOKEN')

      tokenStorage.setAccessToken(accessToken)
      if (newRefresh) tokenStorage.setRefreshToken(newRefresh)
      return accessToken
    } catch (err) {
      tokenStorage.clearAuth()
      throw err
    } finally {
      inflight = null
    }
  })()
  return inflight
}

/** 仅给测试用 */
export function __resetRefreshState(): void {
  inflight = null
}
