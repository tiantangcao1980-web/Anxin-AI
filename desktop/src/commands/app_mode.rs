use crate::models::{AppMode, SharedAppState, SyncStatus};
use tauri::State;

/// 获取当前运行模式和应用状态
#[tauri::command]
pub async fn get_app_state(state: State<'_, SharedAppState>) -> Result<serde_json::Value, String> {
    let s = state.read().await;
    serde_json::to_value(&*s).map_err(|e| e.to_string())
}

/// 切换运行模式
#[tauri::command]
pub async fn switch_mode(
    mode: AppMode,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let mut s = state.write().await;
    let old_mode = s.mode;
    s.mode = mode;

    // 根据新模式调整同步状态
    match mode {
        AppMode::TopSecret => {
            s.sync_status = SyncStatus::Offline;
            log::info!("切换到绝密模式：数据面已断开，仅保留控制面");
        }
        AppMode::Hybrid => {
            s.sync_status = SyncStatus::Idle;
            log::info!("切换到混合模式：选择性云同步已启用");
        }
        AppMode::Cloud => {
            s.sync_status = SyncStatus::Idle;
            log::info!("切换到云端模式：完全云端通信");
        }
    }

    Ok(serde_json::json!({
        "success": true,
        "old_mode": old_mode,
        "new_mode": mode,
        "message": format!("已切换至{}", mode)
    }))
}

/// 获取当前模式名称
#[tauri::command]
pub async fn get_current_mode(state: State<'_, SharedAppState>) -> Result<String, String> {
    let s = state.read().await;
    Ok(serde_json::to_string(&s.mode).map_err(|e| e.to_string())?)
}

/// 获取后端 URL（根据模式返回不同的 URL）
#[tauri::command]
pub async fn get_backend_url(state: State<'_, SharedAppState>) -> Result<String, String> {
    let s = state.read().await;
    match s.mode {
        AppMode::TopSecret => Ok("local://api".to_string()),
        _ => Ok(s.backend_url.clone()),
    }
}

/// 设置用户 Token
#[tauri::command]
pub async fn set_user_token(
    token: Option<String>,
    state: State<'_, SharedAppState>,
) -> Result<(), String> {
    let mut s = state.write().await;
    s.user_token = token;
    Ok(())
}

/// 设置后端 URL
#[tauri::command]
pub async fn set_backend_url(url: String, state: State<'_, SharedAppState>) -> Result<(), String> {
    let normalized_url = normalize_backend_url(&url)?;
    let mut s = state.write().await;
    s.backend_url = normalized_url;
    Ok(())
}

/// 更新未读消息计数
#[tauri::command]
pub async fn update_unread_count(
    count: u32,
    state: State<'_, SharedAppState>,
) -> Result<(), String> {
    let mut s = state.write().await;
    s.unread_count = count;
    Ok(())
}

fn normalize_backend_url(input: &str) -> Result<String, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("后端地址不能为空".to_string());
    }

    let parsed =
        reqwest::Url::parse(trimmed).map_err(|_| "请输入完整的 http:// 或 https:// 地址".to_string())?;
    if !matches!(parsed.scheme(), "http" | "https") {
        return Err("后端地址只允许 http 或 https 协议".to_string());
    }
    if parsed.host_str().is_none() {
        return Err("后端地址缺少主机名".to_string());
    }

    let normalized = parsed.to_string().trim_end_matches('/').to_string();
    Ok(normalized)
}

#[cfg(test)]
mod tests {
    use super::normalize_backend_url;

    #[test]
    fn normalizes_http_backend_url() {
        assert_eq!(
            normalize_backend_url(" http://localhost:8001/ ").unwrap(),
            "http://localhost:8001"
        );
        assert_eq!(
            normalize_backend_url("https://api.anxin.example/v1/").unwrap(),
            "https://api.anxin.example/v1"
        );
    }

    #[test]
    fn rejects_non_backend_url_schemes() {
        assert!(normalize_backend_url("").is_err());
        assert!(normalize_backend_url("local://api").is_err());
        assert!(normalize_backend_url("file:///tmp/anxin").is_err());
    }
}
