// -*- coding: utf-8 -*-
/**
 * 小程序性能采集（P19-B / Mini-Program）
 *
 * 使用 Taro.getPerformance API（微信基础库 2.11.0+），采集：
 *   - appLaunch / firstRender / firstPaint
 *   - route navigation 耗时
 *
 * 采样后 POST 到 /api/v1/client-errors（type='perf'），与 Web 端 web-vital 通道一致。
 */
import Taro from '@tarojs/taro'
import { resolveBaseUrl } from '../api/baseUrl'

interface PerfPayload {
  source: 'miniprogram'
  type: 'perf'
  entries: Array<{ name: string; entryType: string; startTime: number; duration: number }>
  route: string
  ts: number
}

function reportPerf(payload: PerfPayload): void {
  try {
    Taro.request({
      url: `${resolveBaseUrl()}/client-errors`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: payload,
      fail: () => {
        /* swallow */
      },
    })
  } catch {
    /* swallow */
  }
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

export function setupPerfReporter(): void {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const perf: any = (Taro as any).getPerformance?.()
    if (!perf) return
    const observer = perf.createObserver?.((list: { getEntries: () => unknown[] }) => {
      const raw = list.getEntries() as Array<{
        name: string
        entryType: string
        startTime: number
        duration: number
      }>
      if (!raw?.length) return
      reportPerf({
        source: 'miniprogram',
        type: 'perf',
        entries: raw.map((e) => ({
          name: e.name,
          entryType: e.entryType,
          startTime: e.startTime,
          duration: e.duration,
        })),
        route: currentRoute(),
        ts: Date.now(),
      })
    })
    observer?.observe?.({ entryTypes: ['render', 'script', 'navigation', 'loadPackage'] })
  } catch {
    /* getPerformance 在 H5 / 老基础库不可用 */
  }
}
