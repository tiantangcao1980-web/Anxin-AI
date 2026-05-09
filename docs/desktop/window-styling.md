# Desktop Window Styling

Status: code-level desktop chrome contract implemented; packaged visual evidence pending.

## Scope

The desktop workstation keeps one shared top navigation surface while adapting window chrome per platform:

- macOS: Tauri `titleBarStyle: "Overlay"` with native traffic lights. The top bar keeps a safe left inset so the native controls do not overlap the logo.
- Windows/Linux: the desktop runtime disables system decorations at startup and uses the app top bar as the draggable titlebar, with explicit minimize, maximize/restore, and close controls.
- Quick Query: the `quick-query` utility window stays undecorated and ephemeral by design.

## Implementation Contract

| Area | File | Contract |
|---|---|---|
| Main window config | `desktop/tauri.conf.json` | Main window keeps `titleBarStyle: "Overlay"`, hidden title, shadow, and traffic-light position for macOS. |
| Platform chrome | `desktop/src/lib.rs` | Windows/Linux call `set_decorations(false)` for the main window during setup; macOS keeps native traffic lights. |
| Drag region | `frontend/src/components/Layout.tsx` | The 60px fixed top bar has `data-tauri-drag-region` and double-click handling. |
| Controls | `frontend/src/components/desktop/TitleBar.tsx` | Non-macOS Tauri desktop renders minimize, maximize/restore, and close controls only. |
| Safety model | `frontend/src/components/desktop/titleBarModel.ts` | Controls render only for non-macOS Tauri desktops; double-click maximize ignores interactive targets. |
| Capabilities | `desktop/capabilities/default.json` | Window permissions include close, minimize, maximize, and toggle-maximize. |

## Verification

```bash
bash scripts/desktop-window-chrome-gate.sh
cd frontend && npm test -- titleBarModel.test.ts
cd frontend && npm exec tsc -- --noEmit
cd frontend && npm run lint
cd desktop && cargo check
```

## Pending Release Evidence

- macOS screenshot showing native traffic lights, safe logo inset, and draggable 60px titlebar.
- Windows 11 screenshot/video showing undecorated window, minimize/maximize/close controls, and double-click maximize/restore.
- Visual acceptance for vibrancy/acrylic or a documented decision to keep the current translucent app bar without native blur.
- Signed/notarized packaged runtime smoke.
