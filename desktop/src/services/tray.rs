#![allow(dead_code)]

use crate::models::{AppMode, SharedAppState};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager,
};

const TRAY_APP_NAME: &str = "安心智能助手";

fn tray_mode_label(mode: AppMode) -> &'static str {
    match mode {
        AppMode::TopSecret => "绝密模式",
        AppMode::Hybrid => "混合模式",
        AppMode::Cloud => "云端模式",
    }
}

fn tray_mode_tooltip(mode: AppMode) -> String {
    format!("{} - {}", TRAY_APP_NAME, tray_mode_label(mode))
}

/// 创建系统托盘
pub fn create_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let show = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
    let mode_secret = MenuItem::with_id(
        app,
        "mode_secret",
        tray_mode_label(AppMode::TopSecret),
        true,
        None::<&str>,
    )?;
    let mode_hybrid = MenuItem::with_id(
        app,
        "mode_hybrid",
        tray_mode_label(AppMode::Hybrid),
        true,
        None::<&str>,
    )?;
    let mode_cloud = MenuItem::with_id(
        app,
        "mode_cloud",
        tray_mode_label(AppMode::Cloud),
        true,
        None::<&str>,
    )?;
    let sep = PredefinedMenuItem::separator(app)?;
    let sync = MenuItem::with_id(app, "sync", "立即同步", true, None::<&str>)?;
    let sep2 = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, "quit", "退出安心智能助手", true, None::<&str>)?;
    let tooltip = tray_mode_tooltip(AppMode::Cloud);

    let menu = Menu::with_items(
        app,
        &[
            &show,
            &sep,
            &mode_secret,
            &mode_hybrid,
            &mode_cloud,
            &sep2,
            &sync,
            &PredefinedMenuItem::separator(app)?,
            &quit,
        ],
    )?;

    let _tray = TrayIconBuilder::with_id("main-tray")
        .tooltip(tooltip)
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(move |app, event| {
            let id = event.id.as_ref();
            match id {
                "show" => {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "mode_secret" => {
                    let app = app.clone();
                    tauri::async_runtime::spawn(async move {
                        switch_tray_mode(&app, AppMode::TopSecret).await;
                    });
                }
                "mode_hybrid" => {
                    let app = app.clone();
                    tauri::async_runtime::spawn(async move {
                        switch_tray_mode(&app, AppMode::Hybrid).await;
                    });
                }
                "mode_cloud" => {
                    let app = app.clone();
                    tauri::async_runtime::spawn(async move {
                        switch_tray_mode(&app, AppMode::Cloud).await;
                    });
                }
                "sync" => {
                    log::info!("从托盘触发手动同步");
                    // 通过事件通知前端执行同步
                    let _ = app.emit("tray-sync-requested", ());
                }
                "quit" => {
                    app.exit(0);
                }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            if let tauri::tray::TrayIconEvent::Click {
                button: tauri::tray::MouseButton::Left,
                button_state: tauri::tray::MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    Ok(())
}

/// 从托盘切换模式
async fn switch_tray_mode(app: &AppHandle, mode: AppMode) {
    let state = app.state::<SharedAppState>();
    {
        let mut s = state.write().await;
        s.mode = mode;
    }

    // 更新托盘 tooltip
    let tooltip = tray_mode_tooltip(mode);

    if let Some(tray) = app.tray_by_id("main-tray") {
        let _ = tray.set_tooltip(Some(&tooltip));
    }

    // 通知前端模式已切换
    let _ = app.emit("mode-changed", serde_json::json!({ "mode": mode }));
    log::info!("托盘切换模式: {}", mode);
}

/// 更新托盘未读消息数
#[allow(dead_code)]
pub fn update_tray_badge(app: &AppHandle, count: u32) {
    if let Some(tray) = app.tray_by_id("main-tray") {
        let tooltip = if count > 0 {
            format!("安心智能助手 - {} 条未读消息", count)
        } else {
            "安心智能助手".to_string()
        };
        let _ = tray.set_tooltip(Some(&tooltip));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_no_emoji(text: &str) {
        for emoji in ["🔒", "🔄", "☁", "☁️"] {
            assert!(
                !text.contains(emoji),
                "tray text should not depend on emoji glyphs: {text}"
            );
        }
    }

    #[test]
    fn tray_mode_labels_are_plain_text() {
        let labels = [
            (AppMode::TopSecret, "绝密模式"),
            (AppMode::Hybrid, "混合模式"),
            (AppMode::Cloud, "云端模式"),
        ];

        for (mode, expected) in labels {
            let label = tray_mode_label(mode);
            assert_eq!(label, expected);
            assert_no_emoji(label);
        }
    }

    #[test]
    fn tray_mode_tooltips_are_plain_text() {
        let tooltips = [
            (AppMode::TopSecret, "安心智能助手 - 绝密模式"),
            (AppMode::Hybrid, "安心智能助手 - 混合模式"),
            (AppMode::Cloud, "安心智能助手 - 云端模式"),
        ];

        for (mode, expected) in tooltips {
            let tooltip = tray_mode_tooltip(mode);
            assert_eq!(tooltip, expected);
            assert_no_emoji(&tooltip);
        }
    }
}
