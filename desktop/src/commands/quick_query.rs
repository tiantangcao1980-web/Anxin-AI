use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

pub const QUICK_QUERY_WINDOW_LABEL: &str = "quick-query";
pub const QUICK_QUERY_WINDOW_PATH: &str = "/desktop/quick-query";
pub const QUICK_QUERY_WINDOW_TITLE: &str = "安心快问";
pub const QUICK_QUERY_WINDOW_WIDTH: f64 = 420.0;
pub const QUICK_QUERY_WINDOW_HEIGHT: f64 = 540.0;

#[derive(Debug, Clone, PartialEq)]
pub struct QuickQueryWindowSpec {
    pub label: &'static str,
    pub path: &'static str,
    pub title: &'static str,
    pub width: f64,
    pub height: f64,
    pub decorations: bool,
    pub resizable: bool,
    pub always_on_top: bool,
    pub skip_taskbar: bool,
}

pub fn quick_query_window_spec() -> QuickQueryWindowSpec {
    QuickQueryWindowSpec {
        label: QUICK_QUERY_WINDOW_LABEL,
        path: QUICK_QUERY_WINDOW_PATH,
        title: QUICK_QUERY_WINDOW_TITLE,
        width: QUICK_QUERY_WINDOW_WIDTH,
        height: QUICK_QUERY_WINDOW_HEIGHT,
        decorations: false,
        resizable: false,
        always_on_top: true,
        skip_taskbar: true,
    }
}

fn focus_quick_query_window(window: &WebviewWindow) -> Result<(), String> {
    window.show().map_err(|err| err.to_string())?;
    window.center().map_err(|err| err.to_string())?;
    window.set_focus().map_err(|err| err.to_string())?;
    Ok(())
}

pub fn create_quick_query_window(app: &AppHandle) -> Result<WebviewWindow, String> {
    let spec = quick_query_window_spec();
    let builder = WebviewWindowBuilder::new(app, spec.label, WebviewUrl::App(spec.path.into()))
        .title(spec.title)
        .inner_size(spec.width, spec.height)
        .decorations(spec.decorations)
        .resizable(spec.resizable)
        .always_on_top(spec.always_on_top)
        .skip_taskbar(spec.skip_taskbar)
        .visible(true)
        .focused(true)
        .center();

    #[cfg(target_os = "macos")]
    let builder = builder.title_bar_style(tauri::TitleBarStyle::Overlay);

    builder.build().map_err(|err| err.to_string())
}

pub fn toggle_quick_query_window(app: &AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window(QUICK_QUERY_WINDOW_LABEL) {
        let is_visible = window.is_visible().unwrap_or(false);
        let is_focused = window.is_focused().unwrap_or(false);
        if is_visible && is_focused {
            window.hide().map_err(|err| err.to_string())?;
        } else {
            focus_quick_query_window(&window)?;
        }
        return Ok(());
    }

    create_quick_query_window(app).map(|_| ())
}

#[tauri::command]
pub async fn hide_quick_query_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window(QUICK_QUERY_WINDOW_LABEL) {
        window.hide().map_err(|err| err.to_string())?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{quick_query_window_spec, QUICK_QUERY_WINDOW_LABEL, QUICK_QUERY_WINDOW_PATH};

    #[test]
    fn quick_query_window_uses_dedicated_route_and_label() {
        let spec = quick_query_window_spec();

        assert_eq!(spec.label, QUICK_QUERY_WINDOW_LABEL);
        assert_eq!(spec.path, QUICK_QUERY_WINDOW_PATH);
        assert_eq!(spec.title, "安心快问");
    }

    #[test]
    fn quick_query_window_is_spotlight_sized_and_ephemeral() {
        let spec = quick_query_window_spec();

        assert_eq!(spec.width, 420.0);
        assert_eq!(spec.height, 540.0);
        assert!(!spec.decorations);
        assert!(!spec.resizable);
        assert!(spec.always_on_top);
        assert!(spec.skip_taskbar);
    }
}
