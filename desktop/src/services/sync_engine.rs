#![allow(dead_code)]

use crate::models::{AppMode, SharedAppState, SyncStatus};
use chrono::TimeZone;
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::Map;
use serde_json::Value;
use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

pub const MAX_SYNC_RETRIES: i64 = 3;
pub const SYNC_BATCH_LIMIT: i64 = 100;
pub const LAST_SYNC_VERSION_KEY: &str = "sync.last_server_version";
pub const LAST_SYNC_TIME_KEY: &str = "sync.last_sync_time";
pub const DEVICE_ID_KEY: &str = "sync.device_id";

const SYNC_RETRY_DELAYS_SECONDS: [i64; 3] = [30, 120, 300];

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
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

#[derive(Debug, Clone, Serialize)]
pub struct DesktopSyncCodeSmokeReport {
    pub mode: &'static str,
    pub status: &'static str,
    pub release_evidence_complete: bool,
    pub checks: DesktopSyncCodeSmokeChecks,
    pub completion_note: &'static str,
}

#[derive(Debug, Clone, Serialize)]
pub struct DesktopSyncCodeSmokeChecks {
    pub sync_log_migration: &'static str,
    pub snapshot: LocalSyncSnapshot,
    pub pending_rows_decoded: usize,
    pub push_payload_records: usize,
    pub accepted_after_conflict: usize,
    pub conflict_rows: usize,
    pub retry_needs_human: bool,
    pub pull_records_decoded: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct DesktopSyncLoopbackSmokeReport {
    pub mode: &'static str,
    pub status: &'static str,
    pub release_evidence_complete: bool,
    pub checks: DesktopSyncLoopbackSmokeChecks,
    pub completion_note: &'static str,
}

#[derive(Debug, Clone, Serialize)]
pub struct DesktopSyncLoopbackSmokeChecks {
    pub loopback_backend: &'static str,
    pub auth_header_received: bool,
    pub pending_rows_decoded: usize,
    pub push_payload_records: usize,
    pub backend_received_records: usize,
    pub accepted_after_conflict: usize,
    pub conflict_rows: usize,
    pub rows_synced: u32,
    pub rows_conflicted: u32,
    pub pull_records_written: usize,
    pub cursor_advanced_to: i64,
    pub retry_needs_human: bool,
}

#[derive(Debug, Default)]
struct LoopbackBackendState {
    auth_header_received: bool,
    push_seen: bool,
    pull_seen: bool,
    received_records: usize,
}

#[derive(Debug)]
struct LoopbackHttpRequest {
    method: String,
    path: String,
    headers: HashMap<String, String>,
    body: Vec<u8>,
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

fn pending_sync_rows_from_connection(
    conn: &Connection,
    now: &str,
) -> Result<Vec<PendingSyncRow>, String> {
    let mut stmt = conn
        .prepare(pending_sync_rows_sql())
        .map_err(|err| format!("无法准备待同步行查询: {err}"))?;
    let rows = stmt
        .query_map((MAX_SYNC_RETRIES, now, SYNC_BATCH_LIMIT), |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, i64>(0)?,
                "entity_type": row.get::<_, String>(1)?,
                "entity_id": row.get::<_, String>(2)?,
                "action": row.get::<_, String>(3)?,
                "data_json": row.get::<_, Option<String>>(4)?,
                "timestamp": row.get::<_, Option<String>>(5)?,
                "retry_count": row.get::<_, Option<i64>>(6)?.unwrap_or(0),
            }))
        })
        .map_err(|err| format!("无法读取待同步行: {err}"))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|err| format!("无法转换待同步行: {err}"))?;

    decode_pending_sync_rows(&rows)
}

pub fn desktop_sync_code_smoke_report() -> Result<DesktopSyncCodeSmokeReport, String> {
    let conn = Connection::open_in_memory().map_err(|err| format!("无法创建内存同步库: {err}"))?;
    conn.execute_batch(include_str!("../../migrations/001_offline_queue.sql"))
        .map_err(|err| format!("无法应用同步迁移: {err}"))?;
    conn.execute_batch(
        r#"
        INSERT INTO sync_log (entity_type, entity_id, action, data_json, timestamp, status, retry_count, next_retry_at, needs_human)
        VALUES
            ('message', 'msg-pending', 'update', '{"content":"pending","sync_version":7}', '2026-05-09T00:00:00Z', 'pending', 0, NULL, 0),
            ('document', 'doc-retry', 'update', '{"title":"retry","syncVersion":"8"}', '2026-05-09T00:01:00Z', 'failed', 1, '2026-05-09T00:02:00Z', 0),
            ('case', 'case-deferred', 'update', '{"title":"deferred"}', '2026-05-09T00:03:00Z', 'failed', 1, '2026-05-10T00:00:00Z', 0),
            ('contract', 'contract-conflict', 'update', '{"title":"conflict"}', '2026-05-09T00:04:00Z', 'conflict', 0, NULL, 1);
        "#,
    )
    .map_err(|err| format!("无法写入同步 smoke 数据: {err}"))?;

    let now = "2026-05-09T12:00:00Z";
    let snapshot = read_local_sync_snapshot_from_connection(&conn, now)?;
    let expected_snapshot = LocalSyncSnapshot {
        pending: 2,
        deferred: 1,
        conflicts: 1,
        needs_human: 1,
    };
    if snapshot != expected_snapshot {
        return Err(format!("同步快照 smoke 结果不符合预期: {snapshot:?}"));
    }

    let pending_rows = pending_sync_rows_from_connection(&conn, now)?;
    if pending_rows.len() != 2 {
        return Err(format!(
            "待同步行 smoke 数量不符合预期: {}",
            pending_rows.len()
        ));
    }

    let push_records = pending_rows
        .iter()
        .map(pending_row_to_push_record)
        .collect::<Vec<_>>();
    let payload = build_sync_push_payload(push_records, "device-smoke".to_string(), 11);
    if payload.records.len() != 2 || payload.last_sync_version != 11 {
        return Err("同步 push payload smoke 不符合预期".to_string());
    }

    let mut conflict = Map::new();
    conflict.insert(
        "entity_type".to_string(),
        Value::String(pending_rows[0].entity_type.clone()),
    );
    conflict.insert(
        "entity_id".to_string(),
        Value::String(pending_rows[0].entity_id.clone()),
    );
    let conflicts = vec![conflict];
    let accepted_ids = accepted_row_ids(&pending_rows, &conflicts);
    if accepted_ids != vec![pending_rows[1].id] {
        return Err(format!(
            "同步冲突 accepted row smoke 不符合预期: {accepted_ids:?}"
        ));
    }

    let retry_state = sync_retry_state(
        2,
        chrono::Utc
            .with_ymd_and_hms(2026, 5, 9, 12, 0, 0)
            .single()
            .ok_or_else(|| "无法构造同步 retry smoke 时间".to_string())?,
    );
    if !retry_state.needs_human || retry_state.next_retry_at.is_some() {
        return Err("同步 retry needs_human smoke 不符合预期".to_string());
    }

    let pull_body = serde_json::from_value::<SyncPullResponseBody>(serde_json::json!({
        "server_version": 12,
        "has_more": false,
        "records": [
            {
                "entity_type": "message",
                "entity_id": "msg-remote",
                "action": "upsert",
                "data": {"content": "remote"},
                "version": 12
            }
        ]
    }))
    .map_err(|err| format!("同步 pull response smoke 解码失败: {err}"))?;
    let pull_records_decoded = pull_body.records.unwrap_or_default().len();
    if pull_records_decoded != 1 || pull_body.server_version != Some(12) {
        return Err("同步 pull response smoke 不符合预期".to_string());
    }

    Ok(DesktopSyncCodeSmokeReport {
        mode: "desktop_sync_code_smoke",
        status: "passed",
        release_evidence_complete: false,
        checks: DesktopSyncCodeSmokeChecks {
            sync_log_migration: "passed",
            snapshot,
            pending_rows_decoded: pending_rows.len(),
            push_payload_records: payload.records.len(),
            accepted_after_conflict: accepted_ids.len(),
            conflict_rows: conflicts.len(),
            retry_needs_human: retry_state.needs_human,
            pull_records_decoded,
        },
        completion_note: "Packaged-binary sync code smoke only; signed runtime/backend/device evidence remains pending.",
    })
}

pub fn desktop_sync_loopback_smoke_report() -> Result<DesktopSyncLoopbackSmokeReport, String> {
    let listener = TcpListener::bind("127.0.0.1:0")
        .map_err(|err| format!("无法启动同步 loopback 后端: {err}"))?;
    listener
        .set_nonblocking(true)
        .map_err(|err| format!("无法设置同步 loopback 非阻塞模式: {err}"))?;
    let addr = listener
        .local_addr()
        .map_err(|err| format!("无法读取同步 loopback 地址: {err}"))?;
    let backend_state = Arc::new(Mutex::new(LoopbackBackendState::default()));
    let server_state = Arc::clone(&backend_state);
    let server = std::thread::spawn(move || run_sync_loopback_backend(listener, server_state));

    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|err| format!("无法创建同步 loopback runtime: {err}"))?;
    let client_checks = runtime.block_on(run_sync_loopback_client(addr))?;
    let server_result = server
        .join()
        .map_err(|_| "同步 loopback 后端线程异常退出".to_string())?;
    server_result?;

    let observed = backend_state
        .lock()
        .map_err(|_| "同步 loopback 后端状态锁已损坏".to_string())?;
    if !observed.push_seen || !observed.pull_seen {
        return Err("同步 loopback 后端没有收到 push/pull 全流程请求".to_string());
    }
    if observed.received_records != client_checks.push_payload_records {
        return Err(format!(
            "同步 loopback 后端收到记录数不符合预期: expected {}, got {}",
            client_checks.push_payload_records, observed.received_records
        ));
    }

    Ok(DesktopSyncLoopbackSmokeReport {
        mode: "desktop_sync_loopback_smoke",
        status: "passed",
        release_evidence_complete: false,
        checks: DesktopSyncLoopbackSmokeChecks {
            loopback_backend: "passed",
            auth_header_received: observed.auth_header_received,
            backend_received_records: observed.received_records,
            ..client_checks
        },
        completion_note: "Packaged-binary sync loopback smoke only; signed runtime, shared staging backend, and device evidence remain pending.",
    })
}

async fn run_sync_loopback_client(
    addr: SocketAddr,
) -> Result<DesktopSyncLoopbackSmokeChecks, String> {
    let conn = Connection::open_in_memory()
        .map_err(|err| format!("无法创建同步 loopback 本地库: {err}"))?;
    conn.execute_batch(include_str!("../../migrations/001_offline_queue.sql"))
        .map_err(|err| format!("无法应用同步 loopback 迁移: {err}"))?;
    conn.execute_batch(
        r#"
        INSERT INTO sync_log (entity_type, entity_id, action, data_json, timestamp, status, retry_count, next_retry_at, needs_human)
        VALUES
            ('message', 'msg-loopback-conflict', 'update', '{"content":"local conflict","sync_version":7}', '2026-05-09T00:00:00Z', 'pending', 0, NULL, 0),
            ('document', 'doc-loopback-accepted', 'update', '{"title":"local accepted","syncVersion":"8"}', '2026-05-09T00:01:00Z', 'failed', 1, '2026-05-09T00:02:00Z', 0),
            ('case', 'case-loopback-deferred', 'update', '{"title":"deferred"}', '2026-05-09T00:03:00Z', 'failed', 1, '2026-05-10T00:00:00Z', 0);
        "#,
    )
    .map_err(|err| format!("无法写入同步 loopback 本地数据: {err}"))?;

    let now = "2026-05-09T12:00:00Z";
    let pending_rows = pending_sync_rows_from_connection(&conn, now)?;
    let push_records = pending_rows
        .iter()
        .map(pending_row_to_push_record)
        .collect::<Vec<_>>();
    let payload = build_sync_push_payload(push_records, "device-loopback".to_string(), 11);
    let api_base = format!("http://{addr}/api/v1");
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|err| format!("无法创建同步 loopback HTTP 客户端: {err}"))?;

    let push_response = client
        .post(format!("{api_base}/sync/push"))
        .bearer_auth("loopback-token")
        .json(&payload)
        .send()
        .await
        .map_err(|err| format!("同步 loopback push 请求失败: {err}"))?;
    if !push_response.status().is_success() {
        return Err(format!(
            "同步 loopback push 响应异常: {}",
            push_response.status().as_u16()
        ));
    }
    let push_body = push_response
        .json::<SyncPushResponseBody>()
        .await
        .map_err(|err| format!("同步 loopback push 响应解码失败: {err}"))?;
    let conflicts = push_body.conflicts.unwrap_or_default();
    let accepted_ids = accepted_row_ids(&pending_rows, &conflicts);
    for id in &accepted_ids {
        conn.execute(
            "UPDATE sync_log SET status='synced', error_message=NULL WHERE id=?1",
            [id],
        )
        .map_err(|err| format!("无法标记同步 loopback accepted 行: {err}"))?;
    }
    for conflict in &conflicts {
        let entity_type = conflict
            .get("entity_type")
            .and_then(Value::as_str)
            .unwrap_or("");
        let entity_id = conflict
            .get("entity_id")
            .and_then(Value::as_str)
            .unwrap_or("");
        conn.execute(
            "UPDATE sync_log SET status='conflict', needs_human=1, error_message='loopback conflict' WHERE entity_type=?1 AND entity_id=?2",
            (entity_type, entity_id),
        )
        .map_err(|err| format!("无法标记同步 loopback conflict 行: {err}"))?;
    }
    let push_server_version = push_body.server_version.unwrap_or(11).max(11);
    write_sync_loopback_setting(
        &conn,
        LAST_SYNC_VERSION_KEY,
        &push_server_version.to_string(),
    )?;

    let pull_response = client
        .get(format!(
            "{api_base}/sync/pull?since_version={push_server_version}&limit={SYNC_BATCH_LIMIT}"
        ))
        .bearer_auth("loopback-token")
        .send()
        .await
        .map_err(|err| format!("同步 loopback pull 请求失败: {err}"))?;
    if !pull_response.status().is_success() {
        return Err(format!(
            "同步 loopback pull 响应异常: {}",
            pull_response.status().as_u16()
        ));
    }
    let pull_body = pull_response
        .json::<SyncPullResponseBody>()
        .await
        .map_err(|err| format!("同步 loopback pull 响应解码失败: {err}"))?;
    let mut cursor = push_server_version;
    let mut pull_records_written = 0_usize;
    for record in pull_body.records.unwrap_or_default() {
        apply_sync_loopback_remote_record(&conn, &record)?;
        cursor = cursor.max(record.server_version.or(record.version).unwrap_or(cursor));
        pull_records_written += 1;
    }
    cursor = cursor.max(pull_body.server_version.unwrap_or(cursor));
    write_sync_loopback_setting(&conn, LAST_SYNC_VERSION_KEY, &cursor.to_string())?;

    let rows_synced = count_sync_loopback_rows(&conn, "synced")?;
    let rows_conflicted = count_sync_loopback_rows(&conn, "conflict")?;
    let stored_cursor = read_sync_loopback_setting(&conn, LAST_SYNC_VERSION_KEY)?;
    if stored_cursor != cursor.to_string() {
        return Err(format!(
            "同步 loopback cursor 未写回: expected {cursor}, got {stored_cursor}"
        ));
    }
    let remote_doc_count: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM local_documents WHERE id='doc-loopback-remote' AND synced=1 AND sync_version=?1",
            [cursor],
            |row| row.get(0),
        )
        .map_err(|err| format!("无法验证同步 loopback pull 写回: {err}"))?;
    if remote_doc_count != 1 {
        return Err("同步 loopback pull 没有写入远端文档".to_string());
    }

    let retry_state = sync_retry_state(
        2,
        chrono::Utc
            .with_ymd_and_hms(2026, 5, 9, 12, 0, 0)
            .single()
            .ok_or_else(|| "无法构造同步 loopback retry 时间".to_string())?,
    );

    Ok(DesktopSyncLoopbackSmokeChecks {
        loopback_backend: "passed",
        auth_header_received: false,
        pending_rows_decoded: pending_rows.len(),
        push_payload_records: payload.records.len(),
        backend_received_records: 0,
        accepted_after_conflict: accepted_ids.len(),
        conflict_rows: conflicts.len(),
        rows_synced,
        rows_conflicted,
        pull_records_written,
        cursor_advanced_to: cursor,
        retry_needs_human: retry_state.needs_human,
    })
}

fn run_sync_loopback_backend(
    listener: TcpListener,
    backend_state: Arc<Mutex<LoopbackBackendState>>,
) -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_secs(15);
    let mut handled = 0_usize;
    while handled < 2 && Instant::now() < deadline {
        match listener.accept() {
            Ok((mut stream, _)) => {
                handle_sync_loopback_request(&mut stream, &backend_state)?;
                handled += 1;
            }
            Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                std::thread::sleep(Duration::from_millis(10));
            }
            Err(err) => return Err(format!("同步 loopback 后端接收请求失败: {err}")),
        }
    }
    if handled != 2 {
        return Err(format!("同步 loopback 后端请求数量不足: {handled}/2"));
    }
    Ok(())
}

fn handle_sync_loopback_request(
    stream: &mut TcpStream,
    backend_state: &Arc<Mutex<LoopbackBackendState>>,
) -> Result<(), String> {
    let request = read_loopback_http_request(stream)?;
    if request.method == "POST" && request.path == "/api/v1/sync/push" {
        let payload = serde_json::from_slice::<Value>(&request.body)
            .map_err(|err| format!("同步 loopback 后端无法解码 push body: {err}"))?;
        let records = payload
            .get("records")
            .and_then(Value::as_array)
            .ok_or_else(|| "同步 loopback push body 缺少 records".to_string())?;
        {
            let mut observed = backend_state
                .lock()
                .map_err(|_| "同步 loopback 后端状态锁已损坏".to_string())?;
            observed.push_seen = true;
            observed.received_records = records.len();
            observed.auth_header_received = request
                .headers
                .get("authorization")
                .is_some_and(|header| header == "Bearer loopback-token");
        }
        return write_loopback_json_response(
            stream,
            200,
            serde_json::json!({
                "accepted": 1,
                "rejected": 1,
                "conflicts": [
                    {
                        "entity_type": "message",
                        "entity_id": "msg-loopback-conflict",
                        "reason": "remote_newer"
                    }
                ],
                "server_version": 12
            }),
        );
    }

    if request.method == "GET" && request.path == "/api/v1/sync/pull" {
        {
            let mut observed = backend_state
                .lock()
                .map_err(|_| "同步 loopback 后端状态锁已损坏".to_string())?;
            observed.pull_seen = true;
            observed.auth_header_received = observed.auth_header_received
                && request
                    .headers
                    .get("authorization")
                    .is_some_and(|header| header == "Bearer loopback-token");
        }
        return write_loopback_json_response(
            stream,
            200,
            serde_json::json!({
                "server_version": 13,
                "has_more": false,
                "records": [
                    {
                        "entity_type": "document",
                        "entity_id": "doc-loopback-remote",
                        "action": "upsert",
                        "data": {
                            "title": "Loopback remote document",
                            "content": "remote pull payload"
                        },
                        "version": 13,
                        "server_version": 13
                    }
                ]
            }),
        );
    }

    write_loopback_json_response(
        stream,
        404,
        serde_json::json!({"error": "unexpected loopback request"}),
    )
}

fn read_loopback_http_request(stream: &mut TcpStream) -> Result<LoopbackHttpRequest, String> {
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .map_err(|err| format!("无法设置同步 loopback 读取超时: {err}"))?;
    let mut buffer = Vec::new();
    let mut chunk = [0_u8; 4096];
    let mut header_end = None;
    let mut content_length = 0_usize;
    loop {
        let read = stream
            .read(&mut chunk)
            .map_err(|err| format!("同步 loopback 读取请求失败: {err}"))?;
        if read == 0 {
            break;
        }
        buffer.extend_from_slice(&chunk[..read]);
        if header_end.is_none() {
            header_end = find_header_end(&buffer);
            if let Some(end) = header_end {
                let headers = String::from_utf8_lossy(&buffer[..end]);
                content_length = parse_content_length(&headers)?;
            }
        }
        if let Some(end) = header_end {
            if buffer.len() >= end + 4 + content_length {
                break;
            }
        }
    }

    let end = header_end.ok_or_else(|| "同步 loopback 请求缺少 HTTP 头".to_string())?;
    let header_text = String::from_utf8_lossy(&buffer[..end]);
    let mut lines = header_text.lines();
    let request_line = lines
        .next()
        .ok_or_else(|| "同步 loopback 请求行缺失".to_string())?;
    let mut request_parts = request_line.split_whitespace();
    let method = request_parts
        .next()
        .ok_or_else(|| "同步 loopback 请求方法缺失".to_string())?
        .to_string();
    let raw_path = request_parts
        .next()
        .ok_or_else(|| "同步 loopback 请求路径缺失".to_string())?;
    let path = raw_path.split('?').next().unwrap_or(raw_path).to_string();
    let mut headers = HashMap::new();
    for line in lines {
        let Some((key, value)) = line.split_once(':') else {
            continue;
        };
        headers.insert(key.trim().to_ascii_lowercase(), value.trim().to_string());
    }
    let body_start = end + 4;
    let body_end = body_start + content_length;
    let body = if body_end <= buffer.len() {
        buffer[body_start..body_end].to_vec()
    } else {
        Vec::new()
    };
    Ok(LoopbackHttpRequest {
        method,
        path,
        headers,
        body,
    })
}

fn find_header_end(buffer: &[u8]) -> Option<usize> {
    buffer.windows(4).position(|window| window == b"\r\n\r\n")
}

fn parse_content_length(headers: &str) -> Result<usize, String> {
    for line in headers.lines() {
        let Some((key, value)) = line.split_once(':') else {
            continue;
        };
        if key.trim().eq_ignore_ascii_case("content-length") {
            return value
                .trim()
                .parse::<usize>()
                .map_err(|err| format!("同步 loopback Content-Length 无效: {err}"));
        }
    }
    Ok(0)
}

fn write_loopback_json_response(
    stream: &mut TcpStream,
    status: u16,
    body: Value,
) -> Result<(), String> {
    let reason = if status == 200 { "OK" } else { "Not Found" };
    let body =
        serde_json::to_vec(&body).map_err(|err| format!("同步 loopback 响应编码失败: {err}"))?;
    let header = format!(
        "HTTP/1.1 {status} {reason}\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n",
        body.len()
    );
    stream
        .write_all(header.as_bytes())
        .and_then(|_| stream.write_all(&body))
        .map_err(|err| format!("同步 loopback 写入响应失败: {err}"))
}

fn write_sync_loopback_setting(conn: &Connection, key: &str, value: &str) -> Result<(), String> {
    conn.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?1, ?2, CURRENT_TIMESTAMP)
         ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
        (key, value),
    )
    .map_err(|err| format!("无法写入同步 loopback 设置: {err}"))?;
    Ok(())
}

fn read_sync_loopback_setting(conn: &Connection, key: &str) -> Result<String, String> {
    conn.query_row(
        "SELECT value FROM app_settings WHERE key=?1",
        [key],
        |row| row.get(0),
    )
    .map_err(|err| format!("无法读取同步 loopback 设置: {err}"))
}

fn count_sync_loopback_rows(conn: &Connection, status: &str) -> Result<u32, String> {
    let count: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM sync_log WHERE status=?1",
            [status],
            |row| row.get(0),
        )
        .map_err(|err| format!("无法统计同步 loopback 行: {err}"))?;
    u32::try_from(count).map_err(|_| "同步 loopback 行数超出范围".to_string())
}

fn apply_sync_loopback_remote_record(
    conn: &Connection,
    record: &RemoteSyncRecord,
) -> Result<(), String> {
    match record.entity_type.as_str() {
        "document" => {
            let title = record
                .data
                .get("title")
                .and_then(Value::as_str)
                .unwrap_or("Untitled remote document");
            let content = record
                .data
                .get("content")
                .and_then(Value::as_str)
                .unwrap_or("");
            let version = record.server_version.or(record.version).unwrap_or(0);
            conn.execute(
                "INSERT INTO local_documents (id, title, content, synced, sync_version, updated_at)
                 VALUES (?1, ?2, ?3, 1, ?4, CURRENT_TIMESTAMP)
                 ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    content=excluded.content,
                    synced=1,
                    sync_version=excluded.sync_version,
                    updated_at=CURRENT_TIMESTAMP",
                (&record.entity_id, title, content, version),
            )
            .map_err(|err| format!("无法写入同步 loopback 远端文档: {err}"))?;
            Ok(())
        }
        other => Err(format!("同步 loopback 不支持的远端记录类型: {other}")),
    }
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
