// -*- coding: utf-8 -*-
/**
 * Crash & 全局未处理异常上报（P19-B / Mobile）
 *
 * - JS unhandled rejection：通过 Promise 全局事件 + RN ErrorUtils 捕获
 * - Native crash：sentry-expo 自带 native 集成（initSentry 时启用）
 * - 同时打到自实装 /api/v1/client-errors（与 Web/MP 三端共享聚合通道）
 */
import { captureException } from './sentry'

// 后端约定：path 是 /api/v1/client-errors，apiBase 在 mobile/api/client.ts 已含 /api/v1，
// 但本模块在 React Native 树未挂载时也会被调用，故走绝对路径以避免 axios 上下文。
const ENDPOINT = '/client-errors'

interface CrashPayload {
  source: 'mobile'
  type: 'crash' | 'unhandled_rejection'
  error: string
  stack?: string
  context?: Record<string, unknown>
  ts: number
}

function reportToBackend(payload: CrashPayload): void {
  try {
    // 期望 EXPO_PUBLIC_API_BASE_URL 已经是 https://host/api/v1 ；本地缺省走 /api/v1
    const apiBase = process.env.EXPO_PUBLIC_API_BASE_URL || '/api/v1'
    const url = `${apiBase}${ENDPOINT}`
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(() => {
      /* 离线 / 后端 down 不再二次重试，避免风暴 */
    })
  } catch {
    /* swallow */
  }
}

/** 安装全局 crash handler —— 应在 initSentry 之后调用 */
export function setupCrashReporting(): void {
  // 1) Promise unhandled rejection
  // RN 提供的 HermesInternal / global.process 监听
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g: any = globalThis as any
  if (typeof g.addEventListener === 'function') {
    g.addEventListener('unhandledrejection', (event: { reason?: unknown }) => {
      const reason = event?.reason
      const err = reason instanceof Error ? reason : new Error(String(reason))
      captureException(err, { source: 'unhandledrejection' })
      reportToBackend({
        source: 'mobile',
        type: 'unhandled_rejection',
        error: err.message,
        stack: err.stack,
        ts: Date.now(),
      })
    })
  }

  // 2) RN ErrorUtils（捕获 native bridge 抛出 / 同步抛出的未捕获异常）
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ErrorUtils = (g.ErrorUtils || g.HermesInternal?.getRuntimeProperties?.()?.ErrorUtils) as
    | { setGlobalHandler: (h: (e: Error, isFatal?: boolean) => void) => void; getGlobalHandler: () => (e: Error, isFatal?: boolean) => void }
    | undefined
  if (ErrorUtils) {
    const prev = ErrorUtils.getGlobalHandler()
    ErrorUtils.setGlobalHandler((error: Error, isFatal?: boolean) => {
      captureException(error, { isFatal })
      reportToBackend({
        source: 'mobile',
        type: 'crash',
        error: error.message,
        stack: error.stack,
        context: { isFatal },
        ts: Date.now(),
      })
      // 调用前一个 handler，保留 RN 默认红屏（开发态）
      try {
        prev?.(error, isFatal)
      } catch {
        /* swallow */
      }
    })
  }
}
