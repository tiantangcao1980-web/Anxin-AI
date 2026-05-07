use crate::models::{AppMode, SharedAppState};
use crate::services::{offline_queue, secure_db, sync_engine};
use serde_json::json;
use tauri::{AppHandle, State};

fn read_local_sync_snapshot(app: &AppHandle) -> Result<sync_engine::LocalSyncSnapshot, String> {
    let rows = secure_db::select(
        app,
        sync_engine::local_sync_snapshot_sql(),
        vec![
            serde_json::Value::from(sync_engine::MAX_SYNC_RETRIES),
            serde_json::Value::String(chrono::Utc::now().to_rfc3339()),
        ],
    )?;
    sync_engine::decode_local_sync_snapshot(&rows)
}

fn read_offline_queue_stats(
    app: &AppHandle,
) -> Result<offline_queue::OfflineQueueStatsSnapshot, String> {
    let rows = secure_db::select(app, offline_queue::OfflineQueue::count_sql(), Vec::new())?;
    offline_queue::decode_queue_stats(&rows)
}

/// 触发手动同步
///
/// 真实 SQLite push/pull 由前端 `api-adapter.ts` 通过 Rust-owned SQLCipher command 执行。
/// 这里保留 IPC 降级路径，不能伪造空 payload 同步成功。
#[tauri::command]
pub async fn trigger_sync(
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let sync_snapshot = read_local_sync_snapshot(&app)?;
    let queue_stats = read_offline_queue_stats(&app)?;
    let pending_offline_tasks = queue_stats.flushable();
    let (mode, token) = {
        let s = state.read().await;
        (s.mode, s.user_token.clone())
    };

    if matches!(mode, AppMode::TopSecret) {
        return Ok(json!({
            "success": false,
            "message": format!(
                "绝密模式下不同步任何数据；本地仍有 {} 条同步记录、{} 条离线任务待处理",
                sync_snapshot.pending,
                pending_offline_tasks
            ),
            "conflicts": sync_snapshot.conflicts,
            "deferred": sync_snapshot.deferred,
            "needs_human": sync_snapshot.needs_human,
            "pending_sync_records": sync_snapshot.pending,
            "pending_offline_tasks": pending_offline_tasks,
        }));
    }

    let Some(_token) = token else {
        return Ok(json!({
            "success": false,
            "message": format!(
                "请先登录后再同步；本地仍有 {} 条同步记录、{} 条离线任务待处理",
                sync_snapshot.pending,
                pending_offline_tasks
            ),
            "conflicts": sync_snapshot.conflicts,
            "deferred": sync_snapshot.deferred,
            "needs_human": sync_snapshot.needs_human,
            "pending_sync_records": sync_snapshot.pending,
            "pending_offline_tasks": pending_offline_tasks,
        }));
    };

    Ok(json!({
        "success": false,
        "message": format!(
            "Rust IPC 直接同步未启用；本地检测到 {} 条同步记录、{} 条离线任务、{} 条冲突，请使用前端 Tauri bridge 的 SQLCipher 本地同步路径",
            sync_snapshot.pending,
            pending_offline_tasks,
            sync_snapshot.conflicts
        ),
        "sync_time": null,
        "pushed": 0,
        "pulled": 0,
        "conflicts": sync_snapshot.conflicts,
        "deferred": sync_snapshot.deferred,
        "needs_human": sync_snapshot.needs_human,
        "pending_sync_records": sync_snapshot.pending,
        "pending_offline_tasks": pending_offline_tasks,
        "push_ok": false,
        "pull_ok": false,
    }))
}

/// 获取同步状态
#[tauri::command]
pub async fn get_sync_status(
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let s = state.read().await;
    let sync_snapshot = read_local_sync_snapshot(&app)?;
    let queue_stats = read_offline_queue_stats(&app)?;
    Ok(json!({
        "status": s.sync_status,
        "last_sync_time": s.last_sync_time,
        "is_online": s.is_online,
        "pending_sync_records": sync_snapshot.pending,
        "pending_offline_tasks": queue_stats.flushable(),
        "sync_conflicts": sync_snapshot.conflicts,
        "deferred_sync_records": sync_snapshot.deferred,
        "needs_human": sync_snapshot.needs_human,
    }))
}

/// 获取待同步记录数
///
/// 返回 Rust IPC 可观察到的本地待同步工作量：
/// - `sync_log` 中待推送/可重试的记录
/// - `offline_tasks` 中 queued/local_completed 的离线任务
#[tauri::command]
pub async fn get_pending_sync_count(app: AppHandle) -> Result<u32, String> {
    let sync_snapshot = read_local_sync_snapshot(&app)?;
    let queue_stats = read_offline_queue_stats(&app)?;
    Ok(sync_snapshot
        .pending
        .saturating_add(queue_stats.flushable()))
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
        .timeout(std::time::Duration::from_secs(30))
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
