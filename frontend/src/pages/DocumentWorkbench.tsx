import { useEffect } from 'react'
import { DocumentWorkbenchShell } from '@/components/document-workbench/DocumentWorkbenchShell'
import { useDocumentWorkbenchStore } from '@/components/document-workbench/hooks/useDocumentWorkbenchStore'
import { useDocumentWorkspaceEntry } from '@/components/document-workbench/hooks/useDocumentWorkspaceEntry'

export default function DocumentWorkbench() {
  const { entryMode, sessionId, initialDocument } = useDocumentWorkspaceEntry()
  const openDocument = useDocumentWorkbenchStore((state) => state.openDocument)

  useEffect(() => {
    if (initialDocument) {
      openDocument(initialDocument)
    }
  }, [initialDocument, openDocument])

  return <DocumentWorkbenchShell entryMode={entryMode} sessionId={sessionId} />
}
