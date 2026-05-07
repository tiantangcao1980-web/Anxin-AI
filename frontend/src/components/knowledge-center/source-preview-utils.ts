export interface RAGSource {
  id?: string
  doc_id?: string
  chunk_id?: string
  title?: string
  source?: string
  source_url?: string
  content_snippet?: string
  anchor_text?: string
  score?: number
}

export interface SourceDocument {
  id: string
  title: string
  content?: string
  source?: string
  source_url?: string
}

export interface SourceContentSegment {
  text: string
  highlighted: boolean
}

export const getSourceLabel = (source: RAGSource, index: number) =>
  source.title || source.source || `来源 ${index + 1}`

export const getSourceDocumentId = (source: RAGSource) => source.doc_id || source.id

export const getExternalSourceUrl = (source: RAGSource) =>
  !getSourceDocumentId(source) && source.source_url ? source.source_url : null

export function splitSourceContent(content: string, anchorText?: string): SourceContentSegment[] {
  const anchor = anchorText?.trim()
  const index = anchor ? content.indexOf(anchor) : -1

  if (!anchor || index < 0) {
    return [{ text: content, highlighted: false }]
  }

  return [
    { text: content.slice(0, index), highlighted: false },
    { text: anchor, highlighted: true },
    { text: content.slice(index + anchor.length), highlighted: false },
  ].filter(segment => segment.text.length > 0)
}
