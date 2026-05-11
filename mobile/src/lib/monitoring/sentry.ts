// -*- coding: utf-8 -*-
/**
 * Sentry Expo 初始化（P19-B / Mobile）
 *
 * - 优先使用 sentry-expo（已为 Expo 提供 wrappers + 源码 map）
 * - 如未安装则降级到纯 console 上报，避免 RN 启动时崩溃
 * - 指纹规则与 frontend / backend 对齐：[client_source, module, errType, fn]
 */
import Constants from 'expo-constants'

let _initialized = false
// 用 any 是因为 sentry-expo 在未安装时不应导致 TS 编译失败
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let SentryRef: any = null

export function initSentry(): boolean {
  if (_initialized) return true

  const dsn =
    process.env.EXPO_PUBLIC_SENTRY_DSN ||
    (Constants.expoConfig?.extra as Record<string, string> | undefined)?.sentryDsn

  if (!dsn) {
    return false
  }

  try {
    // 动态 require，避免未安装时 RN bundler 报错
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const Sentry = require('sentry-expo')
    Sentry.init({
      dsn,
      environment:
        process.env.EXPO_PUBLIC_SENTRY_ENVIRONMENT ||
        (__DEV__ ? 'development' : 'production'),
      enableInExpoDevelopment: false,
      debug: !!__DEV__,
      tracesSampleRate: parseFloat(
        process.env.EXPO_PUBLIC_SENTRY_TRACES_SAMPLE_RATE || '0.1',
      ),
      beforeSend(event: Record<string, unknown>) {
        try {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const exc = (event as any).exception?.values?.[0]
          if (exc) {
            const errType = exc.type || 'UnknownError'
            const frame = exc.stacktrace?.frames?.[exc.stacktrace.frames.length - 1]
            const mod = frame?.module || frame?.filename || 'unknown'
            const fn = frame?.function || 'anonymous'
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ;(event as any).fingerprint = ['mobile', mod, errType, fn]
          }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          ;(event as any).tags = {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ...((event as any).tags || {}),
            client_source: 'mobile',
          }
        } catch {
          /* swallow */
        }
        return event
      },
    })
    SentryRef = Sentry.Native || Sentry
    _initialized = true
    return true
  } catch (err) {
    // sentry-expo 未安装 → 降级
    // eslint-disable-next-line no-console
    console.warn('[monitoring] sentry-expo not installed, falling back to console:', err)
    return false
  }
}

export function captureException(err: unknown, ctx?: Record<string, unknown>): void {
  if (!_initialized || !SentryRef) {
    // eslint-disable-next-line no-console
    console.error('[monitoring] captureException', err, ctx)
    return
  }
  try {
    SentryRef.captureException(err, { extra: ctx })
  } catch {
    /* swallow */
  }
}

export function setUser(user: { id?: string; email?: string } | null): void {
  if (!_initialized || !SentryRef) return
  try {
    SentryRef.setUser(user)
  } catch {
    /* swallow */
  }
}
