import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface MissingFieldItem {
  key: string
  label: string
  severity: 'high' | 'medium' | 'low'
  group: string
  suggestion: string
  handled?: boolean
}

export interface HandledMissingFieldRecord {
  key: string
  label: string
  action: '插入建议' | 'AI补写'
  handled_at: string
}

export interface DocumentAIMetadata {
  draft_mode?: '成稿' | '高可用草案' | '结构化草稿'
  completeness_score?: number | null
  validation_score?: number | null
  missing_fields?: MissingFieldItem[]
  handled_missing_fields?: HandledMissingFieldRecord[]
}

export interface WorkbenchDocumentItem {
  id: string
  title: string
  kind: 'doc' | 'markdown' | 'txt' | 'pdf' | 'spreadsheet' | 'presentation'
  content?: string
  metadata?: DocumentAIMetadata
}
interface DocumentWorkbenchState {
  activeSpace: 'recent' | 'mine' | 'shared' | 'project' | 'starred'
  openTabs: WorkbenchDocumentItem[]
  recentDocuments: WorkbenchDocumentItem[]
  activeDocumentId: string | null
  setActiveSpace: (space: DocumentWorkbenchState['activeSpace']) => void
  openDocument: (doc: WorkbenchDocumentItem) => void
  closeDocument: (id: string) => void
  setActiveDocument: (id: string) => void
  updateDocumentContent: (id: string, content: string) => void
  markMissingFieldHandled: (id: string, field: MissingFieldItem, action: HandledMissingFieldRecord['action']) => void
}

export const useDocumentWorkbenchStore = create<DocumentWorkbenchState>()(
  persist(
    (set) => ({
      activeSpace: 'mine',
      openTabs: [],
      recentDocuments: [],
      activeDocumentId: null,
      setActiveSpace: (space) => set({ activeSpace: space }),
      openDocument: (doc) =>
        set((state) => {
          const existing = state.openTabs.find((item) => item.id === doc.id)
          const openTabs = existing
            ? state.openTabs.map((item) => (item.id === doc.id ? { ...item, ...doc } : item))
            : [...state.openTabs, doc]
          const recentDocuments = [
            doc,
            ...state.recentDocuments.filter((item) => item.id !== doc.id),
          ].slice(0, 8)

          return {
            openTabs,
            recentDocuments,
            activeDocumentId: doc.id,
          }
        }),
      closeDocument: (id) =>
        set((state) => {
          const openTabs = state.openTabs.filter((item) => item.id !== id)
          const activeDocumentId =
            state.activeDocumentId === id ? openTabs[openTabs.length - 1]?.id ?? null : state.activeDocumentId

          return { openTabs, activeDocumentId }
        }),
      setActiveDocument: (id) => set({ activeDocumentId: id }),
      updateDocumentContent: (id, content) =>
        set((state) => ({
          openTabs: state.openTabs.map((item) => (item.id === id ? { ...item, content } : item)),
        })),
      markMissingFieldHandled: (id, field, action) =>
        set((state) => ({
          openTabs: state.openTabs.map((item) =>
            item.id === id
              ? {
                  ...item,
                  metadata: item.metadata
                    ? {
                        ...item.metadata,
                        missing_fields: (item.metadata.missing_fields ?? []).map((missingField) =>
                          missingField.key === field.key ? { ...missingField, handled: true } : missingField,
                        ),
                        handled_missing_fields: [
                          ...(item.metadata.handled_missing_fields ?? []).filter((record) => record.key !== field.key),
                          {
                            key: field.key,
                            label: field.label,
                            action,
                            handled_at: new Date().toISOString(),
                          },
                        ],
                      }
                    : item.metadata,
                }
              : item,
          ),
        })),
    }),
    {
      name: 'document-workbench-store',
      partialize: (state) => ({
        recentDocuments: state.recentDocuments,
      }),
    },
  ),
)
