/**
 * useChatScroll Hook
 * 管理聊天消息滚动
 */

import { useState, useCallback, useRef, useEffect } from 'react';

export interface UseChatScrollOptions {
  messagesContainerRef: React.RefObject<HTMLDivElement>;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  messages?: any[];
  isStreaming?: boolean;
}

export interface UseChatScrollReturn {
  userScrolledUp: boolean;
  scrollToBottom: (force?: boolean) => void;
  scrollToBottomSmooth: () => void;
}

export function useChatScroll(
  options: UseChatScrollOptions
): UseChatScrollReturn {
  const { messagesContainerRef, messagesEndRef, messages, isStreaming } = options;

  // 状态
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const scrollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * 检测用户是否主动向上滚动
   */
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      // 距底部 150px 以内认为用户没有向上滚动
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 150;
      setUserScrolledUp(!isNearBottom);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [messagesContainerRef]);

  /**
   * 滚动到底部
   */
  const scrollToBottom = useCallback((force = false) => {
    if (!force && userScrolledUp) return; // 尊重用户的滚动意图
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [userScrolledUp, messagesEndRef]);

  /**
   * 防抖滚动 — 流式内容更新时最多 200ms 触发一次
   */
  const debouncedScrollToBottom = useCallback(() => {
    if (userScrolledUp) return;

    if (scrollTimerRef.current) {
      clearTimeout(scrollTimerRef.current);
    }

    scrollTimerRef.current = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 200);
  }, [userScrolledUp, messagesEndRef]);

  /**
   * 平滑滚动到底部
   */
  const scrollToBottomSmooth = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messagesEndRef]);

  /**
   * 新消息到达时智能滚动
   */
  useEffect(() => {
    if (isStreaming) {
      debouncedScrollToBottom(); // 流式内容：防抖滚动
    } else if (messages && messages.length > 0) {
      scrollToBottom(); // 新消息完成：立即滚动（除非用户主动向上滚了）
    }
  }, [messages, isStreaming, scrollToBottom, debouncedScrollToBottom]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (scrollTimerRef.current) {
        clearTimeout(scrollTimerRef.current);
      }
    };
  }, []);

  return {
    userScrolledUp,
    scrollToBottom,
    scrollToBottomSmooth,
  };
}
