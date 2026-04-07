import { useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import type { WorkbenchDocumentItem } from './useDocumentWorkbenchStore'

interface DocumentWorkspaceLocationState {
  entryMode?: 'library' | 'collaboration' | 'chat'
  sessionId?: string
  initialDocument?: {
    id?: string
    title?: string
    content?: string
    kind?: WorkbenchDocumentItem['kind']
    type?: 'document' | 'contract' | 'table' | 'code' | 'presentation' | 'spreadsheet' | 'slides'
    metadata?: WorkbenchDocumentItem['metadata']
  }
}

const WORKBENCH_ENTRY_STORAGE_KEY = 'document-workbench-entry'

export function useDocumentWorkspaceEntry() {
  const location = useLocation()
  const state = (location.state ?? {}) as DocumentWorkspaceLocationState
  const persistedState = useMemo<DocumentWorkspaceLocationState | null>(() => {
    if (typeof window === 'undefined') return null
    const raw = window.sessionStorage.getItem(WORKBENCH_ENTRY_STORAGE_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as DocumentWorkspaceLocationState
    } catch {
      return null
    }
  }, [])
  const entryState = state.initialDocument ? state : persistedState ?? state

  const initialDocument = useMemo<WorkbenchDocumentItem | null>(() => {
    if (!entryState.initialDocument) return null

    const raw = entryState.initialDocument
    const kind =
      raw.kind ??
      (raw.type === 'document' || raw.type === 'contract'
        ? 'doc'
        : raw.type === 'table' || raw.type === 'spreadsheet'
          ? 'spreadsheet'
          : raw.type === 'presentation' || raw.type === 'slides'
            ? 'presentation'
            : raw.type === 'code'
              ? 'txt'
            : 'markdown')

    return {
      id: raw.id ?? `entry-${Date.now()}`,
      title: raw.title ?? '未命名文档',
      content: raw.content ?? '',
      kind,
      metadata: raw.metadata,
    }
  }, [entryState.initialDocument])

  return {
    entryMode: entryState.entryMode ?? 'library',
    sessionId: entryState.sessionId ?? null,
    initialDocument,
  }
}
