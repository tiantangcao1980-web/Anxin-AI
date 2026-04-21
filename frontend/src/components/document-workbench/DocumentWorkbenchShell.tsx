import { useState } from 'react'
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
  // 所有入口都默认展开右侧面板：
  // - library：让用户一进入就能看到 AI 助手 / 属性 / 历史入口
  // - collaboration：协作成员与快照面板需要立即可见
  // - chat：从 Chat 页「查看完整文档」跳来时期望看到 AI 缺项补写面板
  const [showRightPanel, setShowRightPanel] = useState(true)

  return (
    <div
      data-testid="document-workbench-shell"
      data-ui="page-shell"
      data-entry-mode={entryMode}
      data-session-id={sessionId ?? undefined}
      className="flex h-full min-h-0 flex-col bg-surface-2"
    >
      <div data-ui="page-header" className="border-b border-border/60 bg-surface-1 shadow-card">
        <WorkbenchTopbar
          entryMode={entryMode}
          showRightPanel={showRightPanel}
          onToggleRightPanel={() => setShowRightPanel((v) => !v)}
        />
      </div>
      <div className="flex min-h-0 flex-1">
        <WorkbenchSidebar entryMode={entryMode} />
        <main data-testid="document-workbench-canvas" data-ui="surface-card" className="min-w-0 flex-1 bg-surface-1">
          <DocumentTabs />
          <div className="h-[calc(100%-49px)]">
            <DocumentCanvas />
          </div>
        </main>
        {showRightPanel && (
          <WorkbenchRightPanel entryMode={entryMode} sessionId={sessionId} />
        )}
      </div>
      <WorkbenchStatusBar />
    </div>
  )
}
