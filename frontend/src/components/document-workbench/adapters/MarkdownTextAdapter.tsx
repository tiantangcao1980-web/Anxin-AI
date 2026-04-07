import { useEffect, useRef } from 'react'
import type { WorkbenchDocumentItem } from '../hooks/useDocumentWorkbenchStore'
import { useDocumentWorkbenchStore } from '../hooks/useDocumentWorkbenchStore'

interface MarkdownTextAdapterProps {
  document: WorkbenchDocumentItem
}

export function MarkdownTextAdapter({ document }: MarkdownTextAdapterProps) {
  const updateDocumentContent = useDocumentWorkbenchStore((state) => state.updateDocumentContent)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    const handleLocate = (event: Event) => {
      const detail = (event as CustomEvent<{ documentId?: string; targetText?: string }>).detail
      if (!detail || detail.documentId !== document.id || !detail.targetText || !textareaRef.current) return
      const index = (document.content ?? '').indexOf(detail.targetText)
      textareaRef.current.focus()
      if (index >= 0) {
        textareaRef.current.setSelectionRange(index, index + detail.targetText.length)
      }
    }
    window.addEventListener('workbench:locate-content', handleLocate as EventListener)
    return () => window.removeEventListener('workbench:locate-content', handleLocate as EventListener)
  }, [document.content, document.id])

  return (
    <section data-testid="markdown-text-adapter" className="flex min-h-0 flex-1 flex-col">
      <header className="border-b border-border px-4 py-2 text-sm font-medium text-foreground">
        {document.title}
      </header>
      <textarea
        ref={textareaRef}
        className="min-h-0 flex-1 resize-none bg-transparent p-4 text-sm text-foreground outline-none"
        value={document.content ?? ''}
        onChange={(event) => updateDocumentContent(document.id, event.target.value)}
      />
    </section>
  )
}
