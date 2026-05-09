use crate::commands::privacy_guard::ensure_data_network_allowed;
use crate::models::{AppMode, SharedAppState, SyncStatus};
use crate::services::{offline_queue, secure_db, sync_engine};
use serde_json::{json, Map, Value};
use std::time::Duration;
use tauri::{AppHandle, State};

fn read_local_sync_snapshot(app: &AppHandle) -> Result<sync_engine::LocalSyncSnapshot, String> {
    let rows = secure_db::select(
        app,
        sync_engine::local_sync_snapshot_sql(),
        vec![
            serde_json::Value::from(sync_engine::MAX_SYNC_RETRIES),
            serde_json::Value::String(chrono::Utc::now().to_rfc3339()),
        ],
    )?;
    sync_engine::decode_local_sync_snapshot(&rows)
}

fn read_offline_queue_stats(
    app: &AppHandle,
) -> Result<offline_queue::OfflineQueueStatsSnapshot, String> {
    let rows = secure_db::select(app, offline_queue::OfflineQueue::count_sql(), Vec::new())?;
    offline_queue::decode_queue_stats(&rows)
}

#[derive(Debug, Clone)]
struct PushOutcome {
    ok: bool,
    pushed: u32,
    conflicts: u32,
    deferred: u32,
    needs_human: u32,
    server_version: i64,
}

#[derive(Debug, Clone)]
struct PullOutcome {
    ok: bool,
    pulled: u32,
    server_version: i64,
}

fn sync_api_base(backend_url: &str) -> String {
    let trimmed = backend_url.trim().trim_end_matches('/');
    if trimmed.ends_with("/api/v1") {
        trimmed.to_string()
    } else if trimmed.ends_with("/api") {
        format!("{trimmed}/v1")
    } else {
        format!("{trimmed}/api/v1")
    }
}

fn read_setting(app: &AppHandle, key: &str) -> Result<Option<String>, String> {
    let rows = secure_db::select(
        app,
        "SELECT value FROM app_settings WHERE key = ?1",
        vec![Value::String(key.to_string())],
    )?;
    Ok(rows
        .first()
        .and_then(|row| row.get("value"))
        .and_then(Value::as_str)
        .map(str::to_string))
}

fn write_setting(app: &AppHandle, key: &str, value: &str) -> Result<(), String> {
    secure_db::execute(
        app,
        "INSERT OR REPLACE INTO app_settings (key, value, updated_at)
         VALUES (?1, ?2, CURRENT_TIMESTAMP)",
        vec![
            Value::String(key.to_string()),
            Value::String(value.to_string()),
        ],
    )?;
    Ok(())
}

fn read_last_sync_version(app: &AppHandle) -> Result<i64, String> {
    Ok(read_setting(app, sync_engine::LAST_SYNC_VERSION_KEY)?
        .and_then(|value| value.parse::<i64>().ok())
        .unwrap_or(0)
        .max(0))
}

fn write_last_sync_version(app: &AppHandle, version: i64) -> Result<(), String> {
    write_setting(
        app,
        sync_engine::LAST_SYNC_VERSION_KEY,
        &version.max(0).to_string(),
    )
}

fn get_or_create_device_id(app: &AppHandle) -> Result<String, String> {
    if let Some(device_id) = read_setting(app, sync_engine::DEVICE_ID_KEY)? {
        if !device_id.trim().is_empty() {
            return Ok(device_id);
        }
    }
    let device_id = uuid::Uuid::new_v4().to_string();
    write_setting(app, sync_engine::DEVICE_ID_KEY, &device_id)?;
    Ok(device_id)
}

fn read_pending_sync_rows(app: &AppHandle) -> Result<Vec<sync_engine::PendingSyncRow>, String> {
    let rows = secure_db::select(
        app,
        sync_engine::pending_sync_rows_sql(),
        vec![
            Value::from(sync_engine::MAX_SYNC_RETRIES),
            Value::String(chrono::Utc::now().to_rfc3339()),
            Value::from(sync_engine::SYNC_BATCH_LIMIT),
        ],
    )?;
    sync_engine::decode_pending_sync_rows(&rows)
}

fn first_object(rows: Vec<Value>) -> Map<String, Value> {
    rows.into_iter()
        .next()
        .and_then(|row| row.as_object().cloned())
        .unwrap_or_default()
}

fn read_entity_payload(
    app: &AppHandle,
    entity_type: &str,
    entity_id: &str,
) -> Result<Map<String, Value>, String> {
    let bind = vec![Value::String(entity_id.to_string())];
    let rows = match entity_type {
        "message" => secure_db::select(
            app,
            "SELECT id, conversation_id, content, role, agent, created_at, sync_version
             FROM local_messages WHERE id = ?1",
            bind,
        )?,
        "document" => secure_db::select(
            app,
            "SELECT id, title, content, file_path, file_size, mime_type, category, created_at, updated_at, sync_version
             FROM local_documents WHERE id = ?1",
            bind,
        )?,
        "conversation" => secure_db::select(
            app,
            "SELECT id, title, system_prompt, model, mode, created_at, updated_at, sync_version
             FROM local_conversations WHERE id = ?1",
            bind,
        )?,
        "case" => secure_db::select(
            app,
            "SELECT id, title, description, status, case_type, priority, data_json, created_at, updated_at, sync_version
             FROM local_cases WHERE id = ?1",
            bind,
        )?,
        "contract" => secure_db::select(
            app,
            "SELECT id, title, content, contract_type, status, parties_json, review_result_json, created_at, updated_at, sync_version
             FROM local_contracts WHERE id = ?1",
            bind,
        )?,
        "setting" => {
            let value = read_setting(app, entity_id)?;
            let mut map = Map::new();
            if let Some(value) = value {
                map.insert("key".to_string(), Value::String(entity_id.to_string()));
                map.insert("value".to_string(), Value::String(value));
            }
            return Ok(map);
        }
        _ => Vec::new(),
    };
    Ok(first_object(rows))
}

fn hydrate_pending_records(
    app: &AppHandle,
    rows: &[sync_engine::PendingSyncRow],
) -> Result<Vec<sync_engine::SyncPushRecord>, String> {
    rows.iter()
        .map(|row| {
            let data = if row.data.is_empty() {
                read_entity_payload(app, &row.entity_type, &row.entity_id)?
            } else {
                row.data.clone()
            };
            let version = if row.version > 0 {
                row.version
            } else {
                sync_engine::sync_record_version_from_data(&data)
            };
            Ok(sync_engine::SyncPushRecord {
                entity_type: row.entity_type.clone(),
                entity_id: row.entity_id.clone(),
                action: row.action.clone(),
                data,
                timestamp: row.timestamp.clone(),
                version,
            })
        })
        .collect()
}

fn mark_local_entity_synced(
    app: &AppHandle,
    entity_type: &str,
    entity_id: &str,
    server_version: i64,
) -> Result<(), String> {
    let sql = match entity_type {
        "message" => Some("UPDATE local_messages SET synced = 1, sync_version = ?1 WHERE id = ?2"),
        "document" => {
            Some("UPDATE local_documents SET synced = 1, sync_version = ?1 WHERE id = ?2")
        }
        "conversation" => {
            Some("UPDATE local_conversations SET synced = 1, sync_version = ?1 WHERE id = ?2")
        }
        "case" => Some("UPDATE local_cases SET synced = 1, sync_version = ?1 WHERE id = ?2"),
        "contract" => {
            Some("UPDATE local_contracts SET synced = 1, sync_version = ?1 WHERE id = ?2")
        }
        _ => None,
    };
    if let Some(sql) = sql {
        secure_db::execute(
            app,
            sql,
            vec![
                Value::from(server_version),
                Value::String(entity_id.to_string()),
            ],
        )?;
    }
    Ok(())
}

fn mark_rows_synced(
    app: &AppHandle,
    rows: &[sync_engine::PendingSyncRow],
    server_version: i64,
) -> Result<(), String> {
    for row in rows {
        secure_db::execute(
            app,
            "UPDATE sync_log
             SET status = 'synced',
                 error_message = NULL,
                 retry_count = 0,
                 next_retry_at = NULL,
                 needs_human = 0
             WHERE id = ?1",
            vec![Value::from(row.id)],
        )?;
        mark_local_entity_synced(app, &row.entity_type, &row.entity_id, server_version)?;
    }
    Ok(())
}

fn mark_rows_failed(
    app: &AppHandle,
    rows: &[sync_engine::PendingSyncRow],
    message: &str,
) -> Result<(), String> {
    let now = chrono::Utc::now();
    for row in rows {
        let retry = sync_engine::sync_retry_state(row.retry_count, now);
        secure_db::execute(
            app,
            "UPDATE sync_log
             SET status = 'failed',
                 error_message = ?1,
                 retry_count = ?2,
                 next_retry_at = ?3,
                 needs_human = ?4
             WHERE id = ?5",
            vec![
                Value::String(message.to_string()),
                Value::from(retry.retry_count),
                retry
                    .next_retry_at
                    .map(Value::String)
                    .unwrap_or(Value::Null),
                Value::from(i64::from(retry.needs_human)),
                Value::from(row.id),
            ],
        )?;
    }
    Ok(())
}

fn mark_rows_conflicted(
    app: &AppHandle,
    rows: &[sync_engine::PendingSyncRow],
    conflicts: &[Map<String, Value>],
) -> Result<(), String> {
    for conflict in conflicts {
        let Some(entity_type) = conflict.get("entity_type").and_then(Value::as_str) else {
            continue;
        };
        let Some(entity_id) = conflict.get("entity_id").and_then(Value::as_str) else {
            continue;
        };
        let Some(row) = rows
            .iter()
            .find(|row| row.entity_type == entity_type && row.entity_id == entity_id)
        else {
            continue;
        };
        secure_db::execute(
            app,
            "UPDATE sync_log
             SET status = 'conflict',
                 error_message = ?1,
                 next_retry_at = NULL,
                 needs_human = 1
             WHERE id = ?2",
            vec![
                Value::String(Value::Object(conflict.clone()).to_string()),
                Value::from(row.id),
            ],
        )?;
    }
    Ok(())
}

fn count_deferred_sync_rows(app: &AppHandle) -> Result<u32, String> {
    let rows = secure_db::select(
        app,
        "SELECT COUNT(*) AS count
         FROM sync_log
         WHERE status = 'failed'
           AND COALESCE(needs_human, 0) = 0
           AND COALESCE(retry_count, 0) < ?1
           AND next_retry_at IS NOT NULL
           AND next_retry_at > ?2",
        vec![
            Value::from(sync_engine::MAX_SYNC_RETRIES),
            Value::String(chrono::Utc::now().to_rfc3339()),
        ],
    )?;
    Ok(rows
        .first()
        .and_then(|row| row.get("count"))
        .and_then(Value::as_i64)
        .and_then(|value| u32::try_from(value).ok())
        .unwrap_or(0))
}

fn count_needs_human_sync_rows(app: &AppHandle) -> Result<u32, String> {
    let rows = secure_db::select(
        app,
        "SELECT COUNT(*) AS count
         FROM sync_log
         WHERE status = 'conflict'
            OR (status = 'failed' AND COALESCE(needs_human, 0) = 1)",
        Vec::new(),
    )?;
    Ok(rows
        .first()
        .and_then(|row| row.get("count"))
        .and_then(Value::as_i64)
        .and_then(|value| u32::try_from(value).ok())
        .unwrap_or(0))
}

fn data_field(data: &Map<String, Value>, keys: &[&str]) -> Option<Value> {
    keys.iter()
        .find_map(|key| data.get(*key).filter(|value| !value.is_null()).cloned())
}

fn data_or_string(data: &Map<String, Value>, keys: &[&str], fallback: &str) -> Value {
    data_field(data, keys).unwrap_or_else(|| Value::String(fallback.to_string()))
}

fn data_or_null(data: &Map<String, Value>, keys: &[&str]) -> Value {
    data_field(data, keys).unwrap_or(Value::Null)
}

fn data_or_i64(data: &Map<String, Value>, keys: &[&str], fallback: i64) -> Value {
    data_field(data, keys)
        .and_then(|value| {
            value
                .as_i64()
                .or_else(|| value.as_u64().and_then(|number| i64::try_from(number).ok()))
                .or_else(|| value.as_str().and_then(|number| number.parse::<i64>().ok()))
        })
        .map(Value::from)
        .unwrap_or_else(|| Value::from(fallback))
}

fn value_as_setting_text(value: Value) -> String {
    match value {
        Value::String(value) => value,
        Value::Null => String::new(),
        other => other.to_string(),
    }
}

fn remote_timestamp(record: &sync_engine::RemoteSyncRecord) -> String {
    record
        .timestamp
        .clone()
        .unwrap_or_else(|| chrono::Utc::now().to_rfc3339())
}

fn apply_remote_record(
    app: &AppHandle,
    record: &sync_engine::RemoteSyncRecord,
) -> Result<(), String> {
    let entity_id = record.entity_id.clone();
    let data = &record.data;
    let server_version = record.server_version.or(record.version).unwrap_or(0).max(0);
    let timestamp = remote_timestamp(record);

    if record.action == "delete" {
        let sql = match record.entity_type.as_str() {
            "message" => Some("DELETE FROM local_messages WHERE id = ?1"),
            "document" => Some("DELETE FROM local_documents WHERE id = ?1"),
            "conversation" => Some("DELETE FROM local_conversations WHERE id = ?1"),
            "case" => Some("DELETE FROM local_cases WHERE id = ?1"),
            "contract" => Some("DELETE FROM local_contracts WHERE id = ?1"),
            _ => None,
        };
        if let Some(sql) = sql {
            secure_db::execute(app, sql, vec![Value::String(entity_id)])?;
        }
        return Ok(());
    }

    match record.entity_type.as_str() {
        "message" => {
            secure_db::execute(
                app,
                "INSERT OR REPLACE INTO local_messages
                 (id, conversation_id, content, role, agent, created_at, synced, sync_version)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, 1, ?7)",
                vec![
                    Value::String(entity_id),
                    data_or_string(data, &["conversation_id", "conversationId"], ""),
                    data_or_string(data, &["content"], ""),
                    data_or_string(data, &["role"], "user"),
                    data_or_null(data, &["agent"]),
                    data_field(data, &["created_at", "createdAt"])
                        .unwrap_or(Value::String(timestamp)),
                    Value::from(server_version),
                ],
            )?;
        }
        "document" => {
            secure_db::execute(
                app,
                "INSERT OR REPLACE INTO local_documents
                 (id, title, content, file_path, file_size, mime_type, category, updated_at, synced, sync_version)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 1, ?9)",
                vec![
                    Value::String(entity_id),
                    data_or_string(data, &["title"], "未命名文档"),
                    data_or_null(data, &["content"]),
                    data_or_null(data, &["file_path", "filePath"]),
                    data_or_i64(data, &["file_size", "fileSize"], 0),
                    data_or_null(data, &["mime_type", "mimeType"]),
                    data_or_null(data, &["category"]),
                    data_field(data, &["updated_at", "updatedAt"]).unwrap_or(Value::String(timestamp)),
                    Value::from(server_version),
                ],
            )?;
        }
        "conversation" => {
            secure_db::execute(
                app,
                "INSERT OR REPLACE INTO local_conversations
                 (id, title, system_prompt, model, mode, updated_at, synced, sync_version)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, 1, ?7)",
                vec![
                    Value::String(entity_id),
                    data_or_string(data, &["title"], "未命名对话"),
                    data_or_null(data, &["system_prompt", "systemPrompt"]),
                    data_or_null(data, &["model"]),
                    data_or_string(data, &["mode"], "cloud"),
                    data_field(data, &["updated_at", "updatedAt"])
                        .unwrap_or(Value::String(timestamp)),
                    Value::from(server_version),
                ],
            )?;
        }
        "case" => {
            secure_db::execute(
                app,
                "INSERT OR REPLACE INTO local_cases
                 (id, title, description, status, case_type, priority, data_json, updated_at, synced, sync_version)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 1, ?9)",
                vec![
                    Value::String(entity_id),
                    data_or_string(data, &["title"], "未命名案件"),
                    data_or_null(data, &["description"]),
                    data_or_string(data, &["status"], "pending"),
                    data_or_null(data, &["case_type", "caseType"]),
                    data_or_string(data, &["priority"], "medium"),
                    data_field(data, &["data_json", "dataJson"])
                        .unwrap_or_else(|| Value::Object(data.clone())),
                    data_field(data, &["updated_at", "updatedAt"]).unwrap_or(Value::String(timestamp)),
                    Value::from(server_version),
                ],
            )?;
        }
        "contract" => {
            secure_db::execute(
                app,
                "INSERT OR REPLACE INTO local_contracts
                 (id, title, content, contract_type, status, parties_json, review_result_json, updated_at, synced, sync_version)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, 1, ?9)",
                vec![
                    Value::String(entity_id),
                    data_or_string(data, &["title"], "未命名合同"),
                    data_or_null(data, &["content"]),
                    data_or_null(data, &["contract_type", "contractType"]),
                    data_or_string(data, &["status"], "draft"),
                    data_field(data, &["parties_json", "partiesJson", "parties"])
                        .unwrap_or_else(|| Value::Array(Vec::new())),
                    data_field(data, &["review_result_json", "reviewResultJson", "review_result", "reviewResult"])
                        .unwrap_or(Value::Null),
                    data_field(data, &["updated_at", "updatedAt"]).unwrap_or(Value::String(timestamp)),
                    Value::from(server_version),
                ],
            )?;
        }
        "setting" => {
            let value = data_field(data, &["value"])
                .map(value_as_setting_text)
                .unwrap_or_default();
            write_setting(app, &entity_id, &value)?;
        }
        other if other.starts_with("harness_artifact_") => {
            let artifact_type = other.trim_start_matches("harness_artifact_").to_string();
            let session_id = data_field(data, &["session_id", "sessionId"])
                .map(value_as_setting_text)
                .unwrap_or_else(|| {
                    entity_id
                        .split(':')
                        .next()
                        .unwrap_or(&entity_id)
                        .to_string()
                });
            secure_db::execute(
                app,
                "INSERT OR REPLACE INTO local_artifacts
                 (id, session_id, artifact_type, data_json, created_at, synced)
                 VALUES (?1, ?2, ?3, ?4, ?5, 1)",
                vec![
                    Value::String(entity_id),
                    Value::String(session_id),
                    data_field(data, &["artifact_type", "artifactType"])
                        .map(value_as_setting_text)
                        .map(Value::String)
                        .unwrap_or_else(|| Value::String(artifact_type)),
                    data_field(data, &["data"]).unwrap_or_else(|| Value::Object(data.clone())),
                    Value::String(timestamp),
                ],
            )?;
        }
        _ => {}
    }
    Ok(())
}

async fn push_pending_records(
    app: &AppHandle,
    client: &reqwest::Client,
    api_base: &str,
    token: &str,
    device_id: &str,
) -> Result<PushOutcome, String> {
    let pending_rows = read_pending_sync_rows(app)?;
    let last_sync_version = read_last_sync_version(app)?;

    if pending_rows.is_empty() {
        return Ok(PushOutcome {
            ok: true,
            pushed: 0,
            conflicts: 0,
            deferred: count_deferred_sync_rows(app)?,
            needs_human: count_needs_human_sync_rows(app)?,
            server_version: last_sync_version,
        });
    }

    let records = hydrate_pending_records(app, &pending_rows)?;
    let payload =
        sync_engine::build_sync_push_payload(records, device_id.to_string(), last_sync_version);
    let push_url = format!("{api_base}/sync/push");
    let response = match client
        .post(&push_url)
        .bearer_auth(token)
        .json(&payload)
        .send()
        .await
    {
        Ok(response) => response,
        Err(err) => {
            mark_rows_failed(app, &pending_rows, &format!("push failed: {err}"))?;
            return Ok(PushOutcome {
                ok: false,
                pushed: 0,
                conflicts: 0,
                deferred: count_deferred_sync_rows(app)?,
                needs_human: count_needs_human_sync_rows(app)?,
                server_version: last_sync_version,
            });
        }
    };

    if !response.status().is_success() {
        let status = response.status().as_u16();
        mark_rows_failed(app, &pending_rows, &format!("push failed: {status}"))?;
        return Ok(PushOutcome {
            ok: false,
            pushed: 0,
            conflicts: 0,
            deferred: count_deferred_sync_rows(app)?,
            needs_human: count_needs_human_sync_rows(app)?,
            server_version: last_sync_version,
        });
    }

    let body = match response.json::<sync_engine::SyncPushResponseBody>().await {
        Ok(body) => body,
        Err(err) => {
            mark_rows_failed(
                app,
                &pending_rows,
                &format!("push response decode failed: {err}"),
            )?;
            return Ok(PushOutcome {
                ok: false,
                pushed: 0,
                conflicts: 0,
                deferred: count_deferred_sync_rows(app)?,
                needs_human: count_needs_human_sync_rows(app)?,
                server_version: last_sync_version,
            });
        }
    };

    let conflicts = body.conflicts.unwrap_or_default();
    let rejected = body.rejected.unwrap_or(conflicts.len() as u32);
    if rejected > conflicts.len() as u32 {
        mark_rows_failed(app, &pending_rows, "push rejected without conflict details")?;
        return Ok(PushOutcome {
            ok: false,
            pushed: 0,
            conflicts: conflicts.len() as u32,
            deferred: count_deferred_sync_rows(app)?,
            needs_human: count_needs_human_sync_rows(app)?,
            server_version: last_sync_version,
        });
    }
    let accepted_ids = sync_engine::accepted_row_ids(&pending_rows, &conflicts);
    let accepted_rows = pending_rows
        .iter()
        .filter(|row| accepted_ids.contains(&row.id))
        .cloned()
        .collect::<Vec<_>>();
    let server_version = body
        .server_version
        .unwrap_or(last_sync_version)
        .max(last_sync_version);

    mark_rows_synced(app, &accepted_rows, server_version)?;
    mark_rows_conflicted(app, &pending_rows, &conflicts)?;
    write_last_sync_version(app, server_version)?;

    Ok(PushOutcome {
        ok: true,
        pushed: body.accepted.unwrap_or(accepted_rows.len() as u32),
        conflicts: conflicts.len() as u32,
        deferred: count_deferred_sync_rows(app)?,
        needs_human: count_needs_human_sync_rows(app)?,
        server_version,
    })
}

async fn pull_incremental_updates(
    app: &AppHandle,
    client: &reqwest::Client,
    api_base: &str,
    token: &str,
) -> Result<PullOutcome, String> {
    let mut cursor = read_last_sync_version(app)?;
    let mut pulled = 0_u32;
    let mut has_more = true;

    while has_more {
        let pull_url = format!(
            "{api_base}/sync/pull?since_version={cursor}&limit={}",
            sync_engine::SYNC_BATCH_LIMIT
        );
        let response = match client.get(&pull_url).bearer_auth(token).send().await {
            Ok(response) => response,
            Err(_) => {
                return Ok(PullOutcome {
                    ok: false,
                    pulled,
                    server_version: cursor,
                });
            }
        };

        if !response.status().is_success() {
            return Ok(PullOutcome {
                ok: false,
                pulled,
                server_version: cursor,
            });
        }

        let body = match response.json::<sync_engine::SyncPullResponseBody>().await {
            Ok(body) => body,
            Err(_) => {
                return Ok(PullOutcome {
                    ok: false,
                    pulled,
                    server_version: cursor,
                });
            }
        };
        let records = body.records.unwrap_or_default();
        let has_records = !records.is_empty();
        for record in &records {
            apply_remote_record(app, record)?;
            cursor = cursor.max(record.server_version.or(record.version).unwrap_or(0));
            pulled = pulled.saturating_add(1);
        }

        cursor = cursor.max(body.server_version.unwrap_or(cursor));
        has_more = body.has_more.unwrap_or(false) && has_records;
    }

    write_last_sync_version(app, cursor)?;
    Ok(PullOutcome {
        ok: true,
        pulled,
        server_version: cursor,
    })
}

async fn run_rust_ipc_sync(
    app: &AppHandle,
    backend_url: &str,
    token: &str,
) -> Result<Value, String> {
    let api_base = sync_api_base(backend_url);
    let device_id = get_or_create_device_id(app)?;
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|err| format!("无法创建同步 HTTP 客户端: {err}"))?;

    let push = push_pending_records(app, &client, &api_base, token, &device_id).await?;
    let pull = pull_incremental_updates(app, &client, &api_base, token).await?;
    let success = push.ok && pull.ok;
    let sync_time = if success {
        let value = chrono::Utc::now().to_rfc3339();
        write_setting(app, sync_engine::LAST_SYNC_TIME_KEY, &value)?;
        Some(value)
    } else {
        None
    };

    let mut notices = Vec::new();
    if push.deferred > 0 {
        notices.push(format!("{} 条记录等待退避重试", push.deferred));
    }
    if push.needs_human > 0 {
        notices.push(format!("{} 条记录需要人工处理", push.needs_human));
    }
    let message = if success {
        if notices.is_empty() {
            "同步完成".to_string()
        } else {
            format!("同步完成，{}", notices.join("，"))
        }
    } else if notices.is_empty() {
        "同步未完成，请检查网络或登录状态".to_string()
    } else {
        format!("同步未完成，请检查网络或登录状态，{}", notices.join("，"))
    };

    Ok(json!({
        "success": success,
        "message": message,
        "sync_time": sync_time,
        "pushed": push.pushed,
        "pulled": pull.pulled,
        "conflicts": push.conflicts,
        "deferred": push.deferred,
        "needs_human": push.needs_human,
        "pending_sync_records": read_local_sync_snapshot(app)?.pending,
        "pending_offline_tasks": read_offline_queue_stats(app)?.flushable(),
        "push_ok": push.ok,
        "pull_ok": pull.ok,
        "server_version": pull.server_version.max(push.server_version),
        "device_id": device_id,
    }))
}

/// 触发手动同步
///
/// 前端优先使用 `api-adapter.ts` 的 SQLCipher bridge；当该路径不可用时，
/// Rust IPC fallback 也会读取同一份 SQLCipher `sync_log` 并执行真实 push/pull。
#[tauri::command]
pub async fn trigger_sync(
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let sync_snapshot = read_local_sync_snapshot(&app)?;
    let queue_stats = read_offline_queue_stats(&app)?;
    let pending_offline_tasks = queue_stats.flushable();
    let (mode, token, backend_url) = {
        let s = state.read().await;
        (s.mode, s.user_token.clone(), s.backend_url.clone())
    };

    if matches!(mode, AppMode::TopSecret) {
        return Ok(json!({
            "success": false,
            "message": format!(
                "绝密模式下不同步任何数据；本地仍有 {} 条同步记录、{} 条离线任务待处理",
                sync_snapshot.pending,
                pending_offline_tasks
            ),
            "conflicts": sync_snapshot.conflicts,
            "deferred": sync_snapshot.deferred,
            "needs_human": sync_snapshot.needs_human,
            "pending_sync_records": sync_snapshot.pending,
            "pending_offline_tasks": pending_offline_tasks,
        }));
    }

    let Some(token) = token else {
        return Ok(json!({
            "success": false,
            "message": format!(
                "请先登录后再同步；本地仍有 {} 条同步记录、{} 条离线任务待处理",
                sync_snapshot.pending,
                pending_offline_tasks
            ),
            "conflicts": sync_snapshot.conflicts,
            "deferred": sync_snapshot.deferred,
            "needs_human": sync_snapshot.needs_human,
            "pending_sync_records": sync_snapshot.pending,
            "pending_offline_tasks": pending_offline_tasks,
        }));
    };

    {
        let mut s = state.write().await;
        s.sync_status = SyncStatus::Syncing;
    }

    let result = run_rust_ipc_sync(&app, &backend_url, &token).await;
    match result {
        Ok(payload) => {
            let success = payload
                .get("success")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            let sync_time = payload
                .get("sync_time")
                .and_then(Value::as_str)
                .map(str::to_string);
            let mut s = state.write().await;
            s.sync_status = if success {
                SyncStatus::Idle
            } else {
                SyncStatus::Error
            };
            if let Some(sync_time) = sync_time {
                s.last_sync_time = Some(sync_time);
            }
            Ok(payload)
        }
        Err(err) => {
            let mut s = state.write().await;
            s.sync_status = SyncStatus::Error;
            Err(err)
        }
    }
}

/// 获取同步状态
#[tauri::command]
pub async fn get_sync_status(
    app: AppHandle,
    state: State<'_, SharedAppState>,
) -> Result<serde_json::Value, String> {
    let s = state.read().await;
    let sync_snapshot = read_local_sync_snapshot(&app)?;
    let queue_stats = read_offline_queue_stats(&app)?;
    Ok(json!({
        "status": s.sync_status,
        "last_sync_time": s.last_sync_time,
        "is_online": s.is_online,
        "pending_sync_records": sync_snapshot.pending,
        "pending_offline_tasks": queue_stats.flushable(),
        "sync_conflicts": sync_snapshot.conflicts,
        "deferred_sync_records": sync_snapshot.deferred,
        "needs_human": sync_snapshot.needs_human,
    }))
}

/// 获取待同步记录数
///
/// 返回 Rust IPC 可观察到的本地待同步工作量：
/// - `sync_log` 中待推送/可重试的记录
/// - `offline_tasks` 中 queued/local_completed 的离线任务
#[tauri::command]
pub async fn get_pending_sync_count(app: AppHandle) -> Result<u32, String> {
    let sync_snapshot = read_local_sync_snapshot(&app)?;
    let queue_stats = read_offline_queue_stats(&app)?;
    Ok(sync_snapshot
        .pending
        .saturating_add(queue_stats.flushable()))
}

/// 解决同步冲突
///
/// 将冲突决议上报后端 `/api/v1/sync/resolve`。
#[tauri::command]
pub async fn resolve_conflict(
    state: State<'_, SharedAppState>,
    entity_type: String,
    entity_id: String,
    resolution: String, // "keep_local" | "keep_remote" | "merge"
) -> Result<serde_json::Value, String> {
    log::info!(
        "解决冲突: entity={}/{}, resolution={}",
        entity_type,
        entity_id,
        resolution
    );
    ensure_data_network_allowed(state.inner(), "上报同步冲突决议").await?;

    let (backend_url, token) = {
        let s = state.read().await;
        (s.backend_url.clone(), s.user_token.clone())
    };

    let Some(token) = token else {
        return Err("未登录，无法解决冲突".to_string());
    };

    let url = format!("{}/api/v1/sync/resolve", backend_url.trim_end_matches('/'));
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let resp = client
        .post(&url)
        .bearer_auth(&token)
        .json(&json!({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "resolution": resolution,
        }))
        .send()
        .await
        .map_err(|e| format!("上报冲突决议失败: {e}"))?;

    let ok = resp.status().is_success();
    Ok(json!({
        "success": ok,
        "entity_id": entity_id,
        "resolution": resolution,
        "status": resp.status().as_u16(),
    }))
}
