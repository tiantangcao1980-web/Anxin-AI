mod commands;
mod models;
mod services;

use models::{create_shared_state, SharedAppState};
use serde::Serialize;
use serde_json::Value;
use std::io::Write;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::webview::PageLoadEvent;
use tauri::{AppHandle, Emitter, Event, Listener, Manager, State};

#[derive(Debug, Serialize)]
pub struct DesktopRuntimeSelfTest {
    pub app: &'static str,
    pub local_db_url: &'static str,
    pub migration_count: usize,
    pub migration_versions: Vec<i64>,
    pub required_tables_present: Vec<&'static str>,
    pub sync_retry_schema_present: bool,
    pub sqlite_security: DesktopSQLiteSecuritySelfTest,
}

#[derive(Debug, Serialize)]
pub struct DesktopSQLiteSecuritySelfTest {
    pub encrypted: bool,
    pub keyring_backed: bool,
    pub release_blocking: bool,
    pub reason: &'static str,
}

#[derive(Clone, Copy, Debug, Default)]
pub struct DesktopRunOptions {
    pub runtime_smoke_exit_after_ms: Option<u64>,
    pub runtime_ui_smoke_timeout_ms: Option<u64>,
}

struct DesktopRuntimeSmokeState {
    runtime_ui_smoke_enabled: AtomicBool,
}

impl DesktopRuntimeSmokeState {
    fn new(runtime_ui_smoke_enabled: bool) -> Self {
        Self {
            runtime_ui_smoke_enabled: AtomicBool::new(runtime_ui_smoke_enabled),
        }
    }
}

impl DesktopRunOptions {
    pub fn runtime_smoke(exit_after_ms: u64) -> Self {
        Self {
            runtime_smoke_exit_after_ms: Some(exit_after_ms),
            runtime_ui_smoke_timeout_ms: None,
        }
    }

    pub fn runtime_ui_smoke(timeout_ms: u64) -> Self {
        Self {
            runtime_smoke_exit_after_ms: None,
            runtime_ui_smoke_timeout_ms: Some(timeout_ms),
        }
    }
}

pub fn desktop_runtime_self_test() -> DesktopRuntimeSelfTest {
    let migrations = services::local_db::sqlite_migrations();
    let init_sql = services::local_db::build_init_sql();
    let required_tables = [
        "offline_tasks",
        "app_settings",
        "sync_log",
        "local_messages",
        "local_documents",
        "local_cases",
        "local_contracts",
        "local_artifacts",
    ];

    DesktopRuntimeSelfTest {
        app: "anxin-legal-desktop",
        local_db_url: services::local_db::LOCAL_DB_URL,
        migration_count: migrations.len(),
        migration_versions: migrations
            .iter()
            .map(|migration| migration.version)
            .collect(),
        required_tables_present: required_tables
            .into_iter()
            .filter(|table| init_sql.contains(&format!("CREATE TABLE IF NOT EXISTS {table}")))
            .collect(),
        sync_retry_schema_present: init_sql.contains("next_retry_at DATETIME")
            && init_sql.contains("needs_human BOOLEAN DEFAULT 0"),
        sqlite_security: DesktopSQLiteSecuritySelfTest {
            encrypted: services::secure_db::security_contract().encrypted,
            keyring_backed: services::secure_db::security_contract().keyring_backed,
            release_blocking: services::secure_db::security_contract().release_blocking,
            reason: services::secure_db::security_contract().reason,
        },
    }
}

pub fn desktop_runtime_self_test_json() -> Result<String, serde_json::Error> {
    serde_json::to_string_pretty(&desktop_runtime_self_test())
}

pub fn desktop_sync_code_smoke_json() -> Result<String, String> {
    let report = services::sync_engine::desktop_sync_code_smoke_report()?;
    serde_json::to_string_pretty(&report)
        .map_err(|err| format!("无法序列化 desktop sync code smoke 报告: {err}"))
}

pub fn desktop_sync_loopback_smoke_json() -> Result<String, String> {
    let report = services::sync_engine::desktop_sync_loopback_smoke_report()?;
    serde_json::to_string_pretty(&report)
        .map_err(|err| format!("无法序列化 desktop sync loopback smoke 报告: {err}"))
}

pub fn desktop_secure_db_installed_profile_smoke_json() -> Result<String, String> {
    let path = std::env::var("ANXIN_DESKTOP_DB_PATH")
        .map_err(|_| "ANXIN_DESKTOP_DB_PATH must be set for installed-profile smoke".to_string())?;
    let report = services::secure_db::installed_profile_smoke(std::path::Path::new(&path))?;
    serde_json::to_string_pretty(&report)
        .map_err(|err| format!("无法序列化 installed-profile smoke 报告: {err}"))
}

pub fn desktop_secure_db_performance_smoke_json() -> Result<String, String> {
    let path = std::env::var("ANXIN_DESKTOP_DB_PATH")
        .map_err(|_| "ANXIN_DESKTOP_DB_PATH must be set for performance smoke".to_string())?;
    let report = services::secure_db::performance_smoke(std::path::Path::new(&path))?;
    serde_json::to_string_pretty(&report)
        .map_err(|err| format!("无法序列化 performance smoke 报告: {err}"))
}

pub fn delete_desktop_secure_db_smoke_key() -> Result<(), String> {
    services::secure_db::delete_keyring_entry()
}

fn load_desktop_runtime_config(handle: &AppHandle, shared_state: &SharedAppState) {
    match services::runtime_config::load_for_app(handle) {
        Ok(Some(config)) => {
            let mode = config.mode;
            let backend_url = config.backend_url.clone();
            tauri::async_runtime::block_on(async {
                let mut state = shared_state.write().await;
                config.apply_to_state(&mut state);
            });
            log::info!("桌面运行配置已加载: mode={mode}, backend_url={backend_url}");
        }
        Ok(None) => {
            log::info!("未找到桌面运行配置，使用默认运行配置");
        }
        Err(error) => {
            log::warn!("桌面运行配置加载失败，使用默认运行配置: {error}");
        }
    }
}

fn start_remote_control_safe_probe_daemon(shared_state: &SharedAppState) {
    let config = match services::remote_control_host::build_host_daemon_config_from_env() {
        Ok(Some(config)) => config,
        Ok(None) => return,
        Err(error) => {
            log::warn!("移动远控 host 后台 safe-probe daemon 未启动: {error}");
            return;
        }
    };
    let state = shared_state.clone();

    tauri::async_runtime::spawn(async move {
        let client = match services::remote_control_host::build_http_client() {
            Ok(client) => client,
            Err(error) => {
                log::warn!("移动远控 host 后台 safe-probe daemon 未启动: {error}");
                return;
            }
        };

        match services::remote_control_host::run_remote_control_host_daemon(
            &client, &state, &config,
        )
        .await
        {
            Ok(summary) => {
                log::info!(
                    "移动远控 host 后台 safe-probe daemon 已完成: cycles={}, claimed={}, completed={}, failed={}, unsupported={}, stopped_reason={}",
                    summary.cycles,
                    summary.claimed,
                    summary.completed,
                    summary.failed,
                    summary.unsupported,
                    summary.stopped_reason
                );
            }
            Err(error) => {
                log::warn!("移动远控 host 后台 safe-probe daemon 已停止: {error}");
            }
        }
    });
}

fn exit_runtime_smoke(handle: &AppHandle, code: i32) -> ! {
    let _ = std::io::stdout().flush();
    let _ = std::io::stderr().flush();
    handle.exit(code);
    std::process::exit(code);
}

fn desktop_runtime_ui_smoke_payload_ready(payload: &Value) -> bool {
    let platform_ready = payload
        .get("platform")
        .and_then(Value::as_str)
        .is_some_and(|platform| platform.starts_with("tauri-"));
    let has_root = payload
        .get("hasRoot")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let root_child_count = payload
        .get("rootChildCount")
        .and_then(Value::as_u64)
        .unwrap_or(0);
    let has_title = payload
        .get("title")
        .and_then(Value::as_str)
        .is_some_and(|title| !title.is_empty());

    has_root && root_child_count > 0 && platform_ready && has_title
}

#[cfg(any(target_os = "windows", target_os = "linux"))]
fn apply_platform_window_chrome(app: &tauri::App) {
    if let Some(window) = app.get_webview_window("main") {
        if let Err(error) = window.set_decorations(false) {
            log::warn!("桌面自绘标题栏启用失败: {error}");
        }
    }
}

#[cfg(not(any(target_os = "windows", target_os = "linux")))]
fn apply_platform_window_chrome(_app: &tauri::App) {}

fn complete_desktop_runtime_ui_smoke(handle: &AppHandle, payload: &Value) -> ! {
    println!("desktop runtime UI smoke response: {payload}");
    println!("desktop runtime UI smoke exiting: frontend response received");
    exit_runtime_smoke(handle, 0);
}

#[tauri::command]
fn desktop_runtime_ui_smoke_report(
    app: AppHandle,
    state: State<'_, DesktopRuntimeSmokeState>,
    payload: Value,
) -> Result<(), String> {
    if !state.runtime_ui_smoke_enabled.load(Ordering::Relaxed) {
        return Err("desktop runtime UI smoke is not enabled".to_string());
    }

    if desktop_runtime_ui_smoke_payload_ready(&payload) {
        complete_desktop_runtime_ui_smoke(&app, &payload);
    }

    println!("desktop runtime UI smoke observed: {payload}");
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    run_with_options(DesktopRunOptions::default());
}

pub fn run_with_options(options: DesktopRunOptions) {
    let shared_state = create_shared_state();
    let runtime_smoke_exit_after_ms = options.runtime_smoke_exit_after_ms;
    let runtime_ui_smoke_timeout_ms = options.runtime_ui_smoke_timeout_ms;
    let runtime_ui_smoke_enabled = runtime_ui_smoke_timeout_ms.is_some();
    let runtime_ui_smoke_page_load_completed = Arc::new(AtomicBool::new(false));
    let runtime_ui_smoke_page_load_completed_for_handler =
        Arc::clone(&runtime_ui_smoke_page_load_completed);

    tauri::Builder::default()
        .on_page_load(move |webview, payload| {
            if !runtime_ui_smoke_enabled || !matches!(payload.event(), PageLoadEvent::Finished) {
                return;
            }
            if runtime_ui_smoke_page_load_completed_for_handler.swap(true, Ordering::SeqCst) {
                return;
            }

            let app = webview.app_handle().clone();
            let report = serde_json::json!({
                "pageLoadFinished": true,
                "url": payload.url().as_str(),
                "webviewLabel": webview.label(),
                "windowLabel": webview.window().label(),
            });
            complete_desktop_runtime_ui_smoke(&app, &report);
        })
        // ===== 官方插件注册 =====
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        // 持久化窗口位置/尺寸：让用户关掉再开还能回到原位
        .plugin(tauri_plugin_window_state::Builder::new().build())
        // ===== 全局状态 =====
        .manage(shared_state.clone())
        .manage(DesktopRuntimeSmokeState::new(
            runtime_ui_smoke_timeout_ms.is_some(),
        ))
        // ===== IPC 命令注册 =====
        .invoke_handler(tauri::generate_handler![
            desktop_runtime_ui_smoke_report,
            // 应用模式
            commands::app_mode::get_app_state,
            commands::app_mode::switch_mode,
            commands::app_mode::get_current_mode,
            commands::app_mode::get_backend_url,
            commands::app_mode::set_user_token,
            commands::app_mode::set_backend_url,
            commands::app_mode::list_workstation_profiles,
            commands::app_mode::create_workstation_profile,
            commands::app_mode::update_workstation_profile,
            commands::app_mode::delete_workstation_profile,
            commands::app_mode::apply_workstation_profile,
            commands::app_mode::update_unread_count,
            // 同步
            commands::sync::trigger_sync,
            commands::sync::get_sync_status,
            commands::sync::get_pending_sync_count,
            commands::sync::resolve_conflict,
            // 移动远控桌面 host
            commands::remote_control::remote_control_confirm_pairing,
            commands::remote_control::remote_control_claim_commands,
            commands::remote_control::remote_control_report_command_status,
            commands::remote_control::remote_control_run_host_cycle,
            commands::remote_control::remote_control_run_host_poll,
            commands::quick_query::hide_quick_query_window,
            commands::file_drop::queue_file_drop_paths,
            // 本地 LLM
            commands::local_llm::local_llm_chat,
            commands::local_llm::get_local_llm_config,
            commands::local_llm::set_default_local_model,
            commands::local_llm::list_local_models,
            commands::local_llm::check_local_llm_status,
            // 本机通知
            commands::native_notification::preview_desktop_notification,
            commands::native_notification::send_desktop_notification,
            // CLI
            commands::cli::cli_execute,
            commands::cli::cli_create_key,
            commands::cli::cli_list_keys,
            // 离线任务
            commands::offline_tasks::submit_offline_task,
            commands::offline_tasks::get_queue_stats,
            commands::offline_tasks::flush_offline_queue,
            commands::offline_tasks::push_harness_artifacts,
            commands::offline_tasks::pull_harness_artifacts,
            // 安全本地 SQLCipher
            commands::secure_db::secure_sql_execute,
            commands::secure_db::secure_sql_select,
            commands::secure_db::secure_db_reset_local_data,
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
            load_desktop_runtime_config(&handle, &shared_state);
            start_remote_control_safe_probe_daemon(&shared_state);
            apply_platform_window_chrome(app);

            // 桌面端：创建系统托盘 + 注册全局快捷键
            #[cfg(desktop)]
            {
                if let Err(e) = services::tray::create_tray(&handle) {
                    log::error!("系统托盘创建失败: {}", e);
                }

                // 全局快捷键：Cmd+Shift+Space (macOS) / Ctrl+Shift+Space (Win/Linux)
                // 呼出/隐藏独立的快问窗口，主窗口保持当前工作上下文不被打断。
                use tauri_plugin_global_shortcut::{
                    Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState,
                };
                #[cfg(target_os = "macos")]
                let summon_shortcut =
                    Shortcut::new(Some(Modifiers::SUPER | Modifiers::SHIFT), Code::Space);
                #[cfg(not(target_os = "macos"))]
                let summon_shortcut =
                    Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::Space);

                if let Err(e) = app.global_shortcut().on_shortcut(
                    summon_shortcut,
                    move |app, _shortcut, event| {
                        if event.state() == ShortcutState::Pressed {
                            let app = app.clone();
                            std::thread::spawn(move || {
                                if let Err(error) =
                                    commands::quick_query::toggle_quick_query_window(&app)
                                {
                                    log::error!("快问窗口切换失败: {error}");
                                }
                            });
                        }
                    },
                ) {
                    log::error!("全局快捷键注册失败: {}", e);
                } else {
                    log::info!("全局快捷键已注册: Cmd/Ctrl+Shift+Space");
                }
            }

            // 开发模式：打开 DevTools
            #[cfg(debug_assertions)]
            {
                if runtime_smoke_exit_after_ms.is_none() && runtime_ui_smoke_timeout_ms.is_none() {
                    if let Some(window) = app.get_webview_window("main") {
                        window.open_devtools();
                    }
                }
            }

            // 监听深度链接
            let handle_clone = handle.clone();
            app.listen("deep-link://new-url", move |event: Event| {
                log::info!("收到深度链接: {:?}", event.payload());
                // 通知前端处理深度链接
                let _ = handle_clone.emit("deep-link-received", event.payload());
            });

            if let Some(timeout_ms) = runtime_ui_smoke_timeout_ms {
                let request_handle = handle.clone();
                tauri::async_runtime::spawn(async move {
                    let interval_ms = 500;
                    let mut elapsed_ms = 0;

                    while elapsed_ms < timeout_ms {
                        if let Some(window) = request_handle.get_webview_window("main") {
                            if let Err(error) = window.eval(
                                r#"
(() => {
  const root = document.getElementById('root');
  const bodyText = (document.body?.innerText || '').trim();
  const payload = {
    bodyTextLength: bodyText.length,
    hasRoot: Boolean(root),
    platform: document.documentElement.getAttribute('data-platform'),
    rootChildCount: root ? root.childElementCount : 0,
    title: document.title,
    hasTauriInvoke: Boolean(window.__TAURI_INTERNALS__ && typeof window.__TAURI_INTERNALS__.invoke === 'function')
  };
  if (payload.hasTauriInvoke) {
    window.__TAURI_INTERNALS__.invoke('desktop_runtime_ui_smoke_report', { payload }).catch(() => {});
  }
})();
"#,
                            ) {
                                eprintln!(
                                    "desktop runtime UI smoke webview probe eval failed: elapsed_ms={elapsed_ms}, error={error}"
                                );
                            }
                        }
                        println!(
                            "desktop runtime UI smoke webview probe emitted: elapsed_ms={elapsed_ms}"
                        );
                        tokio::time::sleep(std::time::Duration::from_millis(interval_ms)).await;
                        elapsed_ms += interval_ms;
                    }

                    eprintln!("desktop runtime UI smoke timed out: timeout_after_ms={timeout_ms}");
                    exit_runtime_smoke(&request_handle, 1);
                });
            } else if let Some(exit_after_ms) = runtime_smoke_exit_after_ms {
                let smoke_handle = handle.clone();
                tauri::async_runtime::spawn(async move {
                    tokio::time::sleep(std::time::Duration::from_millis(exit_after_ms)).await;
                    println!("desktop runtime smoke exiting: exit_after_ms={exit_after_ms}");
                    exit_runtime_smoke(&smoke_handle, 0);
                });
            } else {
                // 启动控制面心跳（后台定时检查）
                let state_for_heartbeat = shared_state.clone();
                tauri::async_runtime::spawn(async move {
                    let engine =
                        services::sync_engine::SyncEngine::new(state_for_heartbeat.clone(), {
                            state_for_heartbeat.read().await.backend_url.clone()
                        });

                    loop {
                        let _ = engine.control_plane_heartbeat().await;
                        tokio::time::sleep(std::time::Duration::from_secs(60)).await;
                    }
                });
            }

            log::info!("安心法务客户端启动完成");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("安心法务客户端启动失败");
}

#[cfg(test)]
mod tests {
    use super::{
        desktop_runtime_self_test, desktop_sync_code_smoke_json, desktop_sync_loopback_smoke_json,
    };

    #[test]
    fn runtime_self_test_reports_local_db_contract() {
        let report = desktop_runtime_self_test();

        assert_eq!(report.app, "anxin-legal-desktop");
        assert_eq!(report.local_db_url, "sqlcipher:anxin_local.db");
        assert_eq!(report.migration_count, 1);
        assert_eq!(report.migration_versions, vec![1]);
        assert_eq!(report.required_tables_present.len(), 8);
        assert!(report.sync_retry_schema_present);
    }

    #[test]
    fn runtime_self_test_reports_secure_sqlite_contract() {
        let report = desktop_runtime_self_test();

        assert!(report.sqlite_security.encrypted);
        assert!(report.sqlite_security.keyring_backed);
        assert!(!report.sqlite_security.release_blocking);
    }

    #[test]
    fn sync_code_smoke_report_is_packaged_binary_safe() {
        let report = desktop_sync_code_smoke_json().expect("sync code smoke report");
        let payload: serde_json::Value =
            serde_json::from_str(&report).expect("sync code smoke JSON");

        assert_eq!(payload["mode"], "desktop_sync_code_smoke");
        assert_eq!(payload["status"], "passed");
        assert_eq!(payload["release_evidence_complete"], false);
        assert_eq!(payload["checks"]["pending_rows_decoded"], 2);
        assert_eq!(payload["checks"]["retry_needs_human"], true);
    }

    #[test]
    fn sync_loopback_smoke_report_exercises_http_backend() {
        let report = desktop_sync_loopback_smoke_json().expect("sync loopback smoke report");
        let payload: serde_json::Value =
            serde_json::from_str(&report).expect("sync loopback smoke JSON");

        assert_eq!(payload["mode"], "desktop_sync_loopback_smoke");
        assert_eq!(payload["status"], "passed");
        assert_eq!(payload["release_evidence_complete"], false);
        assert_eq!(payload["checks"]["loopback_backend"], "passed");
        assert_eq!(payload["checks"]["auth_header_received"], true);
        assert_eq!(payload["checks"]["backend_received_records"], 2);
        assert_eq!(payload["checks"]["accepted_after_conflict"], 1);
        assert_eq!(payload["checks"]["rows_synced"], 1);
        assert_eq!(payload["checks"]["rows_conflicted"], 1);
        assert_eq!(payload["checks"]["pull_records_written"], 1);
        assert_eq!(payload["checks"]["cursor_advanced_to"], 13);
    }

    #[test]
    fn runtime_smoke_options_are_explicitly_timed() {
        let options = super::DesktopRunOptions::runtime_smoke(1500);

        assert_eq!(options.runtime_smoke_exit_after_ms, Some(1500));
        assert_eq!(options.runtime_ui_smoke_timeout_ms, None);
    }

    #[test]
    fn runtime_ui_smoke_options_are_explicitly_timed() {
        let options = super::DesktopRunOptions::runtime_ui_smoke(10_000);

        assert_eq!(options.runtime_smoke_exit_after_ms, None);
        assert_eq!(options.runtime_ui_smoke_timeout_ms, Some(10_000));
    }

    #[test]
    fn runtime_ui_smoke_payload_requires_rendered_tauri_root() {
        let ready_payload = serde_json::json!({
            "hasRoot": true,
            "platform": "tauri-macos",
            "rootChildCount": 1,
            "title": "安心法务"
        });
        let missing_platform = serde_json::json!({
            "hasRoot": true,
            "platform": "web",
            "rootChildCount": 1,
            "title": "安心法务"
        });

        assert!(super::desktop_runtime_ui_smoke_payload_ready(
            &ready_payload
        ));
        assert!(!super::desktop_runtime_ui_smoke_payload_ready(
            &missing_platform
        ));
    }
}
