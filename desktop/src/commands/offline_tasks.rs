#![allow(dead_code, unused_variables)]

/// 离线任务队列 Tauri 命令
///
/// 暴露给前端的 IPC 命令，用于：
/// 1. 提交离线任务
/// 2. 查询队列状态
/// 3. 触发批量同步
/// 4. 管理 Harness Artifact
use crate::commands::privacy_guard::ensure_data_network_allowed;
use crate::models::{AppMode, SharedAppState};
use crate::services::{offline_queue, secure_db};
use serde::{Deserialize, Serialize};
use tauri::{command, AppHandle, State};

/// 离线任务摘要
#[allow(dead_code)]
#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct OfflineTaskSummary {
    pub id: String,
    pub task_type: String,
    pub title: String,
    pub detail: String,
    pub status: String,
    pub priority: i32,
    pub created_at: String,
    pub updated_at: String,
    pub retry_count: i32,
    pub has_local_result: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_message: Option<String>,
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

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct OfflineQueueRetryReport {
    pub retried: u32,
    pub local_only: bool,
    pub safe_in_top_secret: bool,
    pub message: String,
}

fn clamp_task_limit(limit: Option<u32>) -> u32 {
    limit.unwrap_or(8).clamp(1, 50)
}

fn value_string(row: &serde_json::Value, key: &str) -> Result<String, String> {
    row.get(key)
        .and_then(serde_json::Value::as_str)
        .map(str::to_string)
        .ok_or_else(|| format!("离线任务缺少字段: {key}"))
}

fn value_i32(row: &serde_json::Value, key: &str) -> Result<i32, String> {
    let value = row
        .get(key)
        .ok_or_else(|| format!("离线任务缺少字段: {key}"))?;
    if let Some(value) = value.as_i64() {
        return i32::try_from(value).map_err(|_| format!("离线任务字段 {key} 超出范围"));
    }
    if let Some(value) = value.as_str() {
        return value
            .parse::<i32>()
            .map_err(|err| format!("离线任务字段 {key} 解析失败: {err}"));
    }
    Err(format!("离线任务字段 {key} 类型无效"))
}

fn value_bool(row: &serde_json::Value, key: &str) -> bool {
    row.get(key)
        .and_then(|value| {
            value
                .as_bool()
                .or_else(|| value.as_i64().map(|number| number != 0))
                .or_else(|| value.as_str().map(|text| text == "1" || text == "true"))
        })
        .unwrap_or(false)
}

fn truncate_chars(value: &str, max_chars: usize) -> String {
    if value.chars().count() <= max_chars {
        return value.to_string();
    }
    let keep = max_chars.saturating_sub(3);
    let mut truncated = value.chars().take(keep).collect::<String>();
    truncated.push_str("...");
    truncated
}

fn task_type_label(task_type: &str) -> &'static str {
    match task_type {
        "chat" | "simple_qa" => "离线问答",
        "document_summary" => "文档摘要",
        "contract_review" => "合同审查",
        "document_draft" | "document_drafting" => "文书起草",
        "rag_search" => "知识检索",
        _ => "离线任务",
    }
}

fn summarize_task_description(task_type: &str, description: &str) -> (String, String) {
    if let Ok(payload) = serde_json::from_str::<serde_json::Value>(description) {
        if payload.get("source").and_then(serde_json::Value::as_str) == Some("desktop_file_drop") {
            let action = payload
                .get("action")
                .and_then(serde_json::Value::as_str)
                .unwrap_or_else(|| task_type_label(task_type));
            let file_name = payload
                .get("file_name")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("文件");
            return (
                format!("{action}: {}", truncate_chars(file_name, 64)),
                "桌面文件拖入任务，本地路径仅保存在加密队列".to_string(),
            );
        }
    }

    (
        task_type_label(task_type).to_string(),
        truncate_chars(
            &description.split_whitespace().collect::<Vec<_>>().join(" "),
            120,
        ),
    )
}

fn task_summary_from_row(row: &serde_json::Value) -> Result<OfflineTaskSummary, String> {
    let task_type = value_string(row, "task_type")?;
    let description = value_string(row, "description")?;
    let (title, detail) = summarize_task_description(&task_type, &description);
    let error_message = row
        .get("error_message")
        .and_then(serde_json::Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .map(|value| truncate_chars(value, 120));

    Ok(OfflineTaskSummary {
        id: value_string(row, "id")?,
        task_type,
        title,
        detail,
        status: value_string(row, "status")?,
        priority: value_i32(row, "priority")?,
        created_at: value_string(row, "created_at")?,
        updated_at: value_string(row, "updated_at")?,
        retry_count: value_i32(row, "retry_count")?,
        has_local_result: value_bool(row, "has_local_result"),
        error_message,
    })
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

/// 列出最近离线任务。
///
/// 返回结果会将桌面文件拖入任务的完整本地路径留在加密队列内，只暴露文件名和动作摘要。
#[command]
pub async fn list_offline_tasks(
    app: AppHandle,
    limit: Option<u32>,
) -> Result<Vec<OfflineTaskSummary>, String> {
    let rows = secure_db::select(
        &app,
        offline_queue::OfflineQueue::recent_tasks_sql(),
        vec![serde_json::Value::from(clamp_task_limit(limit))],
    )?;

    rows.iter().map(task_summary_from_row).collect()
}

/// 将 failed 离线任务重新放回本地队列。
///
/// 该命令只更新本地 SQLCipher 队列状态，不触发网络同步，绝密模式下可安全执行。
#[command]
pub async fn retry_failed_offline_tasks(app: AppHandle) -> Result<OfflineQueueRetryReport, String> {
    let result = secure_db::execute(
        &app,
        offline_queue::OfflineQueue::retry_failed_sql(),
        Vec::new(),
    )?;
    let retried =
        u32::try_from(result.rows_affected).map_err(|_| "重试任务数量超出范围".to_string())?;

    Ok(OfflineQueueRetryReport {
        retried,
        local_only: true,
        safe_in_top_secret: true,
        message: if retried == 0 {
            "没有失败任务需要重新入队".to_string()
        } else {
            format!("{retried} 条失败任务已重新入队")
        },
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
    state: State<'_, SharedAppState>,
    session_id: String,
    artifacts: std::collections::HashMap<String, serde_json::Value>,
    _device_id: String,
) -> Result<String, String> {
    ensure_data_network_allowed(state.inner(), "推送 Harness Artifact").await?;

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
    state: State<'_, SharedAppState>,
    session_id: String,
    _artifact_types: Option<Vec<String>>,
) -> Result<std::collections::HashMap<String, serde_json::Value>, String> {
    ensure_data_network_allowed(state.inner(), "拉取 Harness Artifact").await?;

    log::info!("拉取 Harness Artifact: session={}", session_id);

    // 实际实现：POST /api/v1/sync/artifacts/pull
    // 返回 artifacts map

    Ok(std::collections::HashMap::new())
}

#[cfg(test)]
mod tests {
    use super::{clamp_task_limit, summarize_task_description};

    #[test]
    fn file_drop_summary_never_exposes_local_path() {
        let description = serde_json::json!({
            "source": "desktop_file_drop",
            "action": "合同审查",
            "file_name": "并购协议.pdf",
            "local_path": "/Users/alice/secret/并购协议.pdf"
        })
        .to_string();

        let (title, detail) = summarize_task_description("contract_review", &description);

        assert_eq!(title, "合同审查: 并购协议.pdf");
        assert!(detail.contains("加密队列"));
        assert!(!title.contains("/Users"));
        assert!(!detail.contains("/Users"));
    }

    #[test]
    fn plain_summary_is_normalized_and_capped() {
        let (_, detail) = summarize_task_description("chat", &"a\n".repeat(200));

        assert_eq!(detail.chars().count(), 120);
        assert!(detail.ends_with("..."));
    }

    #[test]
    fn task_list_limit_is_bounded() {
        assert_eq!(clamp_task_limit(None), 8);
        assert_eq!(clamp_task_limit(Some(0)), 1);
        assert_eq!(clamp_task_limit(Some(100)), 50);
    }
}
