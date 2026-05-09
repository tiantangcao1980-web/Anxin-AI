use crate::models::{AppMode, SharedAppState, SyncStatus};
use crate::services::runtime_config::{self, DesktopRuntimeProfile};
use tauri::{AppHandle, State};

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
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let current = {
        let s = state.read().await;
        s.clone()
    };
    let mut config = runtime_config::load_or_default_for_app(&app, &current)?;
    config.mode = mode;
    runtime_config::save_for_app(&app, &config)?;

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
pub async fn set_backend_url(
    url: String,
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<(), String> {
    let current = {
        let s = state.read().await;
        s.clone()
    };
    let mut config = runtime_config::load_or_default_for_app(&app, &current)?;
    config.backend_url = runtime_config::normalize_backend_url(&url)?;
    runtime_config::save_for_app(&app, &config)?;

    let mut s = state.write().await;
    s.backend_url = config.backend_url;
    Ok(())
}

/// 列出本机保存的工作站配置档。配置档只保存模式和后端地址，不保存 token/secret。
#[tauri::command]
pub async fn list_workstation_profiles(
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<Vec<DesktopRuntimeProfile>, String> {
    let current = {
        let s = state.read().await;
        s.clone()
    };
    let config = runtime_config::load_or_default_for_app(&app, &current)?;
    Ok(config.profiles)
}

/// 创建一个工作站配置档。
#[tauri::command]
pub async fn create_workstation_profile(
    name: String,
    mode: AppMode,
    backend_url: String,
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<DesktopRuntimeProfile, String> {
    let current = {
        let s = state.read().await;
        s.clone()
    };
    let mut config = runtime_config::load_or_default_for_app(&app, &current)?;
    let profile_id = runtime_config::generate_unique_profile_id(&name, &config.profiles);
    let profile = DesktopRuntimeProfile::new(&profile_id, &name, mode, &backend_url)?;
    config.profiles.push(profile.clone());
    config.profiles = runtime_config::normalize_profiles(config.profiles)?;
    runtime_config::save_for_app(&app, &config)?;
    Ok(profile)
}

/// 更新已保存的工作站配置档。
#[tauri::command]
pub async fn update_workstation_profile(
    id: String,
    name: String,
    mode: AppMode,
    backend_url: String,
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<DesktopRuntimeProfile, String> {
    let current = {
        let s = state.read().await;
        s.clone()
    };
    let mut config = runtime_config::load_or_default_for_app(&app, &current)?;
    let normalized_id = runtime_config::normalize_profile_id(&id)?;
    let profile = DesktopRuntimeProfile::new(&normalized_id, &name, mode, &backend_url)?;
    let mut found = false;
    config.profiles = config
        .profiles
        .into_iter()
        .map(|existing| {
            if existing.id == normalized_id {
                found = true;
                profile.clone()
            } else {
                existing
            }
        })
        .collect();
    if !found {
        return Err("未找到工作站配置档".to_string());
    }
    config.profiles = runtime_config::normalize_profiles(config.profiles)?;
    runtime_config::save_for_app(&app, &config)?;
    Ok(profile)
}

/// 删除工作站配置档。
#[tauri::command]
pub async fn delete_workstation_profile(
    id: String,
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<(), String> {
    let current = {
        let s = state.read().await;
        s.clone()
    };
    let mut config = runtime_config::load_or_default_for_app(&app, &current)?;
    let normalized_id = runtime_config::normalize_profile_id(&id)?;
    let before = config.profiles.len();
    config
        .profiles
        .retain(|profile| profile.id != normalized_id);
    if config.profiles.len() == before {
        return Err("未找到工作站配置档".to_string());
    }
    runtime_config::save_for_app(&app, &config)?;
    Ok(())
}

/// 应用工作站配置档到当前桌面运行时。
#[tauri::command]
pub async fn apply_workstation_profile(
    id: String,
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let current = {
        let s = state.read().await;
        s.clone()
    };
    let mut config = runtime_config::load_or_default_for_app(&app, &current)?;
    let normalized_id = runtime_config::normalize_profile_id(&id)?;
    let profile = config
        .profiles
        .iter()
        .find(|item| item.id == normalized_id)
        .cloned()
        .ok_or_else(|| "未找到工作站配置档".to_string())?;
    config.mode = profile.mode;
    config.backend_url = profile.backend_url.clone();
    runtime_config::save_for_app(&app, &config)?;

    let mut s = state.write().await;
    config.apply_to_state(&mut s);
    Ok(serde_json::json!({
        "success": true,
        "profile": profile,
        "message": "工作站配置档已应用"
    }))
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

#[cfg(test)]
mod tests {
    use crate::services::runtime_config::normalize_backend_url;

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
