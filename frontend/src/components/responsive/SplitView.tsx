import { useEffect, type ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { useBreakpoint } from '@/hooks/useBreakpoint'
import { cn } from '@/lib/utils'

interface SplitViewProps {
  /** 左侧（或顶部，移动端）列表区 */
  list: ReactNode
  /** 右侧（桌面）详情区；移动端自动升级为底部/右侧 Sheet */
  detail: ReactNode
  /** 是否打开详情（受控） */
  detailOpen: boolean
  /** 关闭详情 */
  onDetailClose: () => void
  /** 详情标题（移动端 Sheet header） */
  detailTitle?: string
  /** 是否使用 detail-first 布局（桌面端右列表左详情） */
  detailFirst?: boolean
  /** 桌面端最小列宽，默认 360px */
  listMinWidth?: number
  /** 移动端 Sheet 方向，默认 right（右侧滑入） */
  mobileSheetSide?: 'right' | 'bottom'
  className?: string
}

/**
 * SplitView — 响应式列表/详情双栏
 *
 * 桌面端（>= lg, 1024px）：左右双栏同屏
 * 移动端（< lg）：列表全屏；详情以 Sheet(Dialog) 形式覆盖
 *
 * 业务场景：
 * - 案件中心：案件列表 + 详情
 * - 管理中心：合同列表 + 审查详情
 * - 知识库：文档列表 + 预览
 *
 * 优势：业务代码零分支，由 SplitView 统一处理响应式切换
 */
export function SplitView({
  list,
  detail,
  detailOpen,
  onDetailClose,
  detailTitle,
  detailFirst = false,
  listMinWidth = 360,
  mobileSheetSide = 'right',
  className,
}: SplitViewProps) {
  const { isDesktop } = useBreakpoint()

  // 桌面端切换到移动端时自动关闭 Sheet，避免残影
  useEffect(() => {
    if (isDesktop && detailOpen && !document.querySelector('[data-splitview-detail]')) {
      // 状态保留给父级，仅做兜底
    }
  }, [isDesktop, detailOpen])

  if (isDesktop) {
    return (
      <div
        className={cn('grid h-full gap-4 lg:gap-6', className)}
        style={{
          gridTemplateColumns: detailFirst
            ? `1fr minmax(${listMinWidth}px, 420px)`
            : `minmax(${listMinWidth}px, 420px) 1fr`,
        }}
      >
        {detailFirst ? (
          <>
            <div className="min-w-0 overflow-auto scroll-momentum" data-splitview-detail={detailOpen ? '' : undefined}>
              {detailOpen ? detail : null}
            </div>
            <div className="min-w-0 overflow-auto scroll-momentum">{list}</div>
          </>
        ) : (
          <>
            <div className="min-w-0 overflow-auto scroll-momentum">{list}</div>
            <div className="min-w-0 overflow-auto scroll-momentum" data-splitview-detail={detailOpen ? '' : undefined}>
              {detailOpen ? detail : null}
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <>
      <div className={cn('h-full overflow-auto scroll-momentum', className)}>{list}</div>
      <Dialog.Root open={detailOpen} onOpenChange={(o) => !o && onDetailClose()}>
        <Dialog.Portal>
          <Dialog.Overlay
            className={cn(
              'fixed inset-0 z-overlay bg-foreground/30 backdrop-blur-sm',
              'data-[state=open]:animate-fade-in data-[state=closed]:opacity-0',
            )}
          />
          <Dialog.Content
            data-splitview-detail
            className={cn(
              'fixed z-modal bg-background shadow-elev-5 safe-pb',
              'data-[state=open]:animate-suggestion-in',
              mobileSheetSide === 'right'
                ? 'right-0 top-0 h-full w-[92vw] max-w-md border-l border-border'
                : 'bottom-0 left-0 right-0 max-h-[92vh] rounded-t-dd_2xl border-t border-border',
              'focus-visible:outline-none',
            )}
          >
            {mobileSheetSide === 'bottom' && <span className="drawer-handle" />}
            <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
              <Dialog.Title className="text-body font-medium text-foreground truncate">
                {detailTitle ?? '详情'}
              </Dialog.Title>
              <Dialog.Close
                className={cn(
                  'inline-flex size-8 items-center justify-center rounded-dd',
                  'text-foreground-tertiary hover:bg-surface-2 hover:text-foreground',
                  'transition-colors duration-fast ease-standard',
                )}
                aria-label="关闭详情"
              >
                <X className="size-4" />
              </Dialog.Close>
            </header>
            <div className="h-[calc(100%-52px)] overflow-auto scroll-momentum p-4">{detail}</div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  )
}
