/**
 * useIMWebSocket - IM 即时通讯 WebSocket 单例连接
 *
 * 全局唯一连接，登录后自动建立，消息路由到 IMStore。
 * 自动重连：指数退避 1s -> 15s，最多 10 次。
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useIMStore } from '@/lib/store'

// 模块级单例状态
let imSocket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectCount = 0
const MAX_RECONNECT = 10

export function useIMWebSocket() {
  const [isConnected, setIsConnected] = useState(false)
  const intentionalClose = useRef(false)

  const {
    addMessage,
    setTyping,
    clearTyping,
    recallMessage,
    updateReadReceipt,
  } = useIMStore()

  // 保存 store 方法的引用，避免闭包过期
  const storeRef = useRef({
    addMessage,
    setTyping,
    clearTyping,
    recallMessage,
    updateReadReceipt,
  })
  useEffect(() => {
    storeRef.current = {
      addMessage,
      setTyping,
      clearTyping,
      recallMessage,
      updateReadReceipt,
    }
  }, [addMessage, setTyping, clearTyping, recallMessage, updateReadReceipt])

  /**
   * 建立 WebSocket 连接
   */
  const connect = useCallback(() => {
    // 避免重复连接
    if (imSocket && imSocket.readyState <= WebSocket.OPEN) {
      return
    }

    const token = localStorage.getItem('access_token')
    if (!token) {
      console.warn('[IM WS] 无 token，跳过连接')
      return
    }

    const wsBase = import.meta.env.VITE_WS_URL || 'ws://localhost:8003'
    const wsUrl = `${wsBase}/api/v1/im/ws?token=${encodeURIComponent(token)}`

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setIsConnected(true)
      reconnectCount = 0
      console.info('[IM WS] 连接成功')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        _routeMessage(data, storeRef.current)
      } catch (e) {
        console.error('[IM WS] 消息解析失败:', e)
      }
    }

    ws.onerror = () => {
      console.warn('[IM WS] 连接错误')
    }

    ws.onclose = (event) => {
      imSocket = null
      setIsConnected(false)

      if (intentionalClose.current) {
        intentionalClose.current = false
        return
      }

      // 自动重连
      if (event.code !== 1000 && reconnectCount < MAX_RECONNECT) {
        const delay = Math.min(1000 * Math.pow(2, reconnectCount), 15000)
        reconnectCount++
        console.info(
          `[IM WS] 断开，${delay / 1000}s 后第 ${reconnectCount} 次重连...`
        )
        reconnectTimer = setTimeout(() => {
          if (!imSocket) connect()
        }, delay)
      }
    }

    imSocket = ws
  }, [])

  /**
   * 主动断开连接
   */
  const disconnect = useCallback(() => {
    intentionalClose.current = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    reconnectCount = 0
    if (imSocket) {
      imSocket.close(1000, 'user disconnected')
      imSocket = null
    }
    setIsConnected(false)
  }, [])

  /**
   * 发送消息
   */
  const send = useCallback((data: Record<string, unknown>): boolean => {
    if (!imSocket || imSocket.readyState !== WebSocket.OPEN) {
      console.error('[IM WS] 未连接，无法发送')
      return false
    }
    try {
      imSocket.send(JSON.stringify(data))
      return true
    } catch {
      return false
    }
  }, [])

  return { isConnected, connect, disconnect, send }
}

// ===== 消息路由 =====

function _routeMessage(
  data: Record<string, unknown>,
  store: {
    addMessage: (msg: any) => void
    setTyping: (convId: string, userId: string) => void
    clearTyping: (convId: string, userId: string) => void
    recallMessage: (messageId: string) => void
    updateReadReceipt: (convId: string, userId: string) => void
  }
) {
  const type = data.type as string

  switch (type) {
    case 'message':
      if (data.message) {
        store.addMessage(data.message as any)
      }
      break

    case 'typing': {
      const convId = data.conversation_id as string
      const userId = data.user_id as string
      if (convId && userId) {
        store.setTyping(convId, userId)
        // 3 秒后自动清除输入状态
        setTimeout(() => store.clearTyping(convId, userId), 3000)
      }
      break
    }

    case 'read_receipt': {
      const convId = data.conversation_id as string
      const userId = data.user_id as string
      if (convId && userId) {
        store.updateReadReceipt(convId, userId)
      }
      break
    }

    case 'recall': {
      const messageId = data.message_id as string
      if (messageId) {
        store.recallMessage(messageId)
      }
      break
    }

    case 'error':
      console.error('[IM WS] 服务端错误:', data.message)
      break

    default:
      console.warn('[IM WS] 未知消息类型:', type)
  }
}
