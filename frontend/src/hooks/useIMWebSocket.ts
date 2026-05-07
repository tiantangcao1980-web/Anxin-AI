/**
 * useIMWebSocket - IM 即时通讯 WebSocket 单例连接
 *
 * 全局唯一连接，登录后自动建立，消息路由到 IMStore。
 * 自动重连：指数退避 1s -> 15s，最多 10 次。
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuthStore, useIMStore, useNotificationStore, type IMMessage } from '@/lib/store'
import { getAccessTokenSnapshot } from '@/lib/platform/storage'

// 模块级单例状态
let imSocket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectCount = 0
const MAX_RECONNECT = 10
export const IM_ACK_CURSOR_STORAGE_PREFIX = 'anxin_im_last_ack_message_id'

type AckSender = (messageId: string) => boolean

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

  const { addNotification } = useNotificationStore()

  // 保存 store 方法的引用，避免闭包过期
  const storeRef = useRef({
    addMessage,
    setTyping,
    clearTyping,
    recallMessage,
    updateReadReceipt,
    addNotification,
  })
  useEffect(() => {
    storeRef.current = {
      addMessage,
      setTyping,
      clearTyping,
      recallMessage,
      updateReadReceipt,
      addNotification,
    }
  }, [addMessage, setTyping, clearTyping, recallMessage, updateReadReceipt, addNotification])

  /**
   * 建立 WebSocket 连接
   */
  const connect = useCallback(() => {
    // 避免重复连接
    if (imSocket && imSocket.readyState <= WebSocket.OPEN) {
      return
    }

    const token = getAccessTokenSnapshot()
    if (!token) {
      console.warn('[IM WS] 无 token，跳过连接')
      return
    }

    // 通过 Vite 代理或当前页面地址构建 WebSocket URL
    // 开发环境：ws://localhost:3001/api/v1/im/ws（经由 Vite proxy 转发到后端）
    // 生产环境：根据当前域名自动构建
    const wsBase = import.meta.env.VITE_WS_URL
      || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
    const wsUrl = `${wsBase}/api/v1/im/ws`

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'auth', data: buildAuthPayload(token) }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'auth_ok') {
          setIsConnected(true)
          reconnectCount = 0
          console.info('[IM WS] 鉴权成功')
          return
        }
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

export function _routeMessage(
  data: Record<string, unknown>,
  store: {
    addMessage: (msg: IMMessage) => void
    setTyping: (convId: string, userId: string) => void
    clearTyping: (convId: string, userId: string) => void
    recallMessage: (messageId: string) => void
    updateReadReceipt: (convId: string, userId: string) => void
    addNotification: (item: any) => void
  },
  sendAck: AckSender = acknowledgeIncomingMessage
) {
  const type = data.type as string

  switch (type) {
    case 'message':
      routeIncomingMessage(data.message, store, sendAck)
      break

    case 'offline_messages':
      if (Array.isArray(data.messages)) {
        for (const message of data.messages) {
          routeIncomingMessage(message, store, sendAck)
        }
      }
      break

    case 'ack_ok': {
      const messageId = data.message_id as string
      if (messageId) {
        rememberIMLastAckMessageId(useAuthStore.getState().user?.id, messageId)
      }
      break
    }

    case 'typing': {
      const convId = data.conversation_id as string
      const userId = data.user_id as string
      if (convId && userId) {
        store.setTyping(convId, userId)
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

    case 'notification': {
      if (data.notification) {
        const notifStore = useNotificationStore.getState()
        notifStore.addNotification(data.notification as any)
        // 实时 toast 提示
        const n = data.notification as any
        const title = n.title || '新通知'
        const msg = n.message || ''
        const type = n.type || 'info'
        if (type === 'urgent' || type === 'warning') {
          // 使用动态 import 避免循环依赖
          import('sonner').then(({ toast }) => toast.warning(`${title}: ${msg}`, { duration: 5000 }))
        } else {
          import('sonner').then(({ toast }) => toast.info(title, { description: msg, duration: 4000 }))
        }
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

export function buildAuthPayload(token: string) {
  const lastAckMessageId = getIMLastAckMessageId(useAuthStore.getState().user?.id)
  if (!lastAckMessageId) {
    return { token }
  }
  return { token, last_ack_message_id: lastAckMessageId }
}

export function getIMLastAckMessageId(userId: string | null | undefined): string | null {
  if (!userId) return null
  try {
    return getLocalStorage()?.getItem(getAckCursorStorageKey(userId)) ?? null
  } catch {
    return null
  }
}

export function rememberIMLastAckMessageId(
  userId: string | null | undefined,
  messageId: string
): void {
  if (!userId || !messageId) return
  try {
    getLocalStorage()?.setItem(getAckCursorStorageKey(userId), messageId)
  } catch {
    // localStorage may be unavailable in privacy modes; ACK still reached the server.
  }
}

function routeIncomingMessage(
  message: unknown,
  store: { addMessage: (msg: IMMessage) => void },
  sendAck: AckSender
) {
  if (!isIMMessagePayload(message)) return
  store.addMessage(message)
  sendAck(message.id)
}

function acknowledgeIncomingMessage(messageId: string): boolean {
  if (!imSocket || imSocket.readyState !== WebSocket.OPEN) return false
  try {
    imSocket.send(JSON.stringify({ type: 'ack', message_id: messageId }))
    return true
  } catch {
    return false
  }
}

function isIMMessagePayload(value: unknown): value is IMMessage {
  if (!value || typeof value !== 'object') return false
  const message = value as { id?: unknown; conversation_id?: unknown }
  return typeof message.id === 'string' && typeof message.conversation_id === 'string'
}

function getAckCursorStorageKey(userId: string): string {
  return `${IM_ACK_CURSOR_STORAGE_PREFIX}:${userId}`
}

function getLocalStorage(): Storage | null {
  try {
    return typeof globalThis.localStorage === 'undefined' ? null : globalThis.localStorage
  } catch {
    return null
  }
}
