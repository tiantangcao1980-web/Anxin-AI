use crate::models::{AppMode, SharedAppState, SyncStatus};
use serde_json::json;
use tauri::State;

/// HTTP 请求的通用超时
const SYNC_REQUEST_TIMEOUT_SECS: u64 = 30;

/// 客户端同步请求载荷。
///
/// 为了让桌面 / 云端首版打通，使用最小载荷：
/// - records 从 SQLite `offline_tasks` 表拿（TODO 下个 Sprint）
/// - last_sync_version 从 `sync_state` 表取（TODO 下个 Sprint）
///
/// 本 commit 先把 HTTP 调用链路真实接上，载荷细节逐步补。
fn build_push_body(device_id: &str) -> serde_json::Value {
    json!({
        "device_id": device_id,
        "records": [],  // TODO: 从 SQLite offline_tasks 表读取
        "last_sync_version": 0,
    })
}

/// 触发手动同步
///
/// 流程：
/// 1. 绝密模式直接拒绝
/// 2. 获取 backend_url + auth_token；任一缺失视为未登录
/// 3. POST /api/v1/sync/push（当前载荷为空，后续接入 SQLite 产出）
/// 4. GET  /api/v1/sync/pull?since_version=0（当前丢弃数据，后续写入 SQLite）
/// 5. 更新 last_sync_time + sync_status
#[tauri::command]
pub async fn trigger_sync(state: State<'_, SharedAppState>) -> Result<serde_json::Value, String> {
    let (mode, backend_url, token) = {
        let s = state.read().await;
        (s.mode, s.backend_url.clone(), s.user_token.clone())
    };

    if matches!(mode, AppMode::TopSecret) {
        return Ok(json!({
            "success": false,
            "message": "绝密模式下不同步任何数据"
        }));
    }

    let Some(token) = token else {
        return Ok(json!({
            "success": false,
            "message": "请先登录后再同步"
        }));
    };

    // 状态 → Syncing
    {
        let mut s = state.write().await;
        s.sync_status = SyncStatus::Syncing;
    }

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(SYNC_REQUEST_TIMEOUT_SECS))
        .build()
        .map_err(|e| format!("创建 HTTP 客户端失败: {e}"))?;

    let device_id = std::env::var("ANXIN_DEVICE_ID").unwrap_or_else(|_| "desktop".to_string());

    // Push
    let push_url = format!("{}/api/v1/sync/push", backend_url.trim_end_matches('/'));
    let push_resp = client
        .post(&push_url)
        .bearer_auth(&token)
        .json(&build_push_body(&device_id))
        .send()
        .await;

    let push_ok = match push_resp {
        Ok(r) if r.status().is_success() => true,
        Ok(r) => {
            log::warn!("sync.push 非 2xx: status={}", r.status());
            false
        }
        Err(e) => {
            log::warn!("sync.push 失败: {e}");
            false
        }
    };

    // Pull
    let pull_url = format!(
        "{}/api/v1/sync/pull?since_version=0&limit=100",
        backend_url.trim_end_matches('/')
    );
    let pull_resp = client
        .get(&pull_url)
        .bearer_auth(&token)
        .send()
        .await;

    let pull_ok = match pull_resp {
        Ok(r) if r.status().is_success() => {
            // TODO: 下个 Sprint 把 r.json() 的 records 写入 SQLite
            true
        }
        Ok(r) => {
            log::warn!("sync.pull 非 2xx: status={}", r.status());
            false
        }
        Err(e) => {
            log::warn!("sync.pull 失败: {e}");
            false
        }
    };

    let now = chrono::Utc::now().to_rfc3339();
    let success = push_ok && pull_ok;
    {
        let mut s = state.write().await;
        s.sync_status = if success { SyncStatus::Idle } else { SyncStatus::Error };
        if success {
            s.last_sync_time = Some(now.clone());
        }
    }

    Ok(json!({
        "success": success,
        "message": if success { "同步完成" } else { "同步未完成，请检查网络或登录状态" },
        "sync_time": if success { Some(now) } else { None },
        "push_ok": push_ok,
        "pull_ok": pull_ok,
    }))
}

/// 获取同步状态
#[tauri::command]
pub async fn get_sync_status(state: State<'_, SharedAppState>) -> Result<serde_json::Value, String> {
    let s = state.read().await;
    Ok(json!({
        "status": s.sync_status,
        "last_sync_time": s.last_sync_time,
        "is_online": s.is_online
    }))
}

/// 获取待同步记录数
///
/// 真实实现需要读 SQLite `offline_tasks` 表 WHERE status='pending'。
/// 目前保留为 0，等 sync_engine 的 SQLite schema 落地后替换。
#[tauri::command]
pub async fn get_pending_sync_count() -> Result<u32, String> {
    Ok(0)
}

/// 解决同步冲突
///
/// 将冲突决议上报后端 `/api/v1/sync/resolve`。
#[tauri::command]
pub async fn resolve_conflict(
    state: State<'_, SharedAppState>,
    entity_type: String,
    entity_id: String,
    resolution: String, // "keep_local" | "keep_remote" | "merge"
) -> Result<serde_json::Value, String> {
    log::info!(
        "解决冲突: entity={}/{}, resolution={}",
        entity_type,
        entity_id,
        resolution
    );

    let (backend_url, token) = {
        let s = state.read().await;
        (s.backend_url.clone(), s.user_token.clone())
    };

    let Some(token) = token else {
        return Err("未登录，无法解决冲突".to_string());
    };

    let url = format!("{}/api/v1/sync/resolve", backend_url.trim_end_matches('/'));
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(SYNC_REQUEST_TIMEOUT_SECS))
        .build()
        .map_err(|e| e.to_string())?;

    let resp = client
        .post(&url)
        .bearer_auth(&token)
        .json(&json!({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "resolution": resolution,
        }))
        .send()
        .await
        .map_err(|e| format!("上报冲突决议失败: {e}"))?;

    let ok = resp.status().is_success();
    Ok(json!({
        "success": ok,
        "entity_id": entity_id,
        "resolution": resolution,
        "status": resp.status().as_u16(),
    }))
}
