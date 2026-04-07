import { useEffect, useRef } from 'react'
import type { WorkbenchDocumentItem } from '../hooks/useDocumentWorkbenchStore'
import { useDocumentWorkbenchStore } from '../hooks/useDocumentWorkbenchStore'

interface RichDocumentAdapterProps {
  document: WorkbenchDocumentItem
}

export function RichDocumentAdapter({ document }: RichDocumentAdapterProps) {
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
    <section className="flex min-h-0 flex-1 flex-col">
      <header className="border-b border-border px-4 py-2 text-sm font-medium text-foreground">
        {document.title}
      </header>
      <div className="min-h-0 flex-1 overflow-auto bg-muted/20 p-6">
        <div className="mx-auto min-h-full max-w-3xl rounded-3xl bg-background p-4 shadow-sm">
          <textarea
            ref={textareaRef}
            className="min-h-[60vh] w-full resize-none bg-transparent p-4 text-sm text-foreground outline-none"
            value={document.content ?? ''}
            onChange={(event) => updateDocumentContent(document.id, event.target.value)}
          />
        </div>
      </div>
    </section>
  )
}
