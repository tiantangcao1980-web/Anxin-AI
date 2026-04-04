/**
 * Chat 消息类型定义
 *
 * 从 Chat.tsx 提取的共享类型，供多个组件/hooks 复用。
 */

import type { A2UIMessage } from '@/components/a2ui'

/** 引用来源 */
export interface CitationSource {
  id: string
  type: string
  title: string
  content_snippet?: string
  source?: string
  relevance_score?: number
  url?: string
}

/** 聊天消息 */
export interface Message {
  id: string
  type: 'user' | 'ai' | 'system' | 'clarification' | 'a2ui'
  content: string
  timestamp: Date
  agent?: string
  memory_id?: string
  feedback?: 'up' | 'down'
  attachment?: { type: 'file' | 'image'; name: string; size: string }
  metadata?: {
    isError?: boolean
    originalError?: string
    lastUserMessage?: string
    repair_type?: string
  }
  clarification?: {
    questions: { question: string; options: string[] }[]
    original_content: string
    readinessScore?: number
    filledSlots?: any[]
    missingElements?: string[]
    _prev_assessment?: any
    _prev_intent?: string
    _prev_round?: number
  }
  /** A2UI 结构化组件数据 */
  a2ui?: A2UIMessage
  /** RAG 引用来源 */
  sources?: CitationSource[]
  /** 后续引导建议 */
  suggestions?: string[]
}

/** 欢迎消息 */
export const WELCOME_MESSAGE: Message = {
  id: '1',
  type: 'system',
  content: '__WELCOME__',
  timestamp: new Date(),
}
