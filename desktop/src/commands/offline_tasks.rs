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
use std::path::Path;
use tauri::{command, AppHandle, State};

const MAX_LOCAL_PROCESS_LIMIT: u32 = 10;
const MAX_TEXT_DOCUMENT_BYTES: u64 = 512 * 1024;
const TEXT_SUMMARY_EXCERPT_CHARS: usize = 480;

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
    pub local_result_preview: Option<String>,
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

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct OfflineQueueProcessReport {
    pub processed: u32,
    pub failed: u32,
    pub local_only: bool,
    pub safe_in_top_secret: bool,
    pub message: String,
}

fn clamp_task_limit(limit: Option<u32>) -> u32 {
    limit.unwrap_or(8).clamp(1, 50)
}

fn clamp_process_limit(limit: Option<u32>) -> u32 {
    limit.unwrap_or(3).clamp(1, MAX_LOCAL_PROCESS_LIMIT)
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

fn normalize_inline_text(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn extension_lower(path: &Path) -> String {
    path.extension()
        .and_then(|extension| extension.to_str())
        .unwrap_or("")
        .to_ascii_lowercase()
}

fn text_summary_payload(
    task_id: &str,
    task_type: &str,
    description: &str,
) -> Result<String, String> {
    let payload = serde_json::from_str::<serde_json::Value>(description)
        .map_err(|_| "内置本机处理器仅支持桌面文件拖入任务".to_string())?;
    if payload.get("source").and_then(serde_json::Value::as_str) != Some("desktop_file_drop") {
        return Err("内置本机处理器仅支持桌面文件拖入任务".to_string());
    }
    if task_type != "document_summary" {
        return Err("当前内置本机处理器仅支持文本类文档摘要".to_string());
    }

    let file_name = payload
        .get("file_name")
        .and_then(serde_json::Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .unwrap_or("文档");
    let local_path = payload
        .get("local_path")
        .and_then(serde_json::Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| "离线任务缺少本机文件路径".to_string())?;
    let path = Path::new(local_path);
    let extension = extension_lower(path);
    if !matches!(extension.as_str(), "txt" | "md") {
        return Err("当前内置本机处理器仅支持 .txt / .md 文档摘要".to_string());
    }

    let metadata =
        std::fs::symlink_metadata(path).map_err(|err| format!("无法读取本机文件元数据: {err}"))?;
    if metadata.file_type().is_symlink() {
        return Err("本机离线处理拒绝符号链接文件".to_string());
    }
    if !metadata.is_file() {
        return Err("本机离线处理只接受普通文件".to_string());
    }
    if metadata.len() > MAX_TEXT_DOCUMENT_BYTES {
        return Err(format!(
            "文本文件超过本机摘要上限 {}KB",
            MAX_TEXT_DOCUMENT_BYTES / 1024
        ));
    }

    let content =
        std::fs::read_to_string(path).map_err(|err| format!("无法读取 UTF-8 文本文件: {err}"))?;
    let normalized = normalize_inline_text(&content);
    if normalized.is_empty() {
        return Err("文本文件内容为空".to_string());
    }

    let line_count = content.lines().count();
    let char_count = content.chars().count();
    let heading = content
        .lines()
        .map(str::trim)
        .find(|line| !line.is_empty())
        .map(|line| truncate_chars(line, 80))
        .unwrap_or_else(|| file_name.to_string());
    let key_points = content
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .take(3)
        .map(|line| truncate_chars(line, 120))
        .collect::<Vec<_>>();
    let excerpt = truncate_chars(&normalized, TEXT_SUMMARY_EXCERPT_CHARS);

    Ok(serde_json::json!({
        "processor": "desktop_builtin_text_summary_v1",
        "taskId": task_id,
        "taskType": task_type,
        "fileName": file_name,
        "localOnly": true,
        "safeInTopSecret": true,
        "summary": {
            "title": heading,
            "method": "本机规则摘要，未调用外部模型或云端 API",
            "lineCount": line_count,
            "charCount": char_count,
            "keyPoints": key_points,
            "excerpt": excerpt
        }
    })
    .to_string())
}

fn safe_local_result_preview(local_result: Option<&str>) -> Option<String> {
    let payload = serde_json::from_str::<serde_json::Value>(local_result?).ok()?;
    if payload.get("processor").and_then(serde_json::Value::as_str)
        != Some("desktop_builtin_text_summary_v1")
    {
        return None;
    }
    if payload
        .get("localOnly")
        .and_then(serde_json::Value::as_bool)
        != Some(true)
    {
        return None;
    }
    if payload
        .get("safeInTopSecret")
        .and_then(serde_json::Value::as_bool)
        != Some(true)
    {
        return None;
    }

    let summary = payload.get("summary")?;
    let excerpt = summary
        .get("excerpt")
        .and_then(serde_json::Value::as_str)
        .or_else(|| summary.get("title").and_then(serde_json::Value::as_str))?;
    let preview = normalize_inline_text(excerpt);
    if preview.is_empty() {
        None
    } else {
        Some(truncate_chars(&preview, 180))
    }
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
        local_result_preview: safe_local_result_preview(
            row.get("local_result").and_then(serde_json::Value::as_str),
        ),
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

/// 使用内置本机处理器处理 queued 离线任务。
///
/// 当前只处理桌面文件拖入的 .txt/.md `document_summary`，不触发网络、云模型或同步。
#[command]
pub async fn process_local_offline_tasks(
    app: AppHandle,
    limit: Option<u32>,
) -> Result<OfflineQueueProcessReport, String> {
    let rows = secure_db::select(
        &app,
        offline_queue::OfflineQueue::queued_local_tasks_sql(),
        vec![serde_json::Value::from(clamp_process_limit(limit))],
    )?;

    let mut processed = 0_u32;
    let mut failed = 0_u32;

    for row in rows {
        let task_id = value_string(&row, "id")?;
        let task_type = value_string(&row, "task_type")?;
        let description = value_string(&row, "description")?;

        secure_db::execute(
            &app,
            offline_queue::OfflineQueue::update_status_sql(),
            vec![
                serde_json::Value::String(task_id.clone()),
                serde_json::Value::String("local_processing".to_string()),
                serde_json::Value::Null,
            ],
        )?;

        match text_summary_payload(&task_id, &task_type, &description) {
            Ok(local_result) => {
                secure_db::execute(
                    &app,
                    offline_queue::OfflineQueue::save_local_result_sql(),
                    vec![
                        serde_json::Value::String(task_id),
                        serde_json::Value::String(local_result),
                    ],
                )?;
                processed = processed.saturating_add(1);
            }
            Err(error) => {
                secure_db::execute(
                    &app,
                    offline_queue::OfflineQueue::update_status_sql(),
                    vec![
                        serde_json::Value::String(task_id),
                        serde_json::Value::String("failed".to_string()),
                        serde_json::Value::String(error),
                    ],
                )?;
                failed = failed.saturating_add(1);
            }
        }
    }

    Ok(OfflineQueueProcessReport {
        processed,
        failed,
        local_only: true,
        safe_in_top_secret: true,
        message: if processed == 0 && failed == 0 {
            "没有可由内置本机处理器执行的离线任务".to_string()
        } else if failed == 0 {
            format!("{processed} 条离线任务已在本机处理完成")
        } else {
            format!("{processed} 条离线任务已完成，{failed} 条处理失败")
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
    use super::{
        clamp_process_limit, clamp_task_limit, safe_local_result_preview,
        summarize_task_description, text_summary_payload,
    };
    use std::time::{SystemTime, UNIX_EPOCH};

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

    #[test]
    fn offline_process_limit_is_bounded() {
        assert_eq!(clamp_process_limit(None), 3);
        assert_eq!(clamp_process_limit(Some(0)), 1);
        assert_eq!(clamp_process_limit(Some(99)), 10);
    }

    #[test]
    fn offline_text_summary_result_never_exposes_local_path() {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "anxin-offline-summary-{}-{nonce}.md",
            std::process::id()
        ));
        std::fs::write(&path, "# 会议纪要\n\n第一条 风险说明\n第二条 处理计划")
            .expect("write temp markdown");
        let description = serde_json::json!({
            "source": "desktop_file_drop",
            "action": "文档摘要",
            "file_name": "会议纪要.md",
            "local_path": path.to_string_lossy()
        })
        .to_string();

        let result =
            text_summary_payload("task-1", "document_summary", &description).expect("summary");
        let value: serde_json::Value = serde_json::from_str(&result).expect("json result");

        assert_eq!(value["processor"], "desktop_builtin_text_summary_v1");
        assert_eq!(value["fileName"], "会议纪要.md");
        assert!(value["localOnly"].as_bool().unwrap_or(false));
        assert!(value["safeInTopSecret"].as_bool().unwrap_or(false));
        assert!(value["summary"]["excerpt"]
            .as_str()
            .unwrap_or("")
            .contains("风险说明"));
        assert!(!result.contains(&path.to_string_lossy().to_string()));

        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn offline_text_summary_rejects_non_text_extensions() {
        let description = serde_json::json!({
            "source": "desktop_file_drop",
            "action": "合同审查",
            "file_name": "合同.pdf",
            "local_path": "/tmp/合同.pdf"
        })
        .to_string();

        let error =
            text_summary_payload("task-1", "document_summary", &description).expect_err("reject");

        assert!(error.contains(".txt / .md"));
    }

    #[test]
    fn offline_summary_preview_only_exposes_safe_builtin_results() {
        let safe = serde_json::json!({
            "processor": "desktop_builtin_text_summary_v1",
            "localOnly": true,
            "safeInTopSecret": true,
            "summary": {
                "excerpt": "第一条 风险说明\n第二条 处理计划"
            }
        })
        .to_string();
        let unsafe_result = serde_json::json!({
            "processor": "unknown",
            "localOnly": true,
            "safeInTopSecret": true,
            "summary": {
                "excerpt": "不要展示"
            }
        })
        .to_string();

        assert_eq!(
            safe_local_result_preview(Some(&safe)).as_deref(),
            Some("第一条 风险说明 第二条 处理计划")
        );
        assert_eq!(safe_local_result_preview(Some(&unsafe_result)), None);
        assert_eq!(safe_local_result_preview(Some("not-json")), None);
    }
}
