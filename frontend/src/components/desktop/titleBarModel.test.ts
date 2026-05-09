import { describe, expect, it } from 'vitest'

import {
  shouldRenderDesktopTitleBarControls,
  shouldToggleMaximizeFromTitleBarDoubleClick,
} from './titleBarModel'

describe('titleBarModel', () => {
  it('renders custom titlebar controls only for non-macOS Tauri desktops', () => {
    expect(shouldRenderDesktopTitleBarControls(true, 'tauri-windows')).toBe(true)
    expect(shouldRenderDesktopTitleBarControls(true, 'tauri-linux')).toBe(true)
    expect(shouldRenderDesktopTitleBarControls(true, 'tauri-macos')).toBe(false)
    expect(shouldRenderDesktopTitleBarControls(false, 'tauri-windows')).toBe(false)
    expect(shouldRenderDesktopTitleBarControls(true, 'web')).toBe(false)
  })

  it('allows double-click maximize only from the draggable titlebar surface', () => {
    expect(
      shouldToggleMaximizeFromTitleBarDoubleClick({
        isTauriRuntime: true,
        platform: 'tauri-windows',
        targetTagName: 'header',
      }),
    ).toBe(true)

    expect(
      shouldToggleMaximizeFromTitleBarDoubleClick({
        isTauriRuntime: true,
        platform: 'tauri-windows',
        targetTagName: 'button',
      }),
    ).toBe(false)

    expect(
      shouldToggleMaximizeFromTitleBarDoubleClick({
        isTauriRuntime: true,
        platform: 'tauri-windows',
        targetTagName: 'span',
        hasInteractiveAncestor: true,
      }),
    ).toBe(false)

    expect(
      shouldToggleMaximizeFromTitleBarDoubleClick({
        isTauriRuntime: true,
        platform: 'tauri-macos',
        targetTagName: 'header',
      }),
    ).toBe(false)
  })
})
