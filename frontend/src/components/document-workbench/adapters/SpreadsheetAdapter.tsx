import type { WorkbenchDocumentItem } from '../hooks/useDocumentWorkbenchStore'

interface SpreadsheetAdapterProps {
  document: WorkbenchDocumentItem
}

const SAMPLE_ROWS = [
  ['事项', '负责人', '状态'],
  ['合同初审', '张律师', '进行中'],
  ['风险补充', '李法务', '待确认'],
  ['定稿提交', '项目经理', '未开始'],
]

function parseSpreadsheetRows(content?: string) {
  if (!content?.trim()) return SAMPLE_ROWS

  const rows = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.split(/[,\t，]/).map((cell) => cell.trim()))
    .filter((row) => row.length > 0)

  return rows.length > 0 ? rows : SAMPLE_ROWS
}

export function SpreadsheetAdapter({ document }: SpreadsheetAdapterProps) {
  const rows = parseSpreadsheetRows(document.content)
  const columnCount = Math.max(...rows.map((row) => row.length), 1)

  return (
    <section data-testid="spreadsheet-adapter" className="flex min-h-0 flex-1 flex-col">
      <header className="border-b border-border px-4 py-2 text-sm font-medium text-foreground">
        {document.title}
      </header>
      <div className="min-h-0 flex-1 overflow-auto bg-muted/20 p-4">
        <div className="min-w-[680px] rounded-2xl border border-border bg-background shadow-sm">
          {rows.map((row, rowIndex) => (
            <div
              key={`${document.id}-${rowIndex}`}
              className="grid border-b border-border last:border-b-0"
              style={{ gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))` }}
            >
              {row.map((cell, cellIndex) => (
                <div
                  key={`${document.id}-${rowIndex}-${cellIndex}`}
                  className={`px-4 py-3 text-sm ${rowIndex === 0 ? 'bg-muted font-medium text-foreground' : 'text-muted-foreground'}`}
                >
                  {cell}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
