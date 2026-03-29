use tauri::Manager;

// Tauri IPC commands
#[tauri::command]
fn get_app_info() -> serde_json::Value {
    serde_json::json!({
        "name": "安心法务",
        "version": env!("CARGO_PKG_VERSION"),
        "platform": std::env::consts::OS,
    })
}

#[tauri::command]
fn get_backend_url() -> String {
    std::env::var("ANXIN_BACKEND_URL")
        .unwrap_or_else(|_| "http://localhost:8001".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .invoke_handler(tauri::generate_handler![get_app_info, get_backend_url])
        .setup(|app| {
            #[cfg(debug_assertions)]
            {
                let window = app.get_webview_window("main").unwrap();
                window.open_devtools();
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("安心法务桌面端启动失败");
}
