// -*- coding: utf-8 -*-
/**
 * oauth-flow — expo-web-browser 包装,用于打开 OAuth 授权页 (P17-D)
 *
 * 移动端关键差异:
 *   - Web 在新窗口跳转;移动端通过 expo-web-browser 内嵌 SafariViewController /
 *     Chrome Custom Tabs 的方式打开,避免离开 App
 *   - 失败回退:如果运行环境没有 expo-web-browser (Web preview / 单测),
 *     fallback 到 console.log 以保证 tsc + 单元测试不依赖原生模块
 */

let cached: any = null

async function loadWebBrowser(): Promise<any> {
  if (cached !== null) return cached
  try {
    // 动态 require,以便不安装依赖时也能 build
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    cached = require('expo-web-browser')
  } catch {
    cached = false
  }
  return cached
}

export interface OAuthSessionResult {
  type: 'success' | 'cancel' | 'dismiss' | 'fallback'
  url?: string
}

/**
 * 打开 OAuth 授权页,等待用户在浏览器内完成回调。
 *
 * Mock 模式下: openAuthSessionAsync 立即返回,实际"完成"由
 * appAuthApi.completeConnect 在 1.5s 后回调模拟。
 */
export async function openAuthSession(
  authorizeUrl: string,
  returnUrl: string = 'anxin-mobile://oauth/callback',
): Promise<OAuthSessionResult> {
  const wb = await loadWebBrowser()
  if (!wb || typeof wb.openAuthSessionAsync !== 'function') {
    // 测试 / web fallback:不真正跳转
    if (typeof console !== 'undefined') {
      console.log('[oauth-flow:fallback] would open', authorizeUrl)
    }
    return { type: 'fallback' }
  }
  try {
    const result = await wb.openAuthSessionAsync(authorizeUrl, returnUrl)
    if (result?.type === 'success') {
      return { type: 'success', url: result.url }
    }
    if (result?.type === 'cancel') return { type: 'cancel' }
    return { type: 'dismiss' }
  } catch (e) {
    if (typeof console !== 'undefined') {
      console.warn('[oauth-flow] error', e)
    }
    return { type: 'dismiss' }
  }
}
