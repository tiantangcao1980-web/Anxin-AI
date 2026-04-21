/**
 * Chat 消息类型定义
 *
 * 从 Chat.tsx 提取的共享类型，供多个组件/hooks 复用。
 */

import type { A2UIMessage } from '@/components/a2ui'
import type { ThinkingStep } from '@/lib/store'

/**
 * 引用来源
 *
 * 来自后端 RAG / 知识库检索。字段在网络边界可能缺省，
 * 因此声明为可选；消费组件需要自行提供 UI 兜底。
 */
export interface CitationSource {
  id: string
  type: string
  title: string
  content_snippet?: string
  source?: string
  relevance_score?: number
  url?: string | null
}

export type { ThinkingStep }

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
    actionable?: 'retry' | 'switch_model'
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
  /** V2：本轮 AI 回答对应的思考过程（绑定到消息，而不是全局） */
  thinkingSteps?: ThinkingStep[]
}

/** 欢迎消息 */
export const WELCOME_MESSAGE: Message = {
  id: '1',
  type: 'system',
  content: '__WELCOME__',
  timestamp: new Date(),
}
