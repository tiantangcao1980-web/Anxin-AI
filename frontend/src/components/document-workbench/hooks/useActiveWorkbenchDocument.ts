import { useMemo } from 'react'
import { useDocumentWorkbenchStore } from './useDocumentWorkbenchStore'

const KIND_LABEL: Record<'doc' | 'markdown' | 'txt' | 'pdf' | 'spreadsheet' | 'presentation', string> = {
  doc: '文档',
  markdown: 'Markdown',
  txt: '文本',
  pdf: 'PDF',
  spreadsheet: '表格',
  presentation: '演示',
}

export function useActiveWorkbenchDocument() {
  const { openTabs, activeDocumentId } = useDocumentWorkbenchStore()

  return useMemo(() => {
    const activeDocument = openTabs.find((item) => item.id === activeDocumentId) ?? null
    const kindLabel = activeDocument ? KIND_LABEL[activeDocument.kind] : '未打开'
    const contentLength = activeDocument?.content?.replace(/\s+/g, '').length ?? 0

    return {
      activeDocument,
      kindLabel,
      contentLength,
    }
  }, [activeDocumentId, openTabs])
}
