import { useActiveWorkbenchDocument } from './hooks/useActiveWorkbenchDocument'

export function WorkbenchStatusBar() {
  const { activeDocument, kindLabel, contentLength } = useActiveWorkbenchDocument()
  const modeLabel =
    activeDocument?.kind === 'spreadsheet'
      ? '表格'
      : activeDocument?.kind === 'presentation'
        ? '演示'
        : kindLabel

  return (
    <footer
      data-testid="document-workbench-statusbar"
      className="flex h-9 items-center justify-between border-t border-border bg-background px-4 text-xs text-muted-foreground"
    >
      <div className="flex items-center gap-3">
        <span>自动保存</span>
        <span>已同步</span>
        <span data-testid="workbench-mode-label">{modeLabel} 模式</span>
      </div>
      <div className="flex items-center gap-3">
        <span>{activeDocument ? `字数 ${contentLength}` : '字数 0'}</span>
        <span>缩放 100%</span>
      </div>
    </footer>
  )
}
