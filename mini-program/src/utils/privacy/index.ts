// -*- coding: utf-8 -*-
/**
 * 小程序隐私模式 fail-closed 守门（P21A 重建版）。
 *
 * 历史背景：
 *   - commit e99092e6 为旧版 services/api.ts 引入了 local / top-secret 隐私模式，
 *     在 Taro.request / Taro.login / refreshToken 前置 assertion，
 *     一旦命中"敏感模式"立刻 fail-closed，不发出任何数据网络请求。
 *   - commit da702865 (P21A) 重写为 utils/api/client.ts 时旧守门被一并删除，
 *     scripts/check-privacy-boundary.js 失效。
 *
 * 本模块按相同语义重建：
 *   - 隐私模式 = standard / local / top-secret
 *   - `local` 与 `top-secret` 视为"数据网络禁用"
 *   - 任意网络入口（client、refresh、wxLogin）调用前必须 assert
 *   - 默认 standard；用户在「我的」页可切换
 *
 * Release Directive (来自 e99092e6)：
 *   Do not add new mini-program network paths without routing through this
 *   guard, or you re-open the cross-device privacy regression.
 */

import Taro from '@tarojs/taro'

export type MiniProgramPrivacyMode = 'standard' | 'local' | 'top-secret'

const PRIVACY_STORAGE_KEY = 'anxin:privacy_mode'
const DATA_NETWORK_BLOCKED: ReadonlySet<MiniProgramPrivacyMode> = new Set<MiniProgramPrivacyMode>([
  'local',
  'top-secret',
])

export class MiniProgramPrivacyNetworkBlockedError extends Error {
  readonly mode: MiniProgramPrivacyMode
  constructor(mode: MiniProgramPrivacyMode) {
    super(`数据网络在 ${mode} 隐私模式下已禁用`)
    this.name = 'MiniProgramPrivacyNetworkBlockedError'
    this.mode = mode
  }
}

export function isMiniProgramPrivacyNetworkBlockedError(
  err: unknown,
): err is MiniProgramPrivacyNetworkBlockedError {
  return err instanceof MiniProgramPrivacyNetworkBlockedError
}

export function getStoredPrivacyMode(): MiniProgramPrivacyMode {
  try {
    const raw = Taro.getStorageSync<string>(PRIVACY_STORAGE_KEY)
    if (raw === 'local' || raw === 'top-secret') return raw
  } catch {
    // 读取失败回退 standard
  }
  return 'standard'
}

export function setStoredPrivacyMode(mode: MiniProgramPrivacyMode): void {
  Taro.setStorageSync(PRIVACY_STORAGE_KEY, mode)
}

/**
 * 数据网络前置 assertion：命中敏感模式直接 throw，永不让请求出门。
 *
 * 调用者：utils/api/client.ts、utils/auth/refresh.ts、utils/api/auth.ts (wxLogin)
 */
export function assertMiniProgramDataNetworkAllowed(
  mode: MiniProgramPrivacyMode = getStoredPrivacyMode(),
): void {
  if (DATA_NETWORK_BLOCKED.has(mode)) {
    throw new MiniProgramPrivacyNetworkBlockedError(mode)
  }
}
