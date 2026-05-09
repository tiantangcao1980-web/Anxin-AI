import { closeCurrentWindow, isTauri, minimizeCurrentWindow, toggleMaximizeCurrentWindow } from '@/lib/tauri-bridge'
import { icons } from '@/lib/icons'
import {
  shouldRenderDesktopTitleBarControls,
  shouldToggleMaximizeFromTitleBarDoubleClick,
} from './titleBarModel'

function getDesktopPlatform(): string {
  if (typeof document === 'undefined') return 'web'
  return document.documentElement.getAttribute('data-platform') ?? 'web'
}

function getTitleBarTargetContext(target: EventTarget | null) {
  if (typeof Element === 'undefined' || !(target instanceof Element)) {
    return {}
  }

  return {
    targetTagName: target.tagName,
    hasInteractiveAncestor: Boolean(target.closest('a,button,input,select,textarea,[role="button"],[data-titlebar-control]')),
  }
}

export function shouldHandleDesktopTitleBarDoubleClick(target: EventTarget | null): boolean {
  return shouldToggleMaximizeFromTitleBarDoubleClick({
    isTauriRuntime: isTauri(),
    platform: getDesktopPlatform(),
    ...getTitleBarTargetContext(target),
  })
}

export function handleDesktopTitleBarDoubleClick(target: EventTarget | null): void {
  if (shouldHandleDesktopTitleBarDoubleClick(target)) {
    void toggleMaximizeCurrentWindow()
  }
}

export function DesktopTitleBarControls() {
  const platform = getDesktopPlatform()

  if (!shouldRenderDesktopTitleBarControls(isTauri(), platform)) {
    return null
  }

  return (
    <div
      aria-label="窗口控制"
      data-titlebar-control
      className="hidden shrink-0 items-center gap-0.5 border-l border-border/60 pl-2 md:flex"
    >
      <button
        type="button"
        aria-label="最小化"
        title="最小化"
        onClick={() => void minimizeCurrentWindow()}
        className="flex h-9 w-10 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground"
      >
        <icons.Minus className="h-4 w-4" />
      </button>
      <button
        type="button"
        aria-label="最大化"
        title="最大化"
        onClick={() => void toggleMaximizeCurrentWindow()}
        className="flex h-9 w-10 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground"
      >
        <icons.Maximize className="h-4 w-4" />
      </button>
      <button
        type="button"
        aria-label="关闭"
        title="关闭"
        onClick={() => void closeCurrentWindow()}
        className="flex h-9 w-10 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/90 hover:text-destructive-foreground"
      >
        <icons.Close className="h-4 w-4" />
      </button>
    </div>
  )
}
