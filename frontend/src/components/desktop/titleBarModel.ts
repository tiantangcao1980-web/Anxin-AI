const INTERACTIVE_TAGS = new Set(['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'])

export interface TitleBarInteractionContext {
  isTauriRuntime: boolean
  platform: string | null | undefined
  targetTagName?: string | null
  hasInteractiveAncestor?: boolean
}

export function shouldRenderDesktopTitleBarControls(
  isTauriRuntime: boolean,
  platform: string | null | undefined,
): boolean {
  return isTauriRuntime && typeof platform === 'string' && platform.startsWith('tauri-') && platform !== 'tauri-macos'
}

export function shouldToggleMaximizeFromTitleBarDoubleClick(context: TitleBarInteractionContext): boolean {
  if (!shouldRenderDesktopTitleBarControls(context.isTauriRuntime, context.platform)) {
    return false
  }

  if (context.hasInteractiveAncestor) {
    return false
  }

  const tagName = context.targetTagName?.toUpperCase()
  return !tagName || !INTERACTIVE_TAGS.has(tagName)
}
