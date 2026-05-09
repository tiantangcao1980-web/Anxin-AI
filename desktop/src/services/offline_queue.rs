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
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// 离线任务记录
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OfflineTask {
    pub id: String,
    pub task_type: String, // "chat" | "contract_review" | "document_draft" | "rag_search"
    pub description: String, // 用户输入的任务描述
    pub conversation_id: Option<String>,
    pub priority: i32,                // 0=critical, 1=high, 2=normal, 3=low
    pub status: String, // "queued" | "local_processing" | "local_completed" | "pushing" | "synced" | "failed"
    pub local_result: Option<String>, // 本地 LLM 处理的结果
    pub cloud_result: Option<String>, // 云端返回的结果
    pub created_at: String,
    pub updated_at: String,
    pub retry_count: i32,
    pub error_message: Option<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct OfflineQueueStatsSnapshot {
    pub queued: u32,
    pub local_processing: u32,
    pub local_completed: u32,
    pub synced: u32,
    pub failed: u32,
    pub total: u32,
}

impl OfflineQueueStatsSnapshot {
    pub fn flushable(&self) -> u32 {
        self.queued.saturating_add(self.local_completed)
    }
}

fn json_u32_field(row: &Value, key: &str) -> Result<u32, String> {
    let value = row
        .get(key)
        .ok_or_else(|| format!("离线队列统计缺少字段: {key}"))?;

    if let Some(number) = value.as_u64() {
        return u32::try_from(number).map_err(|_| format!("离线队列统计字段 {key} 超出范围"));
    }
    if let Some(number) = value.as_i64() {
        return u32::try_from(number).map_err(|_| format!("离线队列统计字段 {key} 为负数"));
    }
    if let Some(number) = value.as_str() {
        return number
            .parse::<u32>()
            .map_err(|err| format!("离线队列统计字段 {key} 解析失败: {err}"));
    }

    Err(format!("离线队列统计字段 {key} 类型无效"))
}

pub fn decode_queue_stats(rows: &[Value]) -> Result<OfflineQueueStatsSnapshot, String> {
    let mut stats = OfflineQueueStatsSnapshot::default();

    for row in rows {
        let status = row
            .get("status")
            .and_then(Value::as_str)
            .ok_or_else(|| "离线队列统计缺少 status 字段".to_string())?;
        let count = json_u32_field(row, "count")?;
        stats.total = stats.total.saturating_add(count);

        match status {
            "queued" => stats.queued = count,
            "local_processing" => stats.local_processing = count,
            "local_completed" => stats.local_completed = count,
            "synced" => stats.synced = count,
            "failed" => stats.failed = count,
            _ => {}
        }
    }

    Ok(stats)
}

pub fn read_queue_stats_from_connection(
    conn: &Connection,
) -> Result<OfflineQueueStatsSnapshot, String> {
    let mut stmt = conn
        .prepare(OfflineQueue::count_sql())
        .map_err(|err| format!("无法准备离线队列统计查询: {err}"))?;
    let rows = stmt
        .query_map([], |row| {
            let status: String = row.get(0)?;
            let count: i64 = row.get(1)?;
            Ok((status, count))
        })
        .map_err(|err| format!("无法执行离线队列统计查询: {err}"))?;

    let mut stats = OfflineQueueStatsSnapshot::default();
    for row in rows {
        let (status, count) = row.map_err(|err| format!("无法解码离线队列统计结果: {err}"))?;
        let count = u32::try_from(count)
            .map_err(|_| format!("离线队列统计字段 count 超出范围: {count}"))?;
        stats.total = stats.total.saturating_add(count);
        match status.as_str() {
            "queued" => stats.queued = count,
            "local_processing" => stats.local_processing = count,
            "local_completed" => stats.local_completed = count,
            "synced" => stats.synced = count,
            "failed" => stats.failed = count,
            _ => {}
        }
    }

    Ok(stats)
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

    /// 获取内置本机处理器可执行的 queued 任务。
    ///
    /// 当前只选择 document_summary，避免在没有本地模型 smoke 的情况下把 chat/contract_review 误报为已处理。
    pub fn queued_local_tasks_sql() -> &'static str {
        r#"
        SELECT
            id,
            task_type,
            description,
            priority,
            retry_count
        FROM offline_tasks
        WHERE status = 'queued'
          AND task_type = 'document_summary'
        ORDER BY priority ASC, datetime(created_at) ASC
        LIMIT ?1
        "#
    }

    /// 获取最近离线任务，供工作站只读展示。
    pub fn recent_tasks_sql() -> &'static str {
        r#"
        SELECT
            id,
            task_type,
            description,
            status,
            priority,
            created_at,
            updated_at,
            retry_count,
            error_message,
            local_result,
            CASE WHEN local_result IS NULL OR local_result = '' THEN 0 ELSE 1 END as has_local_result
        FROM offline_tasks
        ORDER BY datetime(updated_at) DESC, datetime(created_at) DESC
        LIMIT ?1
        "#
    }

    /// 插入新的离线任务
    pub fn insert_sql() -> &'static str {
        r#"
        INSERT INTO offline_tasks (id, task_type, description, conversation_id, priority, status)
        VALUES (?1, ?2, ?3, ?4, ?5, 'queued')
        "#
    }

    /// 将失败任务重新放回待处理队列。该操作只改本地 SQLCipher 状态，不触网。
    pub fn retry_failed_sql() -> &'static str {
        r#"
        UPDATE offline_tasks
        SET status = 'queued',
            error_message = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE status = 'failed'
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

#[cfg(test)]
mod tests {
    use super::{
        decode_queue_stats, read_queue_stats_from_connection, OfflineQueue,
        OfflineQueueStatsSnapshot,
    };
    use rusqlite::Connection;
    use serde_json::json;

    #[test]
    fn decode_queue_stats_accumulates_known_statuses_and_total() {
        let rows = vec![
            json!({ "status": "queued", "count": 2 }),
            json!({ "status": "local_completed", "count": 1 }),
            json!({ "status": "failed", "count": 3 }),
            json!({ "status": "pushing", "count": 4 }),
        ];

        let stats = decode_queue_stats(&rows).expect("decode queue stats");

        assert_eq!(
            stats,
            OfflineQueueStatsSnapshot {
                queued: 2,
                local_processing: 0,
                local_completed: 1,
                synced: 0,
                failed: 3,
                total: 10,
            }
        );
        assert_eq!(stats.flushable(), 3);
    }

    #[test]
    fn queue_stats_query_reads_real_sqlite_rows() {
        let conn = Connection::open_in_memory().expect("open sqlite");
        conn.execute_batch(include_str!("../../migrations/001_offline_queue.sql"))
            .expect("init schema");
        conn.execute(
            OfflineQueue::insert_sql(),
            ("task-1", "chat", "draft", Option::<String>::None, 2),
        )
        .expect("insert queued task");
        conn.execute(
            OfflineQueue::insert_sql(),
            ("task-2", "chat", "summary", Some("conv-1".to_string()), 1),
        )
        .expect("insert second queued task");
        conn.execute_batch(
            "UPDATE offline_tasks SET status = 'local_completed' WHERE id = 'task-2';
             INSERT INTO offline_tasks (id, task_type, description, priority, status)
             VALUES ('task-3', 'chat', 'push', 0, 'pushing');
             INSERT INTO offline_tasks (id, task_type, description, priority, status)
             VALUES ('task-4', 'chat', 'fail', 3, 'failed');",
        )
        .expect("seed other statuses");

        let stats = read_queue_stats_from_connection(&conn).expect("read queue stats");

        assert_eq!(stats.queued, 1);
        assert_eq!(stats.local_completed, 1);
        assert_eq!(stats.failed, 1);
        assert_eq!(stats.total, 4);
        assert_eq!(stats.flushable(), 2);
    }

    #[test]
    fn retry_failed_sql_requeues_failed_tasks_only() {
        let conn = Connection::open_in_memory().expect("open sqlite");
        conn.execute_batch(include_str!("../../migrations/001_offline_queue.sql"))
            .expect("init schema");
        conn.execute(
            OfflineQueue::insert_sql(),
            ("task-1", "chat", "draft", Option::<String>::None, 2),
        )
        .expect("insert queued task");
        conn.execute_batch(
            "INSERT INTO offline_tasks (id, task_type, description, priority, status, error_message)
             VALUES ('task-2', 'chat', 'failed draft', 2, 'failed', 'network down');",
        )
        .expect("seed failed task");

        let affected = conn
            .execute(OfflineQueue::retry_failed_sql(), [])
            .expect("retry failed tasks");

        assert_eq!(affected, 1);
        let failed_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM offline_tasks WHERE status = 'failed'",
                [],
                |row| row.get(0),
            )
            .expect("count failed");
        let queued_count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM offline_tasks WHERE status = 'queued'",
                [],
                |row| row.get(0),
            )
            .expect("count queued");
        assert_eq!(failed_count, 0);
        assert_eq!(queued_count, 2);
    }

    #[test]
    fn queued_local_tasks_sql_only_picks_builtin_supported_tasks() {
        let conn = Connection::open_in_memory().expect("open sqlite");
        conn.execute_batch(include_str!("../../migrations/001_offline_queue.sql"))
            .expect("init schema");
        conn.execute(
            OfflineQueue::insert_sql(),
            (
                "task-summary",
                "document_summary",
                "summary",
                Option::<String>::None,
                2,
            ),
        )
        .expect("insert summary task");
        conn.execute(
            OfflineQueue::insert_sql(),
            (
                "task-contract",
                "contract_review",
                "contract",
                Option::<String>::None,
                1,
            ),
        )
        .expect("insert contract task");

        let ids = conn
            .prepare(OfflineQueue::queued_local_tasks_sql())
            .expect("prepare queued local tasks")
            .query_map([10_i64], |row| row.get::<_, String>(0))
            .expect("query queued local tasks")
            .collect::<Result<Vec<_>, _>>()
            .expect("decode ids");

        assert_eq!(ids, vec!["task-summary"]);
    }
}
