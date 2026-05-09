use crate::services::{offline_queue, secure_db};
use serde::Serialize;
use std::path::Path;
use tauri::{AppHandle, Emitter};

pub const FILE_DROP_QUEUED_EVENT: &str = "desktop://file-queued";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileDropTaskPlan {
    pub file_name: String,
    pub task_type: &'static str,
    pub action_label: &'static str,
    pub priority: i32,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct QueuedFileDropTask {
    pub task_id: String,
    pub file_name: String,
    pub task_type: String,
    pub action_label: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct UnsupportedFileDrop {
    pub file_name: String,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct FileDropQueueReport {
    pub queued: Vec<QueuedFileDropTask>,
    pub unsupported: Vec<UnsupportedFileDrop>,
}

pub fn classify_file_drop_path(path: &str) -> Result<FileDropTaskPlan, String> {
    let trimmed = path.trim();
    if trimmed.is_empty() {
        return Err("文件路径为空".to_string());
    }

    let path = Path::new(trimmed);
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .filter(|name| !name.trim().is_empty())
        .ok_or_else(|| "无法识别文件名".to_string())?
        .to_string();
    let extension = path
        .extension()
        .and_then(|extension| extension.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();

    match extension.as_str() {
        "pdf" | "doc" | "docx" => Ok(FileDropTaskPlan {
            file_name,
            task_type: "contract_review",
            action_label: "合同审查",
            priority: 1,
        }),
        "txt" | "md" => Ok(FileDropTaskPlan {
            file_name,
            task_type: "document_summary",
            action_label: "文档摘要",
            priority: 2,
        }),
        _ => Err(format!(
            "暂不支持 .{} 文件",
            if extension.is_empty() {
                "unknown"
            } else {
                extension.as_str()
            }
        )),
    }
}

pub fn build_file_drop_task_description(path: &str, plan: &FileDropTaskPlan) -> String {
    serde_json::json!({
        "source": "desktop_file_drop",
        "action": plan.action_label,
        "file_name": plan.file_name,
        "local_path": path.trim(),
    })
    .to_string()
}

#[tauri::command]
pub async fn queue_file_drop_paths(
    app: AppHandle,
    paths: Vec<String>,
) -> Result<FileDropQueueReport, String> {
    let mut queued = Vec::new();
    let mut unsupported = Vec::new();

    for path in paths {
        match classify_file_drop_path(&path) {
            Ok(plan) => {
                let task_id = uuid::Uuid::new_v4().to_string();
                let description = build_file_drop_task_description(&path, &plan);
                secure_db::execute(
                    &app,
                    offline_queue::OfflineQueue::insert_sql(),
                    vec![
                        serde_json::Value::String(task_id.clone()),
                        serde_json::Value::String(plan.task_type.to_string()),
                        serde_json::Value::String(description),
                        serde_json::Value::Null,
                        serde_json::Value::from(plan.priority),
                    ],
                )?;
                queued.push(QueuedFileDropTask {
                    task_id,
                    file_name: plan.file_name,
                    task_type: plan.task_type.to_string(),
                    action_label: plan.action_label.to_string(),
                });
            }
            Err(reason) => {
                let file_name = Path::new(path.trim())
                    .file_name()
                    .and_then(|name| name.to_str())
                    .filter(|name| !name.trim().is_empty())
                    .unwrap_or("unknown")
                    .to_string();
                unsupported.push(UnsupportedFileDrop { file_name, reason });
            }
        }
    }

    let report = FileDropQueueReport {
        queued,
        unsupported,
    };
    let _ = app.emit(FILE_DROP_QUEUED_EVENT, &report);
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::{build_file_drop_task_description, classify_file_drop_path};
    use serde_json::Value;

    #[test]
    fn classify_file_drop_routes_contract_documents_to_review() {
        for path in ["/tmp/lease.pdf", "/tmp/NDA.DOCX", "/tmp/合同.doc"] {
            let plan = classify_file_drop_path(path).expect("contract plan");

            assert_eq!(plan.task_type, "contract_review");
            assert_eq!(plan.action_label, "合同审查");
            assert_eq!(plan.priority, 1);
        }
    }

    #[test]
    fn classify_file_drop_routes_text_to_summary() {
        for path in ["/tmp/meeting.txt", "/tmp/research.MD"] {
            let plan = classify_file_drop_path(path).expect("summary plan");

            assert_eq!(plan.task_type, "document_summary");
            assert_eq!(plan.action_label, "文档摘要");
            assert_eq!(plan.priority, 2);
        }
    }

    #[test]
    fn classify_file_drop_rejects_empty_and_unsupported_files() {
        assert!(classify_file_drop_path("  ").is_err());
        assert_eq!(
            classify_file_drop_path("/tmp/archive.zip").unwrap_err(),
            "暂不支持 .zip 文件"
        );
    }

    #[test]
    fn file_drop_description_keeps_local_path_in_encrypted_queue_payload() {
        let plan = classify_file_drop_path("/Users/me/合同.pdf").expect("plan");
        let description = build_file_drop_task_description("/Users/me/合同.pdf", &plan);
        let payload: Value = serde_json::from_str(&description).expect("json payload");

        assert_eq!(payload["source"], "desktop_file_drop");
        assert_eq!(payload["action"], "合同审查");
        assert_eq!(payload["file_name"], "合同.pdf");
        assert_eq!(payload["local_path"], "/Users/me/合同.pdf");
    }
}
