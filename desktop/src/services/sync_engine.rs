#![allow(dead_code)]

use crate::models::{AppMode, SharedAppState, SyncStatus};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::Map;
use serde_json::Value;

pub const MAX_SYNC_RETRIES: i64 = 3;
pub const SYNC_BATCH_LIMIT: i64 = 100;
pub const LAST_SYNC_VERSION_KEY: &str = "sync.last_server_version";
pub const LAST_SYNC_TIME_KEY: &str = "sync.last_sync_time";
pub const DEVICE_ID_KEY: &str = "sync.device_id";

const SYNC_RETRY_DELAYS_SECONDS: [i64; 3] = [30, 120, 300];

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct LocalSyncSnapshot {
    pub pending: u32,
    pub deferred: u32,
    pub conflicts: u32,
    pub needs_human: u32,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PendingSyncRow {
    pub id: i64,
    pub entity_type: String,
    pub entity_id: String,
    pub action: String,
    pub data: Map<String, Value>,
    pub timestamp: String,
    pub version: i64,
    pub retry_count: i64,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct SyncPushRecord {
    pub entity_type: String,
    pub entity_id: String,
    pub action: String,
    pub data: Map<String, Value>,
    pub timestamp: String,
    pub version: i64,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct SyncPushPayload {
    pub records: Vec<SyncPushRecord>,
    pub device_id: String,
    pub last_sync_version: i64,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SyncPushResponseBody {
    pub accepted: Option<u32>,
    pub rejected: Option<u32>,
    pub conflicts: Option<Vec<Map<String, Value>>>,
    pub server_version: Option<i64>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct SyncPullResponseBody {
    pub records: Option<Vec<RemoteSyncRecord>>,
    pub server_version: Option<i64>,
    pub has_more: Option<bool>,
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct RemoteSyncRecord {
    pub entity_type: String,
    pub entity_id: String,
    pub action: String,
    #[serde(default)]
    pub data: Map<String, Value>,
    #[serde(default)]
    pub timestamp: Option<String>,
    #[serde(default)]
    pub version: Option<i64>,
    #[serde(default)]
    pub server_version: Option<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyncRetryState {
    pub retry_count: i64,
    pub next_retry_at: Option<String>,
    pub needs_human: bool,
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

fn json_i64_field(row: &Value, key: &str) -> Result<i64, String> {
    let value = row
        .get(key)
        .ok_or_else(|| format!("同步行缺少字段: {key}"))?;

    if let Some(number) = value.as_i64() {
        return Ok(number);
    }
    if let Some(number) = value.as_u64() {
        return i64::try_from(number).map_err(|_| format!("同步行字段 {key} 超出范围"));
    }
    if let Some(number) = value.as_str() {
        return number
            .parse::<i64>()
            .map_err(|err| format!("同步行字段 {key} 解析失败: {err}"));
    }

    Err(format!("同步行字段 {key} 类型无效"))
}

fn json_optional_i64_field(row: &Value, key: &str) -> Result<Option<i64>, String> {
    if row.get(key).is_none_or(Value::is_null) {
        return Ok(None);
    }
    json_i64_field(row, key).map(Some)
}

fn json_string_field(row: &Value, key: &str) -> Result<String, String> {
    row.get(key)
        .and_then(Value::as_str)
        .map(str::to_string)
        .ok_or_else(|| format!("同步行字段 {key} 必须是字符串"))
}

fn json_optional_string_field(row: &Value, key: &str) -> Option<String> {
    row.get(key).and_then(Value::as_str).map(str::to_string)
}

fn parse_data_json(value: Option<String>) -> Map<String, Value> {
    let Some(raw) = value.filter(|item| !item.trim().is_empty()) else {
        return Map::new();
    };
    match serde_json::from_str::<Value>(&raw) {
        Ok(Value::Object(map)) => map,
        Ok(other) => {
            let mut map = Map::new();
            map.insert("value".to_string(), other);
            map
        }
        Err(_) => Map::new(),
    }
}

pub fn sync_record_version_from_data(data: &Map<String, Value>) -> i64 {
    data.get("sync_version")
        .or_else(|| data.get("syncVersion"))
        .and_then(|value| {
            value
                .as_i64()
                .or_else(|| value.as_u64().and_then(|number| i64::try_from(number).ok()))
                .or_else(|| value.as_str().and_then(|number| number.parse::<i64>().ok()))
        })
        .unwrap_or(0)
}

pub fn pending_sync_rows_sql() -> &'static str {
    r#"
    SELECT id, entity_type, entity_id, action, data_json, timestamp, retry_count
    FROM sync_log
    WHERE (
        status = 'pending'
        OR (
            status = 'failed'
            AND COALESCE(needs_human, 0) = 0
            AND COALESCE(retry_count, 0) < ?1
            AND (next_retry_at IS NULL OR next_retry_at <= ?2)
        )
    )
    ORDER BY id ASC
    LIMIT ?3
    "#
}

pub fn decode_pending_sync_rows(rows: &[Value]) -> Result<Vec<PendingSyncRow>, String> {
    rows.iter()
        .map(|row| {
            let data = parse_data_json(json_optional_string_field(row, "data_json"));
            let version = json_optional_i64_field(row, "version")?
                .unwrap_or_else(|| sync_record_version_from_data(&data));
            Ok(PendingSyncRow {
                id: json_i64_field(row, "id")?,
                entity_type: json_string_field(row, "entity_type")?,
                entity_id: json_string_field(row, "entity_id")?,
                action: json_string_field(row, "action")?,
                timestamp: json_optional_string_field(row, "timestamp")
                    .unwrap_or_else(|| chrono::Utc::now().to_rfc3339()),
                retry_count: json_optional_i64_field(row, "retry_count")?.unwrap_or(0),
                data,
                version,
            })
        })
        .collect()
}

pub fn build_sync_push_payload(
    records: Vec<SyncPushRecord>,
    device_id: String,
    last_sync_version: i64,
) -> SyncPushPayload {
    SyncPushPayload {
        records,
        device_id,
        last_sync_version: last_sync_version.max(0),
    }
}

pub fn pending_row_to_push_record(row: &PendingSyncRow) -> SyncPushRecord {
    SyncPushRecord {
        entity_type: row.entity_type.clone(),
        entity_id: row.entity_id.clone(),
        action: row.action.clone(),
        data: row.data.clone(),
        timestamp: row.timestamp.clone(),
        version: row.version,
    }
}

fn conflict_key(conflict: &Map<String, Value>) -> Option<String> {
    let entity_type = conflict.get("entity_type")?.as_str()?;
    let entity_id = conflict.get("entity_id")?.as_str()?;
    Some(format!("{entity_type}:{entity_id}"))
}

pub fn accepted_row_ids(rows: &[PendingSyncRow], conflicts: &[Map<String, Value>]) -> Vec<i64> {
    let conflict_keys = conflicts
        .iter()
        .filter_map(conflict_key)
        .collect::<std::collections::HashSet<_>>();

    rows.iter()
        .filter(|row| !conflict_keys.contains(&format!("{}:{}", row.entity_type, row.entity_id)))
        .map(|row| row.id)
        .collect()
}

pub fn sync_retry_state(
    current_retry_count: i64,
    now: chrono::DateTime<chrono::Utc>,
) -> SyncRetryState {
    let retry_count = current_retry_count.saturating_add(1);
    let needs_human = retry_count >= MAX_SYNC_RETRIES;
    let next_retry_at = if needs_human {
        None
    } else {
        let delay_index = retry_count
            .saturating_sub(1)
            .try_into()
            .unwrap_or(0usize)
            .min(SYNC_RETRY_DELAYS_SECONDS.len().saturating_sub(1));
        Some((now + chrono::Duration::seconds(SYNC_RETRY_DELAYS_SECONDS[delay_index])).to_rfc3339())
    };

    SyncRetryState {
        retry_count,
        next_retry_at,
        needs_human,
    }
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
            AppMode::TopSecret => Ok(SyncResult {
                success: false,
                pushed: 0,
                pulled: 0,
                conflicts: 0,
                message: "绝密模式下不执行数据同步".to_string(),
            }),
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
        log::info!("推送待同步记录到: {}/api/v1/sync/push", self.backend_url);
        self.set_sync_status(SyncStatus::Error).await;
        Err(
            "Rust 同步引擎数据面未启用；请使用前端 Tauri bridge 的 SQLCipher 本地同步路径"
                .to_string(),
        )
    }

    /// 拉取云端增量更新
    async fn pull_incremental_updates(&self) -> Result<u32, String> {
        log::info!("拉取增量更新从: {}/api/v1/sync/pull", self.backend_url);
        self.set_sync_status(SyncStatus::Error).await;
        Err(
            "Rust 同步引擎数据面未启用；请使用前端 Tauri bridge 的 SQLCipher 本地同步路径"
                .to_string(),
        )
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
        accepted_row_ids, build_sync_push_payload, decode_local_sync_snapshot,
        decode_pending_sync_rows, pending_row_to_push_record,
        read_local_sync_snapshot_from_connection, sync_retry_state, LocalSyncSnapshot, SyncEngine,
    };
    use crate::models::{create_shared_state, AppMode, SyncStatus};
    use chrono::TimeZone;
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

    #[test]
    fn decode_pending_rows_builds_push_payload_without_local_log_id() {
        let rows = vec![json!({
            "id": 42,
            "entity_type": "document",
            "entity_id": "doc-1",
            "action": "update",
            "data_json": "{\"title\":\"合同\",\"sync_version\":7}",
            "timestamp": "2026-05-09T00:00:00Z",
            "retry_count": 1
        })];

        let pending = decode_pending_sync_rows(&rows).expect("decode pending rows");
        assert_eq!(pending.len(), 1);
        assert_eq!(pending[0].id, 42);
        assert_eq!(pending[0].version, 7);

        let payload = build_sync_push_payload(
            pending.iter().map(pending_row_to_push_record).collect(),
            "desktop-a".to_string(),
            12,
        );
        let encoded = serde_json::to_value(&payload).expect("serialize push payload");

        assert_eq!(encoded["device_id"], "desktop-a");
        assert_eq!(encoded["last_sync_version"], 12);
        assert_eq!(encoded["records"][0]["entity_id"], "doc-1");
        assert!(encoded["records"][0].get("id").is_none());
    }

    #[test]
    fn accepted_row_ids_excludes_conflicted_entities() {
        let rows = decode_pending_sync_rows(&[
            json!({
                "id": 1,
                "entity_type": "message",
                "entity_id": "m-1",
                "action": "update",
                "timestamp": "2026-05-09T00:00:00Z"
            }),
            json!({
                "id": 2,
                "entity_type": "message",
                "entity_id": "m-2",
                "action": "update",
                "timestamp": "2026-05-09T00:00:00Z"
            }),
        ])
        .expect("decode pending rows");
        let conflicts = vec![json!({
            "entity_type": "message",
            "entity_id": "m-2",
            "remote_data": {"content": "cloud"}
        })
        .as_object()
        .expect("conflict object")
        .clone()];

        assert_eq!(accepted_row_ids(&rows, &conflicts), vec![1]);
    }

    #[test]
    fn retry_state_uses_bounded_backoff_and_human_gate() {
        let now = chrono::Utc
            .with_ymd_and_hms(2026, 5, 9, 0, 0, 0)
            .single()
            .expect("valid datetime");

        let first = sync_retry_state(0, now);
        assert_eq!(first.retry_count, 1);
        assert_eq!(
            first.next_retry_at.as_deref(),
            Some("2026-05-09T00:00:30+00:00")
        );
        assert!(!first.needs_human);

        let final_retry = sync_retry_state(2, now);
        assert_eq!(final_retry.retry_count, 3);
        assert!(final_retry.next_retry_at.is_none());
        assert!(final_retry.needs_human);
    }

    #[tokio::test]
    async fn cloud_sync_fails_closed_when_rust_data_plane_is_not_enabled() {
        let state = create_shared_state();
        {
            let mut s = state.write().await;
            s.mode = AppMode::Cloud;
        }
        let engine = SyncEngine::new(state.clone(), "http://localhost:8001".to_string());

        let result = engine.sync().await;

        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Rust 同步引擎数据面未启用"));
        let s = state.read().await;
        assert_eq!(s.sync_status, SyncStatus::Error);
        assert!(s.last_sync_time.is_none());
    }
}
