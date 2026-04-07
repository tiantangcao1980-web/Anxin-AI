import { DocumentTabs } from './DocumentTabs'
import { DocumentCanvas } from './DocumentCanvas'
import { WorkbenchRightPanel } from './WorkbenchRightPanel'
import { WorkbenchSidebar } from './WorkbenchSidebar'
import { WorkbenchStatusBar } from './WorkbenchStatusBar'
import { WorkbenchTopbar } from './WorkbenchTopbar'

interface DocumentWorkbenchShellProps {
  entryMode: 'library' | 'collaboration' | 'chat'
  sessionId?: string | null
}

export function DocumentWorkbenchShell({ entryMode, sessionId }: DocumentWorkbenchShellProps) {
  return (
    <div
      data-testid="document-workbench-shell"
      data-ui="page-shell"
      data-entry-mode={entryMode}
      data-session-id={sessionId ?? undefined}
      className="flex h-full min-h-0 flex-col bg-surface-2"
    >
      <div data-ui="page-header" className="border-b border-border/60 bg-surface-1 shadow-card">
        <WorkbenchTopbar entryMode={entryMode} />
      </div>
      <div className="flex min-h-0 flex-1">
        <WorkbenchSidebar entryMode={entryMode} />
        <main data-testid="document-workbench-canvas" data-ui="surface-card" className="min-w-0 flex-1 bg-surface-1">
          <DocumentTabs />
          <div className="h-[calc(100%-49px)]">
            <DocumentCanvas />
          </div>
        </main>
        <WorkbenchRightPanel entryMode={entryMode} sessionId={sessionId} />
      </div>
      <WorkbenchStatusBar />
    </div>
  )
}
