import type { ReactNode } from 'react'
import * as HoverCard from '@radix-ui/react-hover-card'
import { FileText, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface CitationSource {
  title: string
  snippet?: string
  url?: string
  locator?: string
}

interface CitationPillProps {
  index: number
  source: CitationSource
  onOpen?: (source: CitationSource) => void
  className?: string
  children?: ReactNode
}

export function CitationPill({
  index,
  source,
  onOpen,
  className,
  children,
}: CitationPillProps) {
  return (
    <HoverCard.Root openDelay={120} closeDelay={80}>
      <HoverCard.Trigger asChild>
        <button
          type="button"
          onClick={() => onOpen?.(source)}
          className={cn(
            'inline-flex h-4 min-w-4 items-center justify-center px-1',
            'rounded-subtle bg-ai-citation-surface text-ai-citation',
            'text-[10px] font-medium leading-none align-super',
            'transition-colors duration-fast ease-standard',
            'hover:bg-ai-citation hover:text-ai-foreground',
            'focus-visible:outline-none focus-visible:shadow-focus-ring',
            className,
          )}
          aria-label={`引用 ${index}: ${source.title}`}
        >
          {children ?? index}
        </button>
      </HoverCard.Trigger>
      <HoverCard.Portal>
        <HoverCard.Content
          side="top"
          align="start"
          sideOffset={6}
          className={cn(
            'z-popover max-w-sm rounded-dd_lg border border-border bg-popover p-3',
            'shadow-elev-4 outline-none',
            'data-[state=open]:animate-suggestion-in',
          )}
        >
          <div className="flex items-start gap-2">
            <FileText className="mt-0.5 size-3.5 shrink-0 text-ai-citation" />
            <div className="min-w-0 flex-1">
              <div className="text-body-sm font-medium text-foreground truncate">
                {source.title}
              </div>
              {source.locator && (
                <div className="mt-0.5 text-caption text-foreground-tertiary">
                  {source.locator}
                </div>
              )}
              {source.snippet && (
                <p className="mt-1.5 text-caption leading-relaxed text-foreground-tertiary line-clamp-3">
                  {source.snippet}
                </p>
              )}
              {source.url && (
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className={cn(
                    'mt-2 inline-flex items-center gap-1 text-caption font-medium',
                    'text-ai-citation hover:underline',
                  )}
                >
                  查看原文
                  <ExternalLink className="size-3" />
                </a>
              )}
            </div>
          </div>
        </HoverCard.Content>
      </HoverCard.Portal>
    </HoverCard.Root>
  )
}
