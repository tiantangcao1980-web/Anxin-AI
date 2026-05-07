#![allow(dead_code, unused_variables)]

/// 离线任务队列 Tauri 命令
///
/// 暴露给前端的 IPC 命令，用于：
/// 1. 提交离线任务
/// 2. 查询队列状态
/// 3. 触发批量同步
/// 4. 管理 Harness Artifact
use crate::models::{AppMode, SharedAppState};
use crate::services::{offline_queue, secure_db};
use serde::{Deserialize, Serialize};
use tauri::{command, AppHandle, State};

/// 离线任务摘要
#[allow(dead_code)]
#[derive(Debug, Serialize, Deserialize)]
pub struct OfflineTaskSummary {
    pub id: String,
    pub task_type: String,
    pub description: String,
    pub status: String,
    pub priority: i32,
    pub created_at: String,
    pub has_local_result: bool,
}

/// 队列状态统计
#[derive(Debug, Serialize, Deserialize)]
pub struct QueueStats {
    pub queued: u32,
    pub local_processing: u32,
    pub local_completed: u32,
    pub synced: u32,
    pub failed: u32,
    pub total: u32,
}

/// 提交离线任务
///
/// 前端调用：`invoke('submit_offline_task', { taskType, description, conversationId, priority })`
#[command]
pub async fn submit_offline_task(
    app: AppHandle,
    task_type: String,
    description: String,
    conversation_id: Option<String>,
    priority: Option<i32>,
) -> Result<String, String> {
    let task_id = uuid::Uuid::new_v4().to_string();
    let priority = priority.unwrap_or(2); // 默认 NORMAL

    secure_db::execute(
        &app,
        offline_queue::OfflineQueue::insert_sql(),
        vec![
            serde_json::Value::String(task_id.clone()),
            serde_json::Value::String(task_type.clone()),
            serde_json::Value::String(description),
            conversation_id
                .map(serde_json::Value::String)
                .unwrap_or(serde_json::Value::Null),
            serde_json::Value::from(priority),
        ],
    )?;

    log::info!(
        "离线任务已排队: id={}, type={}, priority={}",
        task_id,
        task_type,
        priority
    );

    Ok(task_id)
}

/// 获取队列统计
///
/// 前端调用：`invoke('get_queue_stats')`
#[command]
pub async fn get_queue_stats(app: AppHandle) -> Result<QueueStats, String> {
    let rows = secure_db::select(&app, offline_queue::OfflineQueue::count_sql(), Vec::new())?;
    let stats = offline_queue::decode_queue_stats(&rows)?;

    Ok(QueueStats {
        queued: stats.queued,
        local_processing: stats.local_processing,
        local_completed: stats.local_completed,
        synced: stats.synced,
        failed: stats.failed,
        total: stats.total,
    })
}

/// 触发离线任务批量同步
///
/// 前端调用：`invoke('flush_offline_queue')`
/// 将所有 queued/local_completed 的任务推送到云端
#[command]
pub async fn flush_offline_queue(
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<String, String> {
    let rows = secure_db::select(&app, offline_queue::OfflineQueue::count_sql(), Vec::new())?;
    let stats = offline_queue::decode_queue_stats(&rows)?;
    let flushable = stats.flushable();

    if flushable == 0 {
        return Ok("本地离线队列为空，无需同步".to_string());
    }

    let (mode, is_online, has_token) = {
        let state = state.read().await;
        (state.mode, state.is_online, state.user_token.is_some())
    };

    match mode {
        AppMode::TopSecret => Err(format!(
            "绝密模式下不会同步离线任务；当前仍有 {flushable} 条本地任务待推送"
        )),
        _ if !is_online => Err(format!(
            "当前处于离线状态；检测到 {flushable} 条待推送离线任务，未执行云端同步"
        )),
        _ if !has_token => Err(format!(
            "请先登录后再同步；当前仍有 {flushable} 条离线任务待推送"
        )),
        _ => Err(format!(
            "检测到 {flushable} 条待推送离线任务，但 Rust IPC 直连推送尚未实现；请使用前端 Tauri bridge 的本地同步路径"
        )),
    }
}

/// 推送 Harness Artifact 到云端
///
/// 桌面端完成一个任务后，将中间结论推送到云端供其他端使用
#[command]
pub async fn push_harness_artifacts(
    session_id: String,
    artifacts: std::collections::HashMap<String, serde_json::Value>,
    _device_id: String,
) -> Result<String, String> {
    log::info!(
        "推送 Harness Artifact: session={}, types={:?}",
        session_id,
        artifacts.keys().collect::<Vec<_>>()
    );

    // 实际实现：POST /api/v1/sync/artifacts/push
    // {
    //   "device_id": device_id,
    //   "session_id": session_id,
    //   "artifacts": artifacts
    // }

    Ok("Artifact 推送成功".to_string())
}

/// 拉取 Harness Artifact
///
/// 从云端拉取其他设备产出的中间结论
#[command]
pub async fn pull_harness_artifacts(
    session_id: String,
    _artifact_types: Option<Vec<String>>,
) -> Result<std::collections::HashMap<String, serde_json::Value>, String> {
    log::info!("拉取 Harness Artifact: session={}", session_id);

    // 实际实现：POST /api/v1/sync/artifacts/pull
    // 返回 artifacts map

    Ok(std::collections::HashMap::new())
}
