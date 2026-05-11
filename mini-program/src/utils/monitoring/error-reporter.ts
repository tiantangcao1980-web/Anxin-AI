// -*- coding: utf-8 -*-
/**
 * 自实装错误上报（P19-B / Mini-Program）
 *
 * 微信/支付宝/字节小程序无 Sentry 官方 SDK，因此采用：
 *   1. Taro.onError —— 同步错误（render / 业务代码 throw）
 *   2. Taro.onUnhandledRejection —— Promise 链未处理 rejection
 *   3. POST 后端 /api/v1/client-errors（与 Web / Mobile 三端共享）
 *
 * 指纹规则（与 Web / Mobile / 后端 P19-A error_classifier 对齐）：
 *   [client_source='miniprogram', module(=路由 path), errType, firstFrame]
 *   后端 error_classifier 会再做一次归一化 hash，跨端聚合同一错误。
 */
import Taro from '@tarojs/taro'
import { resolveBaseUrl } from '../api/baseUrl'

const ENDPOINT = '/client-errors'
const MAX_BREADCRUMBS = 30
const breadcrumbs: Array<{ ts: number; category: string; data?: unknown }> = []

interface ErrorPayload {
  source: 'miniprogram'
  type: 'crash' | 'unhandled_rejection' | 'event' | 'perf'
  error?: string
  stack?: string
  context?: Record<string, unknown>
  breadcrumbs: typeof breadcrumbs
  ts: number
  fingerprint?: string[]
}

export function addBreadcrumb(category: string, data?: unknown): void {
  breadcrumbs.push({ ts: Date.now(), category, data })
  if (breadcrumbs.length > MAX_BREADCRUMBS) breadcrumbs.shift()
}

function currentRoute(): string {
  try {
    const pages = Taro.getCurrentPages?.() || []
    const top = pages[pages.length - 1]
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (top as any)?.route || 'unknown'
  } catch {
    return 'unknown'
  }
}

function buildFingerprint(errMsg: string, stack?: string): string[] {
  const route = currentRoute()
  // 简化 stack：取第一行有意义的文件:行
  let firstFrame = 'anonymous'
  if (stack) {
    const m = stack.split('\n').map((l) => l.trim()).find((l) => l && !l.startsWith('Error'))
    if (m) firstFrame = m.slice(0, 120)
  }
  // errType：尝试从 "TypeError: xxx" 提取
  const errType = (errMsg.match(/^([A-Z]\w*Error)/) || [, 'UnknownError'])[1] as string
  return ['miniprogram', route, errType, firstFrame]
}

function reportToBackend(payload: ErrorPayload): void {
  try {
    const base = resolveBaseUrl()
    Taro.request({
      url: `${base}${ENDPOINT}`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: payload,
      // 失败静默：不能因上报失败而阻断业务
      fail: () => {
        /* swallow */
      },
    })
  } catch {
    /* swallow */
  }
}

/**
 * 启动错误上报 —— 在 app.tsx 的 useLaunch 中调用一次
 */
export function setupErrorReporter(): void {
  try {
    Taro.onError((err: string) => {
      const payload: ErrorPayload = {
        source: 'miniprogram',
        type: 'crash',
        error: err,
        stack: err,
        context: { route: currentRoute() },
        breadcrumbs: [...breadcrumbs],
        ts: Date.now(),
        fingerprint: buildFingerprint(err, err),
      }
      reportToBackend(payload)
    })
  } catch {
    /* Taro.onError 在某些版本/平台不可用 */
  }

  try {
    // 微信基础库 2.10.0+ 支持
    Taro.onUnhandledRejection?.((res: { reason: unknown; promise: Promise<unknown> }) => {
      const reason = res?.reason
      const msg = reason instanceof Error ? reason.message : String(reason)
      const stack = reason instanceof Error ? reason.stack : undefined
      const payload: ErrorPayload = {
        source: 'miniprogram',
        type: 'unhandled_rejection',
        error: msg,
        stack,
        context: { route: currentRoute() },
        breadcrumbs: [...breadcrumbs],
        ts: Date.now(),
        fingerprint: buildFingerprint(msg, stack),
      }
      reportToBackend(payload)
    })
  } catch {
    /* swallow */
  }
}

/** 业务事件埋点（与 Web 端 customMetrics 同名约定） */
export function trackEvent(name: string, ctx?: Record<string, unknown>): void {
  addBreadcrumb('business', { name, ctx })
  reportToBackend({
    source: 'miniprogram',
    type: 'event',
    context: { name, ...(ctx || {}), route: currentRoute() },
    breadcrumbs: [...breadcrumbs],
    ts: Date.now(),
  })
}
