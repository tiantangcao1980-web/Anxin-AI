import type { WorkbenchDocumentItem } from '../hooks/useDocumentWorkbenchStore'

interface PdfPreviewAdapterProps {
  document: WorkbenchDocumentItem
}

export function PdfPreviewAdapter({ document }: PdfPreviewAdapterProps) {
  return (
    <section
      data-testid="pdf-preview-adapter"
      className="flex min-h-0 flex-1 items-center justify-center bg-muted/20 p-6"
    >
      <div className="w-full max-w-2xl rounded-3xl border border-dashed border-border bg-background p-10 text-center">
        <div className="text-base font-semibold text-foreground">{document.title}</div>
        <div className="mt-2 text-sm text-muted-foreground">PDF 预览与批注区域</div>
      </div>
    </section>
  )
}
