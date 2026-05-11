// -*- coding: utf-8 -*-
/**
 * Web Vitals 采集与上报（P19-B / Web 前端）
 *
 * 上报四个核心指标：
 *   - LCP (Largest Contentful Paint)   性能基线 < 2.5s
 *   - FID (First Input Delay)          性能基线 < 100ms（已被 INP 取代，仍保留）
 *   - INP (Interaction to Next Paint)  新核心指标，性能基线 < 200ms
 *   - CLS (Cumulative Layout Shift)    性能基线 < 0.1
 *   - TTFB (Time to First Byte)        辅助指标
 *
 * 上报策略：
 *   1. 优先发往 Sentry（Performance）
 *   2. 同时打到自实装端点 /api/v1/client-errors?metric=web-vital（便于自建分析）
 *   3. 用 sendBeacon 兜底，确保 unload 时不丢
 *
 * 字段约定（与 docs/v3/OBSERVABILITY_FRONTEND.md 对齐）：
 *   { name, value, rating, id, navigationType }
 */
import type { Metric } from 'web-vitals'
import { Sentry } from './sentry'

const ENDPOINT = '/api/v1/client-errors'

interface VitalPayload {
  source: 'web'
  type: 'web-vital'
  name: string
  value: number
  rating: 'good' | 'needs-improvement' | 'poor' | string
  id: string
  navigationType?: string
  url: string
  ts: number
}

function reportToBackend(payload: VitalPayload): void {
  try {
    const body = JSON.stringify(payload)
    if (typeof navigator !== 'undefined' && 'sendBeacon' in navigator) {
      const blob = new Blob([body], { type: 'application/json' })
      navigator.sendBeacon(ENDPOINT, blob)
      return
    }
    // 兜底
    fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    }).catch(() => {
      /* swallow */
    })
  } catch {
    /* swallow */
  }
}

function handleMetric(metric: Metric): void {
  const payload: VitalPayload = {
    source: 'web',
    type: 'web-vital',
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    id: metric.id,
    navigationType: (metric as Metric & { navigationType?: string }).navigationType,
    url: typeof window !== 'undefined' ? window.location.pathname : '',
    ts: Date.now(),
  }

  // 1) Sentry 自定义 measurement
  try {
    Sentry?.setMeasurement?.(metric.name, metric.value, 'millisecond')
  } catch {
    /* Sentry 未初始化时忽略 */
  }

  // 2) 后端聚合
  reportToBackend(payload)
}

/** 注册 Web Vitals 监听 —— 应用启动时调用一次即可 */
export async function initWebVitals(): Promise<void> {
  // 动态导入避免在不需要时增加首屏体积
  const mod = await import('web-vitals').catch(() => null)
  if (!mod) {
    // web-vitals 未安装时降级为 noop（在 CI 环境也不会炸）
    return
  }
  const { onCLS, onFID, onLCP, onTTFB, onINP } = mod
  onCLS(handleMetric)
  onFID(handleMetric)
  onLCP(handleMetric)
  onTTFB(handleMetric)
  onINP?.(handleMetric)
}
