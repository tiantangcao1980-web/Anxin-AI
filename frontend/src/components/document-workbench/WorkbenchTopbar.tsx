import { useActiveWorkbenchDocument } from './hooks/useActiveWorkbenchDocument'

interface WorkbenchTopbarProps {
  entryMode: 'library' | 'collaboration' | 'chat'
}

const ENTRY_MODE_LABEL: Record<WorkbenchTopbarProps['entryMode'], string> = {
  library: '智能协作 · 文档工作台',
  collaboration: '智能协作 · 在线协作模板',
  chat: '智能协作 · 智能工作台入口',
}

export function WorkbenchTopbar({ entryMode }: WorkbenchTopbarProps) {
  const { activeDocument, kindLabel } = useActiveWorkbenchDocument()

  return (
    <header
      data-testid="document-workbench-topbar"
      className="flex h-14 items-center justify-between border-b border-border bg-background px-4"
    >
      <div>
        <div className="text-sm font-semibold text-foreground">统一文档工作台</div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{ENTRY_MODE_LABEL[entryMode]}</span>
          <span>·</span>
          <span data-testid="workbench-active-title">{activeDocument?.title ?? '未打开文档'}</span>
          <span>·</span>
          <span>{kindLabel}</span>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>上传</span>
        <span>分享</span>
        <span>版本</span>
      </div>
    </header>
  )
}
