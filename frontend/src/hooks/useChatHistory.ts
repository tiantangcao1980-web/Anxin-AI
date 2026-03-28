/**
 * useChatHistory Hook
 * 管理对话历史消息
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { chatApi } from '@/lib/api';
import { v4 as uuidv4 } from 'uuid';

export interface CitationSource {
  id: string;
  type: string; // "law_article" | "case" | "knowledge" | "regulation"
  title: string;
  content_snippet: string;
  source: string;
  relevance_score: number;
  url?: string | null;
}

export interface Message {
  id: string;
  type: 'user' | 'ai' | 'system' | 'clarification';
  content: string;
  timestamp: Date;
  agent?: string;
  memory_id?: string;
  feedback?: 'up' | 'down';
  sources?: CitationSource[];
  attachment?: { type: 'file' | 'image'; name: string; size: string };
  metadata?: { isError?: boolean; originalError?: string; lastUserMessage?: string };
  clarification?: {
    questions: { question: string; options: string[] }[];
    original_content: string;
  };
}

const WELCOME_MESSAGE: Message = {
  id: '1',
  type: 'ai',
  content: '您好！我是您的 AI 法务助手。\n\n我可以帮助您审查合同、分析风险或提供法律建议。系统已启用**自我进化模式**，我会从每一次交互中学习。',
  timestamp: new Date(),
  agent: '法律顾问Agent',
};

export interface UseChatHistoryOptions {
  conversationId: string;
  autoLoad?: boolean;
}

export interface UseChatHistoryReturn {
  // 状态
  messages: Message[];
  historyLoaded: boolean;
  isLoadingHistory: boolean;

  // 操作
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  removeMessage: (id: string) => void;
  clearMessages: () => void;
  loadHistory: (conversationId: string) => Promise<void>;
  resetToWelcome: () => void;

  // 反馈
  submitFeedback: (messageId: string, rating: number) => Promise<boolean>;
}

export function useChatHistory(options: UseChatHistoryOptions): UseChatHistoryReturn {
  const { conversationId, autoLoad = true } = options;

  // 状态
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // 使用 ref 避免依赖循环
  const loadHistoryRef = useRef<((conversationId: string) => Promise<void>) | null>(null);

  /**
   * 加载对话历史
   */
  const loadHistory = useCallback(async (convId: string) => {
    if (!convId || historyLoaded) return;

    let cancelled = false;
    setIsLoadingHistory(true);

    try {
      const result = await chatApi.getHistory({
        conversation_id: convId,
        limit: 100
      });

      if (cancelled) return;

      if (result?.messages?.length > 0) {
        const hist: Message[] = result.messages.map((m: any) => {
          // 从消息内容中还原附件信息
          const attachMatch = m.content?.match(/^\[附件:\s*(.+?)\]\n?/);
          const attachment = attachMatch
            ? {
                type: /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(attachMatch[1])
                  ? 'image'
                  : ('file' as const),
                name: attachMatch[1].trim(),
                size: '',
              }
            : undefined;
          const displayContent = attachMatch
            ? m.content.replace(attachMatch[0], '').trim()
            : m.content;

          return {
            id: m.id || uuidv4(),
            type: m.role === 'user' ? 'user' : 'ai',
            content: displayContent || m.content,
            timestamp: new Date(m.created_at || Date.now()),
            agent: m.agent_name,
            attachment,
          };
        });

        setMessages((prev) => {
          const welcome = prev.length > 0 && prev[0].id === '1' ? [prev[0]] : [];
          return [...welcome, ...hist];
        });
      }
    } catch (e) {
      if (!cancelled) {
        console.debug('加载对话历史失败:', e);
      }
    } finally {
      if (!cancelled) {
        setHistoryLoaded(true);
        setIsLoadingHistory(false);
      }
    }

    // cleanup function is handled via the cancelled flag
  }, [historyLoaded]);

  /**
   * 添加消息
   */
  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: uuidv4(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
  }, []);

  /**
   * 更新消息
   */
  const updateMessage = useCallback((id: string, updates: Partial<Message>) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
    );
  }, []);

  /**
   * 删除消息
   */
  const removeMessage = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  /**
   * 清空消息
   */
  const clearMessages = useCallback(() => {
    setMessages([WELCOME_MESSAGE]);
    setHistoryLoaded(true);
  }, []);

  /**
   * 重置为欢迎消息
   */
  const resetToWelcome = useCallback(() => {
    setMessages([{ ...WELCOME_MESSAGE, id: uuidv4() }]);
    setHistoryLoaded(true);
    setIsLoadingHistory(false);
  }, []);

  /**
   * 提交反馈
   */
  const submitFeedback = useCallback(async (messageId: string, rating: number) => {
    const message = messages.find((m) => m.id === messageId);
    if (!message?.memory_id) return false;

    try {
      await chatApi.submitMemoryFeedback(message.memory_id, rating);
      updateMessage(messageId, {
        feedback: rating >= 4 ? 'up' : 'down',
      });
      return true;
    } catch {
      return false;
    }
  }, [messages, updateMessage]);

  // 自动加载历史
  useEffect(() => {
    if (autoLoad && conversationId && !historyLoaded) {
      loadHistory(conversationId);
    }
  }, [autoLoad, conversationId, historyLoaded, loadHistory]);

  // 保存最新的 loadHistory 到 ref
  useEffect(() => {
    loadHistoryRef.current = loadHistory;
  }, [loadHistory]);

  return {
    // 状态
    messages,
    historyLoaded,
    isLoadingHistory,

    // 操作
    addMessage,
    updateMessage,
    removeMessage,
    clearMessages,
    loadHistory: (convId: string) => loadHistoryRef.current?.(convId) || Promise.resolve(),
    resetToWelcome,

    // 反馈
    submitFeedback,
  };
}
