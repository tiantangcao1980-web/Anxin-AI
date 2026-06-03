/**
 * usePersonaChat — 移动端 persona chat 状态 hook（真实接入版）。
 *
 * 走真实后端：`POST /api/v1/personas/{persona_id}/chat`
 * （依据：backend/src/api/routes/personas.py:101 chat_with_persona，
 *  10 个 persona 均经 PersonaRegistry.autoload 注册、可实例化）。
 *
 * 后端当前为「整段返回」（非 SSE），故这里不再做假 token 流，
 * 而是发请求 → pending → 整段渲染。对外接口保持不变，屏幕代码无需改动。
 */

import { useCallback, useRef, useState } from 'react'
import { chatWithPersona, type ChatHistoryItem } from '../api/personas'
import { ApiError } from '../api/client'
import type { ChatBubbleMessage } from '../../components/v3/personas-mobile/ChatBubble'
import type { PersonaCapability } from './registry'

let MSG_SEQ = 1
function nextId(prefix: string): string {
  MSG_SEQ += 1
  return `${prefix}-${Date.now()}-${MSG_SEQ}`
}

function errText(e: unknown): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error) return e.message
  return String(e)
}

export interface UsePersonaChatReturn {
  messages: ChatBubbleMessage[]
  pending: boolean
  send: (text: string) => void
  triggerCapability: (cap: PersonaCapability) => Promise<void>
  regenerate: (id: string) => void
  clear: () => void
}

export function usePersonaChat(personaId: string): UsePersonaChatReturn {
  const [messages, setMessages] = useState<ChatBubbleMessage[]>([])
  const [pending, setPending] = useState(false)
  const lastUserMsg = useRef<string>('')
  // 维护发往后端的对话历史（不含正在 pending 的助手占位）。
  const historyRef = useRef<ChatHistoryItem[]>([])

  const runChat = useCallback(
    async (userText: string) => {
      const userMsg: ChatBubbleMessage = {
        id: nextId('u'),
        role: 'user',
        content: userText,
      }
      const assistantId = nextId('a')
      const assistantMsg: ChatBubbleMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        pending: true,
      }
      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setPending(true)
      lastUserMsg.current = userText

      const historyForRequest = [...historyRef.current]
      try {
        const resp = await chatWithPersona(personaId, {
          message: userText,
          history: historyForRequest,
        })
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: resp.content, pending: false } : m,
          ),
        )
        historyRef.current = [
          ...historyForRequest,
          { role: 'user', content: userText },
          { role: 'assistant', content: resp.content },
        ]
      } catch (e) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `❌ 出错: ${errText(e)}`, pending: false }
              : m,
          ),
        )
      } finally {
        setPending(false)
      }
    },
    [personaId],
  )

  const send = useCallback(
    (text: string) => {
      if (!text.trim() || pending) return
      void runChat(text.trim())
    },
    [pending, runChat],
  )

  const regenerate = useCallback(
    (_id: string) => {
      if (pending || !lastUserMsg.current) return
      // 简化：以最近一次 user 消息再发一次（不重复写入历史里的上一次回答）。
      void runChat(lastUserMsg.current)
    },
    [pending, runChat],
  )

  const triggerCapability = useCallback(
    async (cap: PersonaCapability) => {
      if (pending) return
      // 能力触发 = 把该能力的 sample prompt 发往真实 /chat。
      // 后端尚无「按 capability_id 直接路由」的通用 endpoint，故复用通用对话；
      // 各 persona 专属结构化 endpoint（如 /personas/dd/investigate-company）
      // 需逐能力映射，留待后续 P17-E。
      await runChat(`[${cap.label}] ${cap.prompt}`)
    },
    [pending, runChat],
  )

  const clear = useCallback(() => {
    setMessages([])
    historyRef.current = []
    lastUserMsg.current = ''
  }, [])

  return { messages, pending, send, triggerCapability, regenerate, clear }
}
