#![allow(dead_code)]

use crate::models::{AppMode, SharedAppState};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager,
};

/// 创建系统托盘
pub fn create_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let show = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
    let mode_secret =
        MenuItem::with_id(app, "mode_secret", "🔒 绝密模式", true, None::<&str>)?;
    let mode_hybrid =
        MenuItem::with_id(app, "mode_hybrid", "🔄 混合模式", true, None::<&str>)?;
    let mode_cloud =
        MenuItem::with_id(app, "mode_cloud", "☁️ 云端模式", true, None::<&str>)?;
    let sep = PredefinedMenuItem::separator(app)?;
    let sync = MenuItem::with_id(app, "sync", "立即同步", true, None::<&str>)?;
    let sep2 = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, "quit", "退出安心法务", true, None::<&str>)?;

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
        .tooltip("安心法务 - 云端模式")
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
    let tooltip = match mode {
        AppMode::TopSecret => "安心法务 - 🔒 绝密模式",
        AppMode::Hybrid => "安心法务 - 🔄 混合模式",
        AppMode::Cloud => "安心法务 - ☁️ 云端模式",
    };

    if let Some(tray) = app.tray_by_id("main-tray") {
        let _ = tray.set_tooltip(Some(tooltip));
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
            format!("安心法务 - {} 条未读消息", count)
        } else {
            "安心法务".to_string()
        };
        let _ = tray.set_tooltip(Some(&tooltip));
    }
}
