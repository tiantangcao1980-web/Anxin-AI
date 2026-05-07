use crate::models::SharedAppState;
use tauri::State;

/// 生物识别认证
#[tauri::command]
pub async fn biometric_authenticate(reason: Option<String>) -> Result<serde_json::Value, String> {
    let auth_reason = reason.unwrap_or_else(|| "安心法务需要验证您的身份".to_string());

    // 实际调用由前端 tauri-plugin-biometric JS API 处理
    // 这里提供 Rust 侧的辅助功能

    Ok(serde_json::json!({
        "supported": true,
        "reason": auth_reason,
        "message": "请使用前端 @tauri-apps/plugin-biometric API 进行生物识别"
    }))
}

/// 保存认证 Token 到安全存储
#[tauri::command]
pub async fn save_auth_token(
    token: String,
    refresh_token: Option<String>,
    state: State<'_, SharedAppState>,
) -> Result<(), String> {
    let mut s = state.write().await;
    s.user_token = Some(token);

    // refresh_token 存储到 tauri-plugin-store（由前端调用）
    if let Some(rt) = refresh_token {
        log::info!("Refresh token 已接收，长度: {}", rt.len());
    }

    Ok(())
}

/// 清除认证信息（登出）
#[tauri::command]
pub async fn clear_auth(state: State<'_, SharedAppState>) -> Result<(), String> {
    let mut s = state.write().await;
    s.user_token = None;
    s.unread_count = 0;
    log::info!("用户已登出，认证信息已清除");
    Ok(())
}

/// 检查是否已认证
#[tauri::command]
pub async fn is_authenticated(state: State<'_, SharedAppState>) -> Result<bool, String> {
    let s = state.read().await;
    Ok(s.user_token.is_some())
}

/// 获取应用基本信息
#[tauri::command]
pub fn get_app_info() -> serde_json::Value {
    serde_json::json!({
        "name": "安心法务",
        "version": env!("CARGO_PKG_VERSION"),
        "platform": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
    })
}
