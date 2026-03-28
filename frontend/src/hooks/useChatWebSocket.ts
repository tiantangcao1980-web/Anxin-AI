/**
 * useChatWebSocket Hook
 * 管理 WebSocket 连接和消息处理
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useChatStore } from '@/lib/store';

export interface WebSocketMessageHandlers {
  onMessage?: (data: any) => void;
  onError?: () => void;
  onClose?: (event: CloseEvent) => void;
  onOpen?: () => void;
}

export interface UseChatWebSocketOptions {
  conversationId: string;
  autoConnect?: boolean;
  maxReconnectAttempts?: number;
}

export interface UseChatWebSocketReturn {
  // 状态
  isConnected: boolean;
  isConnecting: boolean;
  reconnectAttempts: number;

  // 操作
  connect: (conversationId: string) => WebSocket | null;
  disconnect: () => void;
  send: (data: any) => boolean;
  reconnect: () => void;

  // Refs (供外部使用)
  wsRef: React.MutableRefObject<WebSocket | null>;
}

export function useChatWebSocket(
  options: UseChatWebSocketOptions,
  handlers: WebSocketMessageHandlers = {}
): UseChatWebSocketReturn {
  const { conversationId, autoConnect = true, maxReconnectAttempts = 5 } = options;

  // 状态
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);
  const messageHandlerRef = useRef(handlers.onMessage);
  const errorHandlerRef = useRef(handlers.onError);
  const closeHandlerRef = useRef(handlers.onClose);
  const openHandlerRef = useRef(handlers.onOpen);

  // 更新 handlers refs
  useEffect(() => {
    messageHandlerRef.current = handlers.onMessage;
    errorHandlerRef.current = handlers.onError;
    closeHandlerRef.current = handlers.onClose;
    openHandlerRef.current = handlers.onOpen;
  }, [
    handlers.onMessage,
    handlers.onError,
    handlers.onClose,
    handlers.onOpen,
  ]);

  /**
   * 连接 WebSocket
   */
  const connect = useCallback((convId: string): WebSocket | null => {
    if (!convId) return null;

    setIsConnecting(true);

    // 构建 WebSocket URL
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/chat/ws/${convId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      setIsConnecting(false);
      setReconnectAttempts(0);
      openHandlerRef.current?.();
      console.info('[WebSocket] 连接成功');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        messageHandlerRef.current?.(data);
      } catch (e) {
        console.error('[WebSocket] 消息解析失败:', e);
      }
    };

    ws.onerror = () => {
      setIsConnecting(false);
      errorHandlerRef.current?.();
      console.warn('[WebSocket] 连接失败，聊天实时功能暂不可用');
    };

    ws.onclose = (event) => {
      wsRef.current = null;
      setIsConnected(false);
      setIsConnecting(false);

      // 如果是主动关闭，不重连
      if (intentionalCloseRef.current) {
        intentionalCloseRef.current = false;
        return;
      }

      // 非正常关闭 → 自动重连
      if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 15000);
        setReconnectAttempts((prev) => prev + 1);
        console.info(
          `[WebSocket] 断开，${delay / 1000}s 后尝试第 ${reconnectAttempts + 1} 次重连...`
        );

        reconnectTimerRef.current = setTimeout(() => {
          if (!wsRef.current) {
            connect(convId);
          }
        }, delay);
      } else {
        closeHandlerRef.current?.(event);
      }
    };

    wsRef.current = ws;
    return ws;
  }, [maxReconnectAttempts, reconnectAttempts]);

  /**
   * 断开连接
   */
  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    setReconnectAttempts(0);

    if (wsRef.current) {
      wsRef.current.close(1000, 'user disconnected');
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  /**
   * 发送消息
   */
  const send = useCallback((data: any): boolean => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('[WebSocket] 未连接，无法发送消息');
      return false;
    }

    try {
      wsRef.current.send(JSON.stringify(data));
      return true;
    } catch (e) {
      console.error('[WebSocket] 发送消息失败:', e);
      return false;
    }
  }, []);

  /**
   * 手动重连
   */
  const reconnect = useCallback(() => {
    disconnect();
    setReconnectAttempts(0);
    if (conversationId) {
      setTimeout(() => {
        connect(conversationId);
      }, 100);
    }
  }, [conversationId, disconnect, connect]);

  // 自动连接
  useEffect(() => {
    if (autoConnect && conversationId && !wsRef.current) {
      const ws = connect(conversationId);
      wsRef.current = ws;
    }

    return () => {
      // 清理
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      setReconnectAttempts(0);
      if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
        wsRef.current.close(1000, 'component cleanup');
      }
      wsRef.current = null;
    };
  }, [conversationId, autoConnect]); // 只在 conversationId 变化时重连

  return {
    // 状态
    isConnected,
    isConnecting,
    reconnectAttempts,

    // 操作
    connect,
    disconnect,
    send,
    reconnect,

    // Refs
    wsRef,
  };
}
