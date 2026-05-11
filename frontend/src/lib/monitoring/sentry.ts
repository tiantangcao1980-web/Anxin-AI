// -*- coding: utf-8 -*-
/**
 * Sentry React 初始化（P19-B 三端可观测层 / Web 前端）
 *
 * 关键能力：
 *   - 错误捕获 + Performance Tracing
 *   - Session Replay（采样率受 env 控制，默认 10%）
 *   - tracePropagationTargets 与后端 OpenTelemetry traceparent 对齐
 *   - 错误指纹（fingerprint）使用 P19-A 后端 error_classifier 同样的
 *     "module + error_type + first_frame" 三元组规则，便于跨端聚合
 *
 * 注意：Sentry 仅在配置了 VITE_SENTRY_DSN 时启用，开发态默认关闭以免噪音。
 */
import * as Sentry from '@sentry/react'

export interface SentryInitOptions {
  /** 应用版本 / build sha，便于按 release 分组错误 */
  release?: string
}

let _initialized = false

export function initSentry(opts: SentryInitOptions = {}): boolean {
  if (_initialized) return true

  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined
  if (!dsn) {
    // 开发态/未配置 DSN：静默跳过
    return false
  }

  const environment = (import.meta.env.VITE_SENTRY_ENVIRONMENT as string) || 'development'
  const tracesSampleRate = parseFloat(
    (import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE as string) || '0.1',
  )
  const replaysSampleRate = parseFloat(
    (import.meta.env.VITE_SENTRY_REPLAYS_SAMPLE_RATE as string) || '0.1',
  )

  // tracePropagationTargets：与后端 service base URL 对齐，
  // 这样 fetch/XHR 自动注入 sentry-trace + baggage header，
  // 后端 OpenTelemetry middleware 可以串联 trace。
  const apiBase =
    (import.meta.env.VITE_API_BASE_URL as string) ||
    (import.meta.env.VITE_API_URL as string) ||
    '/api'

  Sentry.init({
    dsn,
    environment,
    release: opts.release,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate,
    replaysSessionSampleRate: replaysSampleRate,
    replaysOnErrorSampleRate: 1.0,
    tracePropagationTargets: [/^\//, apiBase, /anxinagent\.com/, /anxinfawu\.com/],
    // 与 P19-A 后端 error_classifier 的指纹规则保持一致：
    //   module + error_type + first_frame
    beforeSend(event) {
      try {
        const exc = event.exception?.values?.[0]
        if (exc) {
          const errType = exc.type || 'UnknownError'
          const firstFrame = exc.stacktrace?.frames?.[exc.stacktrace.frames.length - 1]
          const module = firstFrame?.module || firstFrame?.filename || 'unknown'
          const fn = firstFrame?.function || 'anonymous'
          event.fingerprint = ['frontend-web', module, errType, fn]
        }
        // 附加客户端来源标识，后端聚类时可区分三端
        event.tags = { ...(event.tags || {}), client_source: 'web' }
      } catch {
        // fingerprint 计算失败不应阻断上报
      }
      return event
    },
  })

  _initialized = true
  return true
}

export function captureException(err: unknown, ctx?: Record<string, unknown>): void {
  if (!_initialized) {
    // 未启用 Sentry 时降级到 console，避免静默吞错
    // eslint-disable-next-line no-console
    console.error('[monitoring] captureException', err, ctx)
    return
  }
  Sentry.captureException(err, { extra: ctx })
}

export function setUser(user: { id?: string; email?: string; username?: string } | null): void {
  if (!_initialized) return
  Sentry.setUser(user)
}

export { Sentry }
