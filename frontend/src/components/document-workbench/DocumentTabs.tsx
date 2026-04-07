import { useDocumentWorkbenchStore } from './hooks/useDocumentWorkbenchStore'

export function DocumentTabs() {
  const { openTabs, activeDocumentId, setActiveDocument, closeDocument } = useDocumentWorkbenchStore()

  if (openTabs.length === 0) {
    return (
      <div className="border-b border-border px-4 py-3 text-sm text-muted-foreground">
        请选择左侧文档空间中的文档
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 overflow-x-auto border-b border-border px-4 py-2">
      {openTabs.map((tab) => {
        const active = tab.id === activeDocumentId

        return (
          <div
            key={tab.id}
            data-testid={`document-tab-${tab.id}`}
            className={`flex items-center gap-2 rounded-full border px-3 py-1 text-sm ${
              active
                ? 'border-primary/30 bg-primary/10 text-primary'
                : 'border-border bg-background text-muted-foreground'
            }`}
          >
            <button type="button" onClick={() => setActiveDocument(tab.id)}>
              {tab.title}
            </button>
            <button type="button" onClick={() => closeDocument(tab.id)} aria-label={`关闭${tab.title}`}>
              ×
            </button>
          </div>
        )
      })}
    </div>
  )
}
