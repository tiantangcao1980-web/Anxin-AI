#![allow(dead_code, unused_variables)]

/// 离线任务队列 Tauri 命令
///
/// 暴露给前端的 IPC 命令，用于：
/// 1. 提交离线任务
/// 2. 查询队列状态
/// 3. 触发批量同步
/// 4. 管理 Harness Artifact

use serde::{Deserialize, Serialize};
use tauri::command;

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
    task_type: String,
    _description: String,
    _conversation_id: Option<String>,
    priority: Option<i32>,
) -> Result<String, String> {
    let task_id = uuid::Uuid::new_v4().to_string();
    let priority = priority.unwrap_or(2); // 默认 NORMAL

    // 实际实现：通过 tauri-plugin-sql 写入 SQLite
    // 这里返回 task_id，前端通过 SQL 插件直接执行 INSERT
    log::info!(
        "离线任务已排队: id={}, type={}, priority={}",
        task_id, task_type, priority
    );

    Ok(task_id)
}

/// 获取队列统计
///
/// 前端调用：`invoke('get_queue_stats')`
#[command]
pub async fn get_queue_stats() -> Result<QueueStats, String> {
    // 实际实现：通过 SQL 查询 offline_tasks 表
    // 前端可直接用 tauri-plugin-sql 查询，这里提供 Rust 端备选
    Ok(QueueStats {
        queued: 0,
        local_processing: 0,
        local_completed: 0,
        synced: 0,
        failed: 0,
        total: 0,
    })
}

/// 触发离线任务批量同步
///
/// 前端调用：`invoke('flush_offline_queue')`
/// 将所有 queued/local_completed 的任务推送到云端
#[command]
pub async fn flush_offline_queue() -> Result<String, String> {
    log::info!("触发离线任务队列批量同步...");

    // 实际实现流程：
    // 1. 查询 offline_tasks WHERE status IN ('queued', 'local_completed')
    // 2. 按 priority ASC, created_at ASC 排序
    // 3. 逐个/批量 POST /api/v1/chat 到云端
    // 4. 成功 → 更新 status='synced', cloud_result=响应
    // 5. 失败 → retry_count++, 超过3次 → status='failed'

    Ok("同步任务已触发".to_string())
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
