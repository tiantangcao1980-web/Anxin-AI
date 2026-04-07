import type { WorkbenchDocumentItem } from '../hooks/useDocumentWorkbenchStore'

interface PresentationAdapterProps {
  document: WorkbenchDocumentItem
}

const SLIDES = [
  { id: 'slide-1', title: '项目概览', body: '梳理项目背景、目标与关键里程碑。' },
  { id: 'slide-2', title: '风险提示', body: '聚焦条款风险、履约风险与合规关注点。' },
  { id: 'slide-3', title: '行动建议', body: '输出下一步审阅、补充材料与签约建议。' },
]

function parseSlides(content?: string) {
  if (!content?.trim()) return SLIDES

  const lines = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length === 0) return SLIDES

  return lines.map((line, index) => ({
    id: `slide-${index + 1}`,
    title: line,
    body: index === 0 ? '封面与目录概览。' : `${line} 相关内容轻量预览。`,
  }))
}

export function PresentationAdapter({ document }: PresentationAdapterProps) {
  const slides = parseSlides(document.content)

  return (
    <section data-testid="presentation-adapter" className="flex min-h-0 flex-1 bg-muted/20">
      <div className="w-52 border-r border-border bg-background/90 p-3">
        <div className="text-sm font-medium text-foreground">{document.title}</div>
        <div className="mt-3 space-y-2">
          {slides.map((slide, index) => (
            <div key={slide.id} className="rounded-xl border border-border bg-background px-3 py-2">
              <div className="text-xs text-muted-foreground">第 {index + 1} 页</div>
              <div className="mt-1 text-sm font-medium text-foreground">{slide.title}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="flex min-h-0 flex-1 items-center justify-center p-6">
        <div className="aspect-[16/9] w-full max-w-3xl rounded-[28px] border border-border bg-background p-10 shadow-sm">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">演示文稿</div>
          <div className="mt-6 text-3xl font-semibold text-foreground">{slides[0]?.title ?? document.title}</div>
          <div className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">{slides[0]?.body ?? '演示内容预览。'}</div>
        </div>
      </div>
    </section>
  )
}
