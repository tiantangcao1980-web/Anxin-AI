#![allow(dead_code)]

use crate::models::{AppMode, SharedAppState, SyncStatus};
use rusqlite::Connection;
use serde_json::Value;

pub const MAX_SYNC_RETRIES: i64 = 3;

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LocalSyncSnapshot {
    pub pending: u32,
    pub deferred: u32,
    pub conflicts: u32,
    pub needs_human: u32,
}

fn json_u32_field(row: &Value, key: &str) -> Result<u32, String> {
    let value = row
        .get(key)
        .ok_or_else(|| format!("同步快照缺少字段: {key}"))?;

    if let Some(number) = value.as_u64() {
        return u32::try_from(number).map_err(|_| format!("同步快照字段 {key} 超出范围"));
    }
    if let Some(number) = value.as_i64() {
        return u32::try_from(number).map_err(|_| format!("同步快照字段 {key} 为负数"));
    }
    if let Some(number) = value.as_str() {
        return number
            .parse::<u32>()
            .map_err(|err| format!("同步快照字段 {key} 解析失败: {err}"));
    }

    Err(format!("同步快照字段 {key} 类型无效"))
}

pub fn local_sync_snapshot_sql() -> &'static str {
    r#"
    SELECT
        COALESCE(SUM(
            CASE
                WHEN status = 'pending'
                    OR (
                        status = 'failed'
                        AND COALESCE(needs_human, 0) = 0
                        AND COALESCE(retry_count, 0) < ?1
                        AND (next_retry_at IS NULL OR next_retry_at <= ?2)
                    )
                THEN 1 ELSE 0
            END
        ), 0) AS pending_count,
        COALESCE(SUM(
            CASE
                WHEN status = 'failed'
                    AND COALESCE(needs_human, 0) = 0
                    AND COALESCE(retry_count, 0) < ?1
                    AND next_retry_at > ?2
                THEN 1 ELSE 0
            END
        ), 0) AS deferred_count,
        COALESCE(SUM(CASE WHEN status = 'conflict' THEN 1 ELSE 0 END), 0) AS conflict_count,
        COALESCE(SUM(
            CASE
                WHEN COALESCE(needs_human, 0) = 1 OR status = 'conflict'
                THEN 1 ELSE 0
            END
        ), 0) AS needs_human_count
    FROM sync_log
    "#
}

pub fn decode_local_sync_snapshot(rows: &[Value]) -> Result<LocalSyncSnapshot, String> {
    let row = rows
        .first()
        .ok_or_else(|| "同步快照查询未返回任何结果".to_string())?;

    Ok(LocalSyncSnapshot {
        pending: json_u32_field(row, "pending_count")?,
        deferred: json_u32_field(row, "deferred_count")?,
        conflicts: json_u32_field(row, "conflict_count")?,
        needs_human: json_u32_field(row, "needs_human_count")?,
    })
}

pub fn read_local_sync_snapshot_from_connection(
    conn: &Connection,
    now: &str,
) -> Result<LocalSyncSnapshot, String> {
    let mut stmt = conn
        .prepare(local_sync_snapshot_sql())
        .map_err(|err| format!("无法准备同步快照查询: {err}"))?;
    stmt.query_row((MAX_SYNC_RETRIES, now), |row| {
        let pending: i64 = row.get(0)?;
        let deferred: i64 = row.get(1)?;
        let conflicts: i64 = row.get(2)?;
        let needs_human: i64 = row.get(3)?;

        Ok(LocalSyncSnapshot {
            pending: u32::try_from(pending)
                .map_err(|_| rusqlite::Error::IntegralValueOutOfRange(0, pending))?,
            deferred: u32::try_from(deferred)
                .map_err(|_| rusqlite::Error::IntegralValueOutOfRange(1, deferred))?,
            conflicts: u32::try_from(conflicts)
                .map_err(|_| rusqlite::Error::IntegralValueOutOfRange(2, conflicts))?,
            needs_human: u32::try_from(needs_human)
                .map_err(|_| rusqlite::Error::IntegralValueOutOfRange(3, needs_human))?,
        })
    })
    .map_err(|err| format!("无法读取同步快照: {err}"))
}

/// 同步引擎：处理本地与云端之间的数据同步
///
/// 架构设计：
/// - 控制面（始终在线）：OTA 更新、许可证验证、能力清单
/// - 数据面（按模式）：消息、文档、案件等业务数据
pub struct SyncEngine {
    state: SharedAppState,
    backend_url: String,
}

impl SyncEngine {
    pub fn new(state: SharedAppState, backend_url: String) -> Self {
        Self { state, backend_url }
    }

    /// 执行增量同步
    pub async fn sync(&self) -> Result<SyncResult, String> {
        let mode = {
            let s = self.state.read().await;
            s.mode
        };

        match mode {
            AppMode::TopSecret => {
                return Ok(SyncResult {
                    success: false,
                    pushed: 0,
                    pulled: 0,
                    conflicts: 0,
                    message: "绝密模式下不执行数据同步".to_string(),
                });
            }
            AppMode::Hybrid => self.sync_selective().await,
            AppMode::Cloud => self.sync_full().await,
        }
    }

    /// 选择性同步（混合模式）
    async fn sync_selective(&self) -> Result<SyncResult, String> {
        self.set_sync_status(SyncStatus::Syncing).await;

        // 1. 推送本地待同步数据
        let pushed = self.push_pending_records().await?;

        // 2. 拉取云端增量更新（仅用户标记为同步的内容）
        let pulled = self.pull_incremental_updates().await?;

        self.set_sync_status(SyncStatus::Idle).await;
        self.update_last_sync_time().await;

        Ok(SyncResult {
            success: true,
            pushed,
            pulled,
            conflicts: 0,
            message: "混合模式同步完成".to_string(),
        })
    }

    /// 全量同步（云端模式）
    async fn sync_full(&self) -> Result<SyncResult, String> {
        self.set_sync_status(SyncStatus::Syncing).await;

        let pushed = self.push_pending_records().await?;
        let pulled = self.pull_incremental_updates().await?;

        self.set_sync_status(SyncStatus::Idle).await;
        self.update_last_sync_time().await;

        Ok(SyncResult {
            success: true,
            pushed,
            pulled,
            conflicts: 0,
            message: "全量同步完成".to_string(),
        })
    }

    /// 推送本地待同步记录
    async fn push_pending_records(&self) -> Result<u32, String> {
        // TODO: 从 SQLite sync_log 查询 status='pending' 的记录
        // 然后 POST /api/v1/sync/push
        log::info!("推送待同步记录到: {}/api/v1/sync/push", self.backend_url);
        Ok(0)
    }

    /// 拉取云端增量更新
    async fn pull_incremental_updates(&self) -> Result<u32, String> {
        // TODO: GET /api/v1/sync/pull?since={last_sync_version}
        // 然后写入本地 SQLite
        log::info!("拉取增量更新从: {}/api/v1/sync/pull", self.backend_url);
        Ok(0)
    }

    /// 控制面心跳（所有模式都执行）
    pub async fn control_plane_heartbeat(&self) -> Result<(), String> {
        let backend_url = { self.state.read().await.backend_url.clone() };

        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .map_err(|e| e.to_string())?;

        match client
            .get(format!("{}/api/v1/health", backend_url))
            .send()
            .await
        {
            Ok(resp) => {
                let mut s = self.state.write().await;
                s.is_online = resp.status().is_success();
                Ok(())
            }
            Err(_) => {
                let mut s = self.state.write().await;
                s.is_online = false;
                Ok(())
            }
        }
    }

    async fn set_sync_status(&self, status: SyncStatus) {
        let mut s = self.state.write().await;
        s.sync_status = status;
    }

    async fn update_last_sync_time(&self) {
        let mut s = self.state.write().await;
        s.last_sync_time = Some(chrono::Utc::now().to_rfc3339());
    }
}

#[derive(Debug, serde::Serialize)]
pub struct SyncResult {
    pub success: bool,
    pub pushed: u32,
    pub pulled: u32,
    pub conflicts: u32,
    pub message: String,
}

#[cfg(test)]
mod tests {
    use super::{
        decode_local_sync_snapshot, read_local_sync_snapshot_from_connection, LocalSyncSnapshot,
    };
    use rusqlite::Connection;
    use serde_json::json;

    #[test]
    fn decode_local_sync_snapshot_reads_numeric_fields() {
        let rows = vec![json!({
            "pending_count": 2,
            "deferred_count": 1,
            "conflict_count": 3,
            "needs_human_count": 4
        })];

        let snapshot = decode_local_sync_snapshot(&rows).expect("decode local sync snapshot");

        assert_eq!(
            snapshot,
            LocalSyncSnapshot {
                pending: 2,
                deferred: 1,
                conflicts: 3,
                needs_human: 4,
            }
        );
    }

    #[test]
    fn local_sync_snapshot_query_reads_retryable_and_human_gated_rows() {
        let conn = Connection::open_in_memory().expect("open sqlite");
        conn.execute_batch(include_str!("../../migrations/001_offline_queue.sql"))
            .expect("init schema");
        conn.execute_batch(
            "INSERT INTO sync_log (entity_type, entity_id, action, status)
             VALUES
                ('message', 'm-1', 'update', 'pending'),
                ('message', 'm-2', 'update', 'failed'),
                ('message', 'm-3', 'update', 'failed'),
                ('message', 'm-4', 'update', 'conflict'),
                ('message', 'm-5', 'update', 'failed');
             UPDATE sync_log
             SET retry_count = 1,
                 next_retry_at = '2026-05-06T00:00:00.000Z'
             WHERE entity_id = 'm-2';
             UPDATE sync_log
             SET retry_count = 1,
                 next_retry_at = '2026-05-08T00:00:00.000Z'
             WHERE entity_id = 'm-3';
             UPDATE sync_log
             SET needs_human = 1,
                 error_message = 'needs review'
             WHERE entity_id = 'm-4';
             UPDATE sync_log
             SET retry_count = 3,
                 needs_human = 1,
                 error_message = 'manual fix'
             WHERE entity_id = 'm-5';",
        )
        .expect("seed sync log");

        let snapshot = read_local_sync_snapshot_from_connection(&conn, "2026-05-07T00:00:00.000Z")
            .expect("read local sync snapshot");

        assert_eq!(snapshot.pending, 2);
        assert_eq!(snapshot.deferred, 1);
        assert_eq!(snapshot.conflicts, 1);
        assert_eq!(snapshot.needs_human, 2);
    }
}
