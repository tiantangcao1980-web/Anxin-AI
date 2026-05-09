import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, Send, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { chatApi } from '@/lib/api'
import {
  getCurrentMode,
  hideQuickQueryWindow,
  isTauri,
  localLLMChat,
} from '@/lib/tauri-bridge'
import {
  QUICK_QUERY_AUTO_HIDE_MS,
  QUICK_QUERY_SYSTEM_PROMPT,
  normalizeQuickQueryInput,
  resolveLocalQuickQueryAnswer,
  shouldUseLocalQuickQuery,
} from './quickQueryModel'

type QuickQueryMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  meta?: string
}

type QuickQueryStatus = 'idle' | 'thinking' | 'done' | 'error'

function buildMessage(role: QuickQueryMessage['role'], content: string, meta?: string): QuickQueryMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    meta,
  }
}

export default function QuickQuery() {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const hideTimerRef = useRef<number | null>(null)
  const [input, setInput] = useState('')
  const [draftAnswer, setDraftAnswer] = useState('')
  const [messages, setMessages] = useState<QuickQueryMessage[]>([])
  const [status, setStatus] = useState<QuickQueryStatus>('idle')
  const [error, setError] = useState<string | null>(null)

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current !== null) {
      window.clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
  }, [])

  const requestHide = useCallback(() => {
    if (!isTauri()) return
    void hideQuickQueryWindow()
  }, [])

  const scheduleHide = useCallback(() => {
    if (!isTauri()) return
    clearHideTimer()
    hideTimerRef.current = window.setTimeout(() => {
      void hideQuickQueryWindow()
    }, QUICK_QUERY_AUTO_HIDE_MS)
  }, [clearHideTimer])

  useEffect(() => {
    inputRef.current?.focus()

    const handleWindowBlur = () => {
      requestHide()
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        requestHide()
      }
    }

    window.addEventListener('blur', handleWindowBlur)
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      clearHideTimer()
      window.removeEventListener('blur', handleWindowBlur)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [clearHideTimer, requestHide])

  const sendCloudQuickQuery = useCallback(async (question: string) => {
    let streamed = ''
    try {
      await chatApi.streamMessage(
        { content: question, mode: 'quick_query', agent_name: 'legal_assistant' },
        (event) => {
          const payload = event as typeof event & {
            content?: string
            full_content?: string
          }
          if (payload.type === 'content' && payload.content) {
            streamed += payload.content
            setDraftAnswer(streamed)
          }
          if (payload.type === 'done' && payload.full_content) {
            streamed = payload.full_content
            setDraftAnswer(streamed)
          }
        },
      )
    } catch {
      const response = await chatApi.sendMessage({
        content: question,
        mode: 'quick_query',
        agent_name: 'legal_assistant',
      })
      streamed = response.content
      setDraftAnswer(streamed)
    }

    return streamed.trim() || '已收到问题，但暂未生成可展示内容。'
  }, [])

  const handleSubmit = useCallback(async () => {
    const normalized = normalizeQuickQueryInput(input)
    if (!normalized.ok || status === 'thinking') {
      setError(normalized.ok ? null : normalized.error)
      return
    }

    clearHideTimer()
    setError(null)
    setStatus('thinking')
    setDraftAnswer('')
    setMessages((current) => [...current, buildMessage('user', normalized.value)])
    setInput('')

    try {
      const tauriRuntime = isTauri()
      const mode = tauriRuntime ? await getCurrentMode() : null
      let answer = ''
      let meta = '云端'

      if (shouldUseLocalQuickQuery(mode, tauriRuntime)) {
        const response = await localLLMChat(normalized.value, undefined, QUICK_QUERY_SYSTEM_PROMPT)
        const localAnswer = resolveLocalQuickQueryAnswer(response)
        if (!localAnswer.ok) {
          throw new Error(localAnswer.error)
        }
        answer = localAnswer.answer
        meta = `${localAnswer.source} · ${localAnswer.model}`
        setDraftAnswer(answer)
      } else {
        answer = await sendCloudQuickQuery(normalized.value)
      }

      setMessages((current) => [...current, buildMessage('assistant', answer, meta)])
      setDraftAnswer('')
      setStatus('done')
      scheduleHide()
    } catch (err) {
      setStatus('error')
      setDraftAnswer('')
      setError(err instanceof Error ? err.message : '快问暂时不可用')
    }
  }, [clearHideTimer, input, scheduleHide, sendCloudQuickQuery, status])

  return (
    <main className="flex h-screen min-h-[520px] flex-col bg-background text-foreground">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-background/95 px-3">
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold">安心快问</h1>
          <p className="truncate text-xs text-muted-foreground">桌面即时法律助手</p>
        </div>
        <Button variant="ghost" size="icon" onClick={requestHide} aria-label="关闭快问">
          <X className="h-4 w-4" />
        </Button>
      </header>

      <section className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {messages.length === 0 && !draftAnswer ? (
          <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
            输入问题后按回车发送
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((message) => (
              <article
                key={message.id}
                className={
                  message.role === 'user'
                    ? 'ml-8 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground'
                    : 'mr-8 rounded-md border border-border bg-muted/40 px-3 py-2 text-sm leading-relaxed'
                }
              >
                <p className="whitespace-pre-wrap break-words">{message.content}</p>
                {message.meta ? (
                  <p className="mt-2 text-[11px] text-muted-foreground">{message.meta}</p>
                ) : null}
              </article>
            ))}
            {draftAnswer ? (
              <article className="mr-8 rounded-md border border-border bg-muted/40 px-3 py-2 text-sm leading-relaxed">
                <p className="whitespace-pre-wrap break-words">{draftAnswer}</p>
              </article>
            ) : null}
          </div>
        )}
      </section>

      {error ? (
        <div className="mx-3 mb-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      ) : null}

      <footer className="shrink-0 border-t border-border bg-background p-3">
        <div className="flex items-end gap-2">
          <Textarea
            ref={inputRef}
            value={input}
            rows={2}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void handleSubmit()
              }
            }}
            placeholder="输入需要快速确认的问题"
            className="max-h-28 min-h-[48px] resize-none text-sm"
            disabled={status === 'thinking'}
          />
          <Button
            size="icon"
            onClick={() => void handleSubmit()}
            disabled={status === 'thinking' || !input.trim()}
            aria-label="发送快问"
          >
            {status === 'thinking' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </footer>
    </main>
  )
}
