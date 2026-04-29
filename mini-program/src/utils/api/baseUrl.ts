// -*- coding: utf-8 -*-
/**
 * API base URL 解析。
 *
 * Taro 的 defineConstants 在 webpack 打包时注入 `process.env.TARO_APP_API_BASE`。
 * 微信小程序生产环境必须把后端域名加入 request.legalDomain 白名单。
 */

declare const process: { env: Record<string, string | undefined> }

const FALLBACK_DEV = 'http://localhost:8001/api/v1'
const FALLBACK_PROD = 'https://api.anxinagent.com/api/v1'

export function resolveBaseUrl(): string {
  const fromEnv =
    (typeof process !== 'undefined' && process.env?.TARO_APP_API_BASE) || ''
  if (fromEnv) return fromEnv
  // weapp 编译时 NODE_ENV=production，h5 dev 时为 development
  const isProd =
    typeof process !== 'undefined' && process.env?.NODE_ENV === 'production'
  return isProd ? FALLBACK_PROD : FALLBACK_DEV
}
