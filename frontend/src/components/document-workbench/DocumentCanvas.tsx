import { resolveWorkbenchAdapter } from './adapters'
import { useDocumentWorkbenchStore } from './hooks/useDocumentWorkbenchStore'

export function DocumentCanvas() {
  const { openTabs, activeDocumentId } = useDocumentWorkbenchStore()
  const activeDocument = openTabs.find((item) => item.id === activeDocumentId)

  if (!activeDocument) {
    return (
      <div className="flex h-full items-center justify-center px-6">
        <div className="w-full max-w-3xl rounded-3xl border border-dashed border-border/80 bg-background/80 p-8">
          <div className="text-lg font-semibold text-foreground">请从左侧打开文档</div>
          <div className="mt-2 text-sm text-muted-foreground">
            文档打开后会在这里显示内容，并支持后续的多标签切换。
          </div>
        </div>
      </div>
    )
  }

  const Adapter = resolveWorkbenchAdapter(activeDocument)

  return <Adapter document={activeDocument} />
}
