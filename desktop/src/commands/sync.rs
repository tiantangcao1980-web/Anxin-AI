use crate::models::{AppMode, SharedAppState, SyncStatus};
use tauri::State;

/// 触发手动同步
#[tauri::command]
pub async fn trigger_sync(state: State<'_, SharedAppState>) -> Result<serde_json::Value, String> {
    let mode = {
        let s = state.read().await;
        s.mode
    };

    match mode {
        AppMode::TopSecret => {
            return Ok(serde_json::json!({
                "success": false,
                "message": "绝密模式下不支持数据同步"
            }));
        }
        _ => {}
    }

    // 设置同步状态
    {
        let mut s = state.write().await;
        s.sync_status = SyncStatus::Syncing;
    }

    // TODO: 实际同步逻辑（调用后端 /api/v1/sync/push 和 /pull）
    // 这里先模拟同步完成
    let now = chrono::Utc::now().to_rfc3339();

    {
        let mut s = state.write().await;
        s.sync_status = SyncStatus::Idle;
        s.last_sync_time = Some(now.clone());
    }

    Ok(serde_json::json!({
        "success": true,
        "message": "同步完成",
        "sync_time": now
    }))
}

/// 获取同步状态
#[tauri::command]
pub async fn get_sync_status(state: State<'_, SharedAppState>) -> Result<serde_json::Value, String> {
    let s = state.read().await;
    Ok(serde_json::json!({
        "status": s.sync_status,
        "last_sync_time": s.last_sync_time,
        "is_online": s.is_online
    }))
}

/// 获取待同步记录数
#[tauri::command]
pub async fn get_pending_sync_count() -> Result<u32, String> {
    // TODO: 查询本地 SQLite sync_log 表中 status='pending' 的记录数
    Ok(0)
}

/// 解决同步冲突
#[tauri::command]
pub async fn resolve_conflict(
    entity_id: String,
    resolution: String, // "keep_local" | "keep_remote"
) -> Result<serde_json::Value, String> {
    log::info!("解决冲突: entity={}, resolution={}", entity_id, resolution);
    // TODO: 实际冲突解决逻辑
    Ok(serde_json::json!({
        "success": true,
        "entity_id": entity_id,
        "resolution": resolution
    }))
}
