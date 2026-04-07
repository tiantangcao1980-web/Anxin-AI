#![allow(dead_code)]

/// 离线任务队列
///
/// 断网时缓存用户的 AI 任务请求到 SQLite，重连后自动推送到云端执行。
///
/// 工作流程：
/// 1. 用户提交任务 → 检查网络状态
/// 2. 在线 → 直接调用云端 API
/// 3. 离线 → 存入 offline_tasks 表（status='queued'）
/// 4. 本地 LLM 可处理的任务 → 本地执行并标记 status='local_completed'
/// 5. 重连后 → 批量推送 queued 任务到云端
/// 6. 云端返回结果 → 更新本地记录 status='synced'

use crate::models::SharedAppState;
use serde::{Deserialize, Serialize};

/// 离线任务记录
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OfflineTask {
    pub id: String,
    pub task_type: String,        // "chat" | "contract_review" | "document_draft" | "rag_search"
    pub description: String,       // 用户输入的任务描述
    pub conversation_id: Option<String>,
    pub priority: i32,             // 0=critical, 1=high, 2=normal, 3=low
    pub status: String,            // "queued" | "local_processing" | "local_completed" | "pushing" | "synced" | "failed"
    pub local_result: Option<String>,  // 本地 LLM 处理的结果
    pub cloud_result: Option<String>,  // 云端返回的结果
    pub created_at: String,
    pub updated_at: String,
    pub retry_count: i32,
    pub error_message: Option<String>,
}

/// SQLite 建表 SQL（追加到 local_db.rs 的 INIT_SQL 中）
pub const OFFLINE_TASKS_SQL: &str = r#"
-- 离线任务队列
CREATE TABLE IF NOT EXISTS offline_tasks (
    id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL DEFAULT 'chat',
    description TEXT NOT NULL,
    conversation_id TEXT,
    priority INTEGER DEFAULT 2,
    status TEXT DEFAULT 'queued',
    local_result TEXT,
    cloud_result TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_offline_tasks_status ON offline_tasks(status);
CREATE INDEX IF NOT EXISTS idx_offline_tasks_priority ON offline_tasks(priority, created_at);
"#;

/// 离线任务队列管理器
pub struct OfflineQueue {
    state: SharedAppState,
}

impl OfflineQueue {
    pub fn new(state: SharedAppState) -> Self {
        Self { state }
    }

    /// 检查当前是否在线
    pub async fn is_online(&self) -> bool {
        let s = self.state.read().await;
        s.is_online
    }

    /// 获取当前运行模式
    pub async fn get_mode(&self) -> crate::models::AppMode {
        let s = self.state.read().await;
        s.mode
    }

    /// 判断任务是否可以在本地执行
    ///
    /// 基于 capability_negotiator 的逻辑：
    /// - basic tier (7B): 仅 general_consultation, simple_qa, document_summary
    /// - medium tier (14B): + contract_review, document_drafting
    /// - high tier (34B+): 全部
    pub fn can_execute_locally(task_type: &str) -> bool {
        // 保守策略：仅最简单的任务在本地执行
        matches!(task_type, "chat" | "simple_qa" | "document_summary")
    }

    /// 统计各状态的任务数
    pub fn count_sql() -> &'static str {
        r#"
        SELECT status, COUNT(*) as count
        FROM offline_tasks
        GROUP BY status
        "#
    }

    /// 获取待推送的任务（按优先级排序）
    pub fn pending_push_sql() -> &'static str {
        r#"
        SELECT * FROM offline_tasks
        WHERE status IN ('queued', 'local_completed')
        ORDER BY priority ASC, created_at ASC
        LIMIT 20
        "#
    }

    /// 插入新的离线任务
    pub fn insert_sql() -> &'static str {
        r#"
        INSERT INTO offline_tasks (id, task_type, description, conversation_id, priority, status)
        VALUES (?1, ?2, ?3, ?4, ?5, 'queued')
        "#
    }

    /// 更新任务状态
    pub fn update_status_sql() -> &'static str {
        r#"
        UPDATE offline_tasks
        SET status = ?2, updated_at = CURRENT_TIMESTAMP, error_message = ?3
        WHERE id = ?1
        "#
    }

    /// 保存本地执行结果
    pub fn save_local_result_sql() -> &'static str {
        r#"
        UPDATE offline_tasks
        SET status = 'local_completed', local_result = ?2, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?1
        "#
    }

    /// 保存云端返回结果
    pub fn save_cloud_result_sql() -> &'static str {
        r#"
        UPDATE offline_tasks
        SET status = 'synced', cloud_result = ?2, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?1
        "#
    }

    /// 标记推送失败并增加重试计数
    pub fn mark_failed_sql() -> &'static str {
        r#"
        UPDATE offline_tasks
        SET status = CASE WHEN retry_count < 3 THEN 'queued' ELSE 'failed' END,
            retry_count = retry_count + 1,
            error_message = ?2,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?1
        "#
    }

    /// 清理已同步的旧任务（保留最近 7 天）
    pub fn cleanup_sql() -> &'static str {
        r#"
        DELETE FROM offline_tasks
        WHERE status = 'synced'
        AND updated_at < datetime('now', '-7 days')
        "#
    }
}
