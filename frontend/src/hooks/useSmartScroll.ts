/**
 * 智能滚动 Hook
 *
 * 从 Chat.tsx 提取的滚动控制逻辑
 * 包含：自动滚动、用户上滚暂停、防抖滚动
 */

import { useCallback, useRef, useState } from 'react'

export function useSmartScroll() {
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [userScrolledUp, setUserScrolledUp] = useState(false)

  const scrollToBottom = useCallback((force = false) => {
    if (!force && userScrolledUp) return
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [userScrolledUp])

  const debouncedScrollToBottom = useCallback(() => {
    if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current)
    scrollTimerRef.current = setTimeout(() => {
      scrollToBottom()
    }, 100)
  }, [scrollToBottom])

  // 检测用户是否手动上滚
  const handleScroll = useCallback(() => {
    const container = messagesContainerRef.current
    if (!container) return
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100
    setUserScrolledUp(!isAtBottom)
  }, [])

  return {
    messagesContainerRef,
    messagesEndRef,
    userScrolledUp,
    setUserScrolledUp,
    scrollToBottom,
    debouncedScrollToBottom,
    handleScroll,
  }
}
