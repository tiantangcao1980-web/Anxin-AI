import type { WorkbenchDocumentItem } from '../hooks/useDocumentWorkbenchStore'
import { MarkdownTextAdapter } from './MarkdownTextAdapter'
import { PresentationAdapter } from './PresentationAdapter'
import { PdfPreviewAdapter } from './PdfPreviewAdapter'
import { RichDocumentAdapter } from './RichDocumentAdapter'
import { SpreadsheetAdapter } from './SpreadsheetAdapter'

export function resolveWorkbenchAdapter(doc: WorkbenchDocumentItem) {
  switch (doc.kind) {
    case 'markdown':
    case 'txt':
      return MarkdownTextAdapter
    case 'doc':
      return RichDocumentAdapter
    case 'pdf':
      return PdfPreviewAdapter
    case 'spreadsheet':
      return SpreadsheetAdapter
    case 'presentation':
      return PresentationAdapter
    default:
      return MarkdownTextAdapter
  }
}
