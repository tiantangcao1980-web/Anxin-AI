/**
 * useGovernanceWS —— 订阅治理 dashboard 实时事件
 *
 * 用法：
 *   useGovernanceWS(ev => {
 *     if (ev.type.startsWith('ticket.')) refreshTickets()
 *     if (ev.type.startsWith('cookbook.')) refreshOverview()
 *     if (ev.type === 'audit') refreshTimeline()
 *   })
 *
 * 连接 /api/v1/governance/ws，首条消息发 token 完成认证；断线自动重连（指数退避）。
 */
import { useEffect, useRef } from 'react'
import { API_BASE_URL } from '@/lib/api'
import { getAccessTokenSnapshot } from '@/lib/platform/storage'

export interface GovernanceEvent {
  type: string                // ticket.created / confirm.granted / authz.decide / shadow.* / lifecycle.* / cookbook.*
  ts: string
  tenant_id?: string | null
  payload: Record<string, unknown>
}

/** 把 REST 的 API base 转换成 governance WS URL。导出仅为可测试性。 */
export function wsUrlFromApiBase(
  base: string = API_BASE_URL,
  origin?: { protocol: string; host: string },
): string {
  if (base.startsWith('http')) {
    return base.replace(/^http/, 'ws') + '/governance/ws'
  }
  // 相对路径：拼当前 origin
  const o = origin ?? (typeof window !== 'undefined'
    ? { protocol: window.location.protocol, host: window.location.host }
    : { protocol: 'http:', host: 'localhost' })
  const proto = o.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${o.host}${base}/governance/ws`
}

/** 指数退避：当前 delay * 2，clamp 到 [_, max]。导出仅为可测试性。 */
export function nextBackoff(currentDelay: number, max: number = 30_000): number {
  return Math.min(currentDelay * 2, max)
}

export function useGovernanceWS(onEvent: (ev: GovernanceEvent) => void): void {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    let ws: WebSocket | null = null
    let closed = false
    let retryDelay = 1000

    const connect = async () => {
      const token = await getAccessTokenSnapshot()
      if (!token) {
        // 未登录 → 暂不连接；后续若用户登录会通过组件重渲染重试
        return
      }
      try {
        ws = new WebSocket(wsUrlFromApiBase())
      } catch (e) {
        console.warn('[governance-ws] open failed', e)
        scheduleReconnect()
        return
      }
      ws.onopen = () => {
        ws?.send(JSON.stringify({ type: 'auth', token }))
      }
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data as string)
          if (data.type === 'ready') {
            retryDelay = 1000   // reset backoff
            return
          }
          if (data.type === 'error') {
            console.warn('[governance-ws] error:', data.message)
            return
          }
          handlerRef.current(data as GovernanceEvent)
        } catch (e) {
          console.warn('[governance-ws] parse', e)
        }
      }
      ws.onclose = () => {
        if (!closed) scheduleReconnect()
      }
      ws.onerror = (e) => {
        console.warn('[governance-ws] error', e)
        ws?.close()
      }
    }

    const scheduleReconnect = () => {
      if (closed) return
      const delay = retryDelay
      retryDelay = nextBackoff(retryDelay)
      setTimeout(() => { if (!closed) void connect() }, delay)
    }

    void connect()

    return () => {
      closed = true
      ws?.close()
    }
  }, [])
}
