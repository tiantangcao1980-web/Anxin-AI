/**
 * PersonaChatPanel — 简化版 chat 面板
 *
 * 接 personasApi.chat（POST /personas/{id}/chat）。
 * 顶部：persona 简介条
 * 中部：消息列表（user + assistant 两种气泡）
 * 底部：textarea + 发送
 *
 * 注：故意只走通用 chat 端点；各 persona 专属 endpoint 由 CapabilityRunner 触发。
 */

import { useEffect, useRef, useState } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/components/ui/utils'

import type { Persona } from '@/lib/api/personas'
import { usePersonasStore } from '@/lib/store/personasStore'

interface Props {
  persona: Persona
}

export function PersonaChatPanel({ persona }: Props) {
  const thread = usePersonasStore((s) => s.getThread(persona.persona_id))
  const chat = usePersonasStore((s) => s.chat)
  const clearThread = usePersonasStore((s) => s.clearThread)
  const pending = usePersonasStore((s) => s.chatPending)

  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement | null>(null)

  // 切 persona 时清空当前 input（thread 是分线程的，由 store 保留）
  useEffect(() => {
    setInput('')
  }, [persona.persona_id])

  // 自动滚到最底
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [thread.history.length, pending])

  const send = async () => {
    const msg = input.trim()
    if (!msg || pending) return
    setInput('')
    try {
      await chat(persona.persona_id, msg)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '发送失败')
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* 顶部状态条 */}
      <div className="flex items-center justify-between gap-2 border-b border-border/40 bg-card/30 px-4 py-2 text-xs text-muted-foreground">
        <span>
          与 <span className="font-medium text-foreground">{persona.display_name}</span>{' '}
          对话 · {thread.history.length} 条
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1 text-xs"
          onClick={() => clearThread(persona.persona_id)}
          disabled={thread.history.length === 0 || pending}
        >
          <icons.RefreshCcw className="size-3" />
          清空
        </Button>
      </div>

      {/* 消息区 */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {thread.history.length === 0 && !pending && (
          <EmptyHint persona={persona} onPickSample={(s) => setInput(s)} />
        )}
        {thread.history.map((m, i) => (
          <ChatBubble
            key={i}
            role={m.role}
            content={m.content}
            personaEmoji={persona.emoji}
          />
        ))}
        {pending && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <icons.Loader2 className="size-3 animate-spin" />
            {persona.display_name} 正在思考……
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div className="border-t border-border/40 bg-card/30 p-3">
        <div className="flex items-end gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={`和 ${persona.display_name} 说点什么…… (Enter 发送，Shift+Enter 换行)`}
            rows={2}
            className="min-h-[60px] resize-none"
            disabled={pending}
          />
          <Button
            onClick={send}
            disabled={!input.trim() || pending}
            className="h-10 gap-1"
          >
            {pending ? <icons.Loader2 className="size-3.5 animate-spin" /> : <icons.Send className="size-3.5" />}
            发送
          </Button>
        </div>
        {!persona.is_implemented && (
          <p className="mt-2 text-[11px] text-amber-700 dark:text-amber-400">
            ⚠️ 该 persona 后端尚未实装（规划中），当前为前端 mock 占位应答。
          </p>
        )}
      </div>
    </div>
  )
}

interface BubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  personaEmoji: string
}

function ChatBubble({ role, content, personaEmoji }: BubbleProps) {
  const isUser = role === 'user'
  return (
    <div className={cn('flex gap-2', isUser && 'flex-row-reverse')}>
      <div
        className={cn(
          'flex size-8 shrink-0 items-center justify-center rounded-full text-base ring-1 ring-border/60',
          isUser ? 'bg-primary/10 text-primary' : 'bg-muted/60',
        )}
        aria-hidden
      >
        {isUser ? '🧑' : personaEmoji}
      </div>
      <div
        className={cn(
          'max-w-[78%] rounded-2xl px-3 py-2 text-sm leading-relaxed shadow-sm',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'border border-border/50 bg-card text-foreground',
        )}
      >
        <pre className="whitespace-pre-wrap break-words font-sans">{content}</pre>
      </div>
    </div>
  )
}

function EmptyHint({
  persona,
  onPickSample,
}: {
  persona: Persona
  onPickSample: (s: string) => void
}) {
  const samples = persona.capabilities.slice(0, 3).map((c) => `请帮我：${c.split('（')[0]}`)
  return (
    <div className="rounded-lg border border-dashed border-border/60 p-6 text-sm">
      <p className="font-medium text-foreground">和 {persona.display_name} 开始对话</p>
      <p className="mt-1 text-xs text-muted-foreground">{persona.description}</p>
      {samples.length > 0 && (
        <div className="mt-3 space-y-1.5">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
            试试这些提问
          </p>
          {samples.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onPickSample(s)}
              className="block w-full truncate rounded-md border border-border/40 bg-muted/30 px-2.5 py-1.5 text-left text-xs text-foreground/80 transition-colors hover:border-primary/40 hover:bg-muted/60"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
