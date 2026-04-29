/**
 * usePersonaChat — 移动端 persona chat 状态 hook（mock 流式版）
 *
 * 真接入（P17-A 提供 personasApi/personasStore）后,会替换内部实现，
 * 但对外接口保持不变,屏幕代码无需改动。
 */

import { useCallback, useRef, useState } from 'react'
import {
  mockStreamChat,
  mockRunCapability,
} from '../api/__mocks__/personas.mock'
import type { ChatBubbleMessage } from '../../components/v3/personas-mobile/ChatBubble'
import type { PersonaCapability } from './registry'

let MSG_SEQ = 1
function nextId(prefix: string): string {
  MSG_SEQ += 1
  return `${prefix}-${Date.now()}-${MSG_SEQ}`
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

  const startStream = useCallback(
    (userText: string) => {
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

      mockStreamChat(
        personaId,
        { message: userText },
        {
          onToken: (chunk) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + chunk } : m,
              ),
            )
          },
          onDone: () => {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, pending: false } : m)),
            )
            setPending(false)
          },
          onError: (err) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: `❌ 出错: ${err.message}`, pending: false }
                  : m,
              ),
            )
            setPending(false)
          },
        },
      )
    },
    [personaId],
  )

  const send = useCallback(
    (text: string) => {
      if (!text.trim() || pending) return
      startStream(text.trim())
    },
    [pending, startStream],
  )

  const regenerate = useCallback(
    (_id: string) => {
      if (pending || !lastUserMsg.current) return
      // 简化：直接以最近一次 user 消息再发一次
      startStream(lastUserMsg.current)
    },
    [pending, startStream],
  )

  const triggerCapability = useCallback(
    async (cap: PersonaCapability) => {
      if (pending) return
      const userText = `[能力] ${cap.label}`
      const userMsg: ChatBubbleMessage = {
        id: nextId('u'),
        role: 'user',
        content: userText,
      }
      const assistantId = nextId('a')
      const assistantPending: ChatBubbleMessage = {
        id: assistantId,
        role: 'assistant',
        content: `正在调用「${cap.label}」...`,
        pending: true,
      }
      setMessages((prev) => [...prev, userMsg, assistantPending])
      setPending(true)
      try {
        const result = await mockRunCapability(personaId, cap.id)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: result.content, pending: false } : m,
          ),
        )
      } catch (e) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: `❌ 能力调用失败: ${e instanceof Error ? e.message : String(e)}`,
                  pending: false,
                }
              : m,
          ),
        )
      } finally {
        setPending(false)
      }
    },
    [pending, personaId],
  )

  const clear = useCallback(() => setMessages([]), [])

  return { messages, pending, send, triggerCapability, regenerate, clear }
}
