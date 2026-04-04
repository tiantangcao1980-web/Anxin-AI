mod commands;
mod models;
mod services;

use models::create_shared_state;
use tauri::{Emitter, Event, Listener, Manager};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let shared_state = create_shared_state();

    tauri::Builder::default()
        // ===== 官方插件注册 =====
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_sql::Builder::default().build())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_opener::init())
        // ===== 全局状态 =====
        .manage(shared_state.clone())
        // ===== IPC 命令注册 =====
        .invoke_handler(tauri::generate_handler![
            // 应用模式
            commands::app_mode::get_app_state,
            commands::app_mode::switch_mode,
            commands::app_mode::get_current_mode,
            commands::app_mode::get_backend_url,
            commands::app_mode::set_user_token,
            commands::app_mode::set_backend_url,
            commands::app_mode::update_unread_count,
            // 同步
            commands::sync::trigger_sync,
            commands::sync::get_sync_status,
            commands::sync::get_pending_sync_count,
            commands::sync::resolve_conflict,
            // 本地 LLM
            commands::local_llm::local_llm_chat,
            commands::local_llm::list_local_models,
            commands::local_llm::check_local_llm_status,
            // 认证
            commands::auth::biometric_authenticate,
            commands::auth::save_auth_token,
            commands::auth::clear_auth,
            commands::auth::is_authenticated,
            commands::auth::get_app_info,
        ])
        // ===== 应用初始化 =====
        .setup(move |app| {
            let handle = app.handle().clone();

            // 桌面端：创建系统托盘
            #[cfg(desktop)]
            {
                if let Err(e) = services::tray::create_tray(&handle) {
                    log::error!("系统托盘创建失败: {}", e);
                }
            }

            // 开发模式：打开 DevTools
            #[cfg(debug_assertions)]
            {
                if let Some(window) = app.get_webview_window("main") {
                    window.open_devtools();
                }
            }

            // 监听深度链接
            let handle_clone = handle.clone();
            app.listen("deep-link://new-url", move |event: Event| {
                log::info!("收到深度链接: {:?}", event.payload());
                // 通知前端处理深度链接
                let _ = handle_clone.emit("deep-link-received", event.payload());
            });

            // 启动控制面心跳（后台定时检查）
            let state_for_heartbeat = shared_state.clone();
            tauri::async_runtime::spawn(async move {
                let engine = services::sync_engine::SyncEngine::new(
                    state_for_heartbeat.clone(),
                    {
                        state_for_heartbeat.read().await.backend_url.clone()
                    },
                );

                loop {
                    let _ = engine.control_plane_heartbeat().await;
                    tokio::time::sleep(std::time::Duration::from_secs(60)).await;
                }
            });

            log::info!("安心法务客户端启动完成");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("安心法务客户端启动失败");
}
