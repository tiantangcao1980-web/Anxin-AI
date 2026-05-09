use std::path::{Path, PathBuf};
use std::time::Instant;

use getrandom::getrandom;
use keyring::{Entry, Error as KeyringError};
use rusqlite::types::{Value as SqlValue, ValueRef};
use rusqlite::{params, params_from_iter, Connection};
use serde::Serialize;
use serde_json::{Map, Value};
use tauri::{AppHandle, Manager};

use crate::services::local_db;

const DB_FILENAME: &str = "anxin_local.db";
const KEYRING_SERVICE: &str = "com.anxin.legal.desktop";
const KEYRING_USER: &str = "sqlcipher-db-key-v1";
const TEST_KEY_ENV: &str = "ANXIN_DESKTOP_SQLCIPHER_KEY_HEX";
const KEYRING_SERVICE_ENV: &str = "ANXIN_DESKTOP_KEYRING_SERVICE";
const KEYRING_USER_ENV: &str = "ANXIN_DESKTOP_KEYRING_USER";
pub const RESET_CONFIRMATION: &str = "ERASE LOCAL DATA";

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SecureExecuteResult {
    pub rows_affected: usize,
}

#[derive(Debug, Serialize)]
pub struct SecureDbSecurityContract {
    pub encrypted: bool,
    pub keyring_backed: bool,
    pub release_blocking: bool,
    pub reason: &'static str,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct InstalledProfileSmokeReport {
    pub db_path: String,
    pub keyring_service: String,
    pub keyring_user: String,
    pub keyring_round_trip: bool,
    pub encrypted_reopen: bool,
    pub plaintext_backup_present: bool,
    pub plaintext_open_blocked: bool,
    pub sentinel_id: &'static str,
    pub sentinel_content: &'static str,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SecureDbPerformanceSmokeReport {
    pub db_path: String,
    pub keyring_service: String,
    pub keyring_user: String,
    pub keyring_round_trip: bool,
    pub encrypted_reopen: bool,
    pub status: &'static str,
    pub push_100_rows_p95_ms: f64,
    pub pull_500_rows_p95_ms: f64,
    pub push_threshold_ms: f64,
    pub pull_threshold_ms: f64,
    pub push_samples_ms: Vec<f64>,
    pub pull_samples_ms: Vec<f64>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SecureDbResetReport {
    pub db_path: String,
    pub keyring_deleted: bool,
    pub removed_files: Vec<String>,
}

pub fn security_contract() -> SecureDbSecurityContract {
    SecureDbSecurityContract {
        encrypted: true,
        keyring_backed: true,
        release_blocking: false,
        reason: "Desktop SQLite is owned by Rust, opened through SQLCipher, and the production key is stored in the OS keyring.",
    }
}

fn keyring_identity() -> (String, String) {
    let service =
        std::env::var(KEYRING_SERVICE_ENV).unwrap_or_else(|_| KEYRING_SERVICE.to_string());
    let user = std::env::var(KEYRING_USER_ENV).unwrap_or_else(|_| KEYRING_USER.to_string());
    (service, user)
}

fn keyring_entry() -> Result<Entry, String> {
    let (service, user) = keyring_identity();
    Entry::new(&service, &user).map_err(|err| format!("无法打开系统 keyring 条目: {err}"))
}

pub fn database_path(app: &AppHandle) -> Result<PathBuf, String> {
    if let Ok(path) = std::env::var("ANXIN_DESKTOP_DB_PATH") {
        return Ok(PathBuf::from(path));
    }

    let dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("无法解析桌面应用数据目录: {err}"))?;
    std::fs::create_dir_all(&dir).map_err(|err| format!("无法创建桌面应用数据目录: {err}"))?;
    Ok(dir.join(DB_FILENAME))
}

fn hex_encode(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

fn is_valid_key_hex(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

fn generate_key_hex() -> Result<String, String> {
    let mut key = [0_u8; 32];
    getrandom(&mut key).map_err(|err| format!("无法生成 SQLCipher key: {err}"))?;
    Ok(hex_encode(&key))
}

fn load_or_create_key_hex() -> Result<String, String> {
    if let Ok(value) = std::env::var(TEST_KEY_ENV) {
        if is_valid_key_hex(&value) {
            return Ok(value);
        }
        return Err(format!("{TEST_KEY_ENV} 必须是 64 位十六进制字符串"));
    }

    let entry = keyring_entry()?;

    match entry.get_password() {
        Ok(value) if is_valid_key_hex(&value) => Ok(value),
        Ok(_) => Err("系统 keyring 中的 SQLCipher key 格式无效".to_string()),
        Err(KeyringError::NoEntry) => {
            let value = generate_key_hex()?;
            entry
                .set_password(&value)
                .map_err(|err| format!("无法写入系统 keyring: {err}"))?;
            Ok(value)
        }
        Err(err) => Err(format!("无法读取系统 keyring: {err}")),
    }
}

fn key_pragma_sql(key_hex: &str) -> String {
    format!("PRAGMA key = \"x'{key_hex}'\";")
}

fn open_encrypted_path(path: &Path, key_hex: &str) -> Result<Connection, String> {
    let conn = Connection::open(path).map_err(|err| format!("无法打开本地 SQLCipher DB: {err}"))?;
    conn.execute_batch(&key_pragma_sql(key_hex))
        .map_err(|err| format!("无法应用 SQLCipher key: {err}"))?;
    conn.execute_batch(
        "PRAGMA foreign_keys = ON;
         PRAGMA journal_mode = WAL;",
    )
    .map_err(|err| format!("无法初始化 SQLCipher PRAGMA: {err}"))?;
    ensure_schema(&conn)?;
    Ok(conn)
}

fn verify_integrity(conn: &Connection) -> Result<(), String> {
    let status: String = conn
        .query_row("PRAGMA integrity_check", [], |row| row.get(0))
        .map_err(|err| format!("SQLite integrity_check 执行失败: {err}"))?;
    if status.eq_ignore_ascii_case("ok") {
        Ok(())
    } else {
        Err(format!("SQLite integrity_check 失败: {status}"))
    }
}

fn sql_quote(value: &str) -> String {
    value.replace('\'', "''")
}

fn migrate_plaintext_to_encrypted(path: &Path, key_hex: &str) -> Result<(), String> {
    let plaintext =
        Connection::open(path).map_err(|err| format!("无法打开待迁移明文 SQLite: {err}"))?;
    verify_integrity(&plaintext)?;

    let encrypted_tmp = path.with_extension("sqlcipher.tmp");
    let plaintext_backup = path.with_extension("plaintext.backup");
    let _ = std::fs::remove_file(&encrypted_tmp);
    let _ = std::fs::remove_file(&plaintext_backup);

    let encrypted_tmp_sql = sql_quote(&encrypted_tmp.to_string_lossy());
    plaintext
        .execute_batch(&format!(
            "ATTACH DATABASE '{encrypted_tmp_sql}' AS encrypted KEY \"x'{key_hex}'\";
             SELECT sqlcipher_export('encrypted');
             DETACH DATABASE encrypted;"
        ))
        .map_err(|err| format!("明文 SQLite 迁移到 SQLCipher 失败: {err}"))?;

    let encrypted = open_encrypted_path(&encrypted_tmp, key_hex)?;
    verify_integrity(&encrypted)?;
    drop(encrypted);
    drop(plaintext);

    std::fs::rename(path, &plaintext_backup)
        .map_err(|err| format!("无法隔离明文 SQLite 备份: {err}"))?;
    std::fs::rename(&encrypted_tmp, path).map_err(|err| format!("无法启用加密 SQLite: {err}"))?;
    Ok(())
}

fn open_connection(app: &AppHandle) -> Result<Connection, String> {
    let path = database_path(app)?;
    open_connection_for_path(&path)
}

fn open_connection_for_path(path: &Path) -> Result<Connection, String> {
    let key_hex = load_or_create_key_hex()?;

    if !path.exists() {
        return open_encrypted_path(path, &key_hex);
    }

    match open_encrypted_path(path, &key_hex).and_then(|conn| {
        verify_integrity(&conn)?;
        Ok(conn)
    }) {
        Ok(conn) => Ok(conn),
        Err(encrypted_error) => {
            migrate_plaintext_to_encrypted(path, &key_hex)
                .map_err(|migration_error| {
                    format!(
                        "无法打开加密 SQLite，也无法完成明文迁移；encrypted_error={encrypted_error}; migration_error={migration_error}"
                    )
                })?;
            open_encrypted_path(path, &key_hex)
        }
    }
}

pub fn delete_keyring_entry() -> Result<(), String> {
    match keyring_entry()?.delete_credential() {
        Ok(()) | Err(KeyringError::NoEntry) => Ok(()),
        Err(err) => Err(format!("无法删除系统 keyring 条目: {err}")),
    }
}

fn path_with_file_name_suffix(path: &Path, suffix: &str) -> PathBuf {
    let mut file_name = path
        .file_name()
        .map(|value| value.to_os_string())
        .unwrap_or_default();
    file_name.push(suffix);
    path.with_file_name(file_name)
}

fn local_database_file_candidates(path: &Path) -> Vec<PathBuf> {
    vec![
        path.to_path_buf(),
        path_with_file_name_suffix(path, "-wal"),
        path_with_file_name_suffix(path, "-shm"),
        path.with_extension("plaintext.backup"),
        path.with_extension("sqlcipher.tmp"),
    ]
}

fn remove_local_database_files(path: &Path) -> Result<Vec<String>, String> {
    let mut removed = Vec::new();

    for candidate in local_database_file_candidates(path) {
        if candidate.is_dir() {
            return Err(format!(
                "拒绝删除目录形式的本地数据库路径: {}",
                candidate.display()
            ));
        }

        match std::fs::remove_file(&candidate) {
            Ok(()) => removed.push(candidate.display().to_string()),
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => {}
            Err(err) => {
                return Err(format!(
                    "无法删除本地数据库文件 {}: {err}",
                    candidate.display()
                ));
            }
        }
    }

    Ok(removed)
}

pub fn reset_local_data_for_path(
    path: &Path,
    confirmation: &str,
) -> Result<SecureDbResetReport, String> {
    if confirmation != RESET_CONFIRMATION {
        return Err(format!("重置本地数据需要确认短语: {RESET_CONFIRMATION}"));
    }

    delete_keyring_entry()?;
    let removed_files = remove_local_database_files(path)?;

    Ok(SecureDbResetReport {
        db_path: path.display().to_string(),
        keyring_deleted: true,
        removed_files,
    })
}

pub fn reset_local_data(
    app: &AppHandle,
    confirmation: &str,
) -> Result<SecureDbResetReport, String> {
    let path = database_path(app)?;
    reset_local_data_for_path(&path, confirmation)
}

pub fn installed_profile_smoke(path: &Path) -> Result<InstalledProfileSmokeReport, String> {
    if std::env::var(TEST_KEY_ENV).is_ok() {
        return Err(format!(
            "{TEST_KEY_ENV} must be unset for installed-profile keyring smoke"
        ));
    }

    let sentinel_id = "installed-profile-smoke";
    let sentinel_content = "installed profile SQLCipher keyring reopen smoke";

    let conn = open_connection_for_path(path)?;
    conn.execute(
        "INSERT OR REPLACE INTO local_messages (id, conversation_id, content, role, synced)
         VALUES (?1, 'installed-profile-smoke', ?2, 'user', 0)",
        [sentinel_id, sentinel_content],
    )
    .map_err(|err| format!("无法写入 installed-profile smoke sentinel: {err}"))?;
    verify_integrity(&conn)?;
    drop(conn);

    let reopened = open_connection_for_path(path)?;
    let stored: String = reopened
        .query_row(
            "SELECT content FROM local_messages WHERE id = ?1",
            [sentinel_id],
            |row| row.get(0),
        )
        .map_err(|err| format!("无法复开 SQLCipher sentinel: {err}"))?;
    verify_integrity(&reopened)?;
    drop(reopened);

    let (service, user) = keyring_identity();
    let keyring_value = keyring_entry()?
        .get_password()
        .map_err(|err| format!("无法回读系统 keyring: {err}"))?;

    let plaintext_open_blocked = Connection::open(path)
        .and_then(|conn| conn.query_row("SELECT COUNT(*) FROM sqlite_master", [], |_| Ok(())))
        .is_err();

    Ok(InstalledProfileSmokeReport {
        db_path: path.display().to_string(),
        keyring_service: service,
        keyring_user: user,
        keyring_round_trip: is_valid_key_hex(&keyring_value),
        encrypted_reopen: stored == sentinel_content,
        plaintext_backup_present: path.with_extension("plaintext.backup").exists(),
        plaintext_open_blocked,
        sentinel_id,
        sentinel_content,
    })
}

fn timed_ms<F>(mut f: F) -> Result<f64, String>
where
    F: FnMut() -> Result<(), String>,
{
    let started = Instant::now();
    f()?;
    Ok(started.elapsed().as_secs_f64() * 1000.0)
}

fn percentile(values: &[f64], pct: f64) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(|left, right| left.total_cmp(right));
    let index = (((pct / 100.0) * sorted.len() as f64).ceil() as usize)
        .saturating_sub(1)
        .min(sorted.len() - 1);
    sorted[index]
}

fn round_one_decimal(value: f64) -> f64 {
    (value * 10.0).round() / 10.0
}

fn insert_perf_push_rows(conn: &mut Connection, round: usize) -> Result<(), String> {
    let tx = conn
        .transaction()
        .map_err(|err| format!("无法开始 SQLCipher push 性能事务: {err}"))?;
    let prefix = format!("release-perf-push-{round}-%");
    tx.execute(
        "DELETE FROM sync_log WHERE entity_id LIKE ?1",
        params![prefix],
    )
    .map_err(|err| format!("无法清理 SQLCipher push 性能行: {err}"))?;
    {
        let mut stmt = tx
            .prepare(
                "INSERT INTO sync_log (entity_type, entity_id, action, data_json, status, retry_count, needs_human)
                 VALUES (?1, ?2, ?3, ?4, ?5, 0, 0)",
            )
            .map_err(|err| format!("无法准备 SQLCipher push 性能插入: {err}"))?;
        for index in 0..100 {
            let entity_id = format!("release-perf-push-{round}-{index}");
            let payload = serde_json::json!({
                "index": index,
                "title": format!("Desktop release push perf {index}"),
            })
            .to_string();
            stmt.execute(params!["document", entity_id, "push", payload, "pending"])
                .map_err(|err| format!("无法写入 SQLCipher push 性能行: {err}"))?;
        }
    }
    tx.commit()
        .map_err(|err| format!("无法提交 SQLCipher push 性能事务: {err}"))
}

fn insert_perf_pull_rows(conn: &mut Connection, round: usize) -> Result<(), String> {
    let tx = conn
        .transaction()
        .map_err(|err| format!("无法开始 SQLCipher pull 性能事务: {err}"))?;
    let prefix = format!("release-perf-pull-{round}-%");
    tx.execute(
        "DELETE FROM local_documents WHERE id LIKE ?1",
        params![prefix],
    )
    .map_err(|err| format!("无法清理 SQLCipher pull 性能行: {err}"))?;
    {
        let mut stmt = tx
            .prepare(
                "INSERT OR REPLACE INTO local_documents
                 (id, title, content, file_size, mime_type, category, synced, sync_version)
                 VALUES (?1, ?2, ?3, 128, ?4, ?5, 1, ?6)",
            )
            .map_err(|err| format!("无法准备 SQLCipher pull 性能插入: {err}"))?;
        for index in 0..500 {
            let id = format!("release-perf-pull-{round}-{index}");
            stmt.execute(params![
                id,
                format!("Pulled release document {index}"),
                format!("Release local pull performance content {index}"),
                "text/plain",
                "perf",
                round as i64,
            ])
            .map_err(|err| format!("无法写入 SQLCipher pull 性能行: {err}"))?;
        }
    }
    tx.commit()
        .map_err(|err| format!("无法提交 SQLCipher pull 性能事务: {err}"))
}

fn count_like(conn: &Connection, sql: &str, pattern: &str) -> Result<i64, String> {
    conn.query_row(sql, params![pattern], |row| row.get(0))
        .map_err(|err| format!("无法读取 SQLCipher 性能计数: {err}"))
}

pub fn performance_smoke(path: &Path) -> Result<SecureDbPerformanceSmokeReport, String> {
    let mut conn = open_connection_for_path(path)?;
    let mut push_samples = Vec::new();
    let mut pull_samples = Vec::new();

    for round in 1..=5 {
        push_samples.push(timed_ms(|| insert_perf_push_rows(&mut conn, round))?);
        let push_pattern = format!("release-perf-push-{round}-%");
        let push_count = count_like(
            &conn,
            "SELECT COUNT(*) FROM sync_log WHERE entity_id LIKE ?1",
            &push_pattern,
        )?;
        if push_count != 100 {
            return Err(format!(
                "SQLCipher push 性能行数量不正确: expected=100 actual={push_count}"
            ));
        }

        pull_samples.push(timed_ms(|| insert_perf_pull_rows(&mut conn, round))?);
        let pull_pattern = format!("release-perf-pull-{round}-%");
        let pull_count = count_like(
            &conn,
            "SELECT COUNT(*) FROM local_documents WHERE id LIKE ?1",
            &pull_pattern,
        )?;
        if pull_count != 500 {
            return Err(format!(
                "SQLCipher pull 性能行数量不正确: expected=500 actual={pull_count}"
            ));
        }
    }

    verify_integrity(&conn)?;
    drop(conn);

    let reopened = open_connection_for_path(path)?;
    let encrypted_reopen_count = count_like(
        &reopened,
        "SELECT COUNT(*) FROM local_documents WHERE id LIKE ?1",
        "release-perf-pull-5-%",
    )?;
    verify_integrity(&reopened)?;
    drop(reopened);

    let (service, user) = keyring_identity();
    let keyring_round_trip = if std::env::var(TEST_KEY_ENV).is_ok() {
        false
    } else {
        keyring_entry()
            .and_then(|entry| {
                entry
                    .get_password()
                    .map_err(|err| format!("无法回读系统 keyring: {err}"))
            })
            .is_ok_and(|value| is_valid_key_hex(&value))
    };

    let push_p95 = round_one_decimal(percentile(&push_samples, 95.0));
    let pull_p95 = round_one_decimal(percentile(&pull_samples, 95.0));
    let push_threshold = 2000.0;
    let pull_threshold = 3000.0;
    if push_p95 >= push_threshold {
        return Err(format!(
            "100-row push SQLCipher P95 exceeded 2s: {push_p95:.1}ms"
        ));
    }
    if pull_p95 >= pull_threshold {
        return Err(format!(
            "500-row pull SQLCipher P95 exceeded 3s: {pull_p95:.1}ms"
        ));
    }

    Ok(SecureDbPerformanceSmokeReport {
        db_path: path.display().to_string(),
        keyring_service: service,
        keyring_user: user,
        keyring_round_trip,
        encrypted_reopen: encrypted_reopen_count == 500,
        status: "passed",
        push_100_rows_p95_ms: push_p95,
        pull_500_rows_p95_ms: pull_p95,
        push_threshold_ms: push_threshold,
        pull_threshold_ms: pull_threshold,
        push_samples_ms: push_samples.into_iter().map(round_one_decimal).collect(),
        pull_samples_ms: pull_samples.into_iter().map(round_one_decimal).collect(),
    })
}

fn ensure_schema(conn: &Connection) -> Result<(), String> {
    conn.execute_batch(local_db::build_init_sql())
        .map_err(|err| format!("无法初始化本地 SQLCipher schema: {err}"))
}

fn json_to_sql_value(value: Value) -> SqlValue {
    match value {
        Value::Null => SqlValue::Null,
        Value::Bool(value) => SqlValue::Integer(i64::from(value)),
        Value::Number(value) => {
            if let Some(value) = value.as_i64() {
                SqlValue::Integer(value)
            } else if let Some(value) = value.as_f64() {
                SqlValue::Real(value)
            } else {
                SqlValue::Text(value.to_string())
            }
        }
        Value::String(value) => SqlValue::Text(value),
        other => SqlValue::Text(other.to_string()),
    }
}

fn sql_value_to_json(value: ValueRef<'_>) -> Value {
    match value {
        ValueRef::Null => Value::Null,
        ValueRef::Integer(value) => Value::from(value),
        ValueRef::Real(value) => Value::from(value),
        ValueRef::Text(value) => Value::String(String::from_utf8_lossy(value).into_owned()),
        ValueRef::Blob(value) => {
            Value::Array(value.iter().map(|byte| Value::from(*byte)).collect())
        }
    }
}

pub fn execute(
    app: &AppHandle,
    sql: &str,
    bind_values: Vec<Value>,
) -> Result<SecureExecuteResult, String> {
    let conn = open_connection(app)?;
    let values: Vec<SqlValue> = bind_values.into_iter().map(json_to_sql_value).collect();
    let rows_affected = conn
        .execute(sql, params_from_iter(values.iter()))
        .map_err(|err| format!("SQLCipher execute 失败: {err}"))?;
    Ok(SecureExecuteResult { rows_affected })
}

pub fn select(app: &AppHandle, sql: &str, bind_values: Vec<Value>) -> Result<Vec<Value>, String> {
    let conn = open_connection(app)?;
    let values: Vec<SqlValue> = bind_values.into_iter().map(json_to_sql_value).collect();
    let mut stmt = conn
        .prepare(sql)
        .map_err(|err| format!("SQLCipher select 准备失败: {err}"))?;
    let column_names: Vec<String> = stmt
        .column_names()
        .into_iter()
        .map(str::to_string)
        .collect();

    let rows = stmt
        .query_map(params_from_iter(values.iter()), |row| {
            let mut item = Map::with_capacity(column_names.len());
            for (index, name) in column_names.iter().enumerate() {
                item.insert(name.clone(), sql_value_to_json(row.get_ref(index)?));
            }
            Ok(Value::Object(item))
        })
        .map_err(|err| format!("SQLCipher select 执行失败: {err}"))?;

    let mut out = Vec::new();
    for row in rows {
        out.push(row.map_err(|err| format!("SQLCipher row 解码失败: {err}"))?);
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use rusqlite::Connection;

    use super::{
        hex_encode, is_valid_key_hex, migrate_plaintext_to_encrypted, open_encrypted_path,
        remove_local_database_files, reset_local_data_for_path, security_contract,
    };

    #[test]
    fn generated_key_contract_is_sqlcipher_sized_hex() {
        let key = hex_encode(&[0xab; 32]);
        assert!(is_valid_key_hex(&key));
        assert!(!is_valid_key_hex("short"));
    }

    #[test]
    fn security_contract_is_release_ready_when_secure_db_is_owner() {
        let contract = security_contract();
        assert!(contract.encrypted);
        assert!(contract.keyring_backed);
        assert!(!contract.release_blocking);
    }

    #[test]
    fn migrates_plaintext_sqlite_to_sqlcipher() {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock should be after epoch")
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "anxin-plaintext-migration-{}-{nonce}.db",
            std::process::id()
        ));
        let key_hex = "11".repeat(32);

        {
            let conn = Connection::open(&path).expect("create plaintext sqlite");
            conn.execute_batch(
                "CREATE TABLE local_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    agent TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    synced BOOLEAN DEFAULT 0,
                    sync_version INTEGER DEFAULT 0
                 );
                 INSERT INTO local_messages (id, conversation_id, content, role)
                 VALUES ('msg-1', 'conv-1', 'secret body', 'user');",
            )
            .expect("seed plaintext sqlite");
        }

        migrate_plaintext_to_encrypted(&path, &key_hex).expect("migrate plaintext sqlite");
        let conn = open_encrypted_path(&path, &key_hex).expect("open encrypted sqlite");
        let content: String = conn
            .query_row(
                "SELECT content FROM local_messages WHERE id = 'msg-1'",
                [],
                |row| row.get(0),
            )
            .expect("read migrated row");

        assert_eq!(content, "secret body");
        assert!(path.with_extension("plaintext.backup").exists());

        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_file(path.with_extension("plaintext.backup"));
    }

    #[test]
    fn reset_local_data_requires_explicit_confirmation_before_keyring_access() {
        let path = std::env::temp_dir().join(format!(
            "anxin-reset-confirmation-{}.db",
            std::process::id()
        ));
        std::fs::write(&path, b"local data").expect("seed local DB placeholder");

        let error = reset_local_data_for_path(&path, "delete it").expect_err("must reject typo");

        assert!(error.contains(super::RESET_CONFIRMATION));
        assert!(path.exists());
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn reset_local_data_removes_database_wal_shm_and_migration_artifacts() {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock should be after epoch")
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "anxin-reset-local-data-{}-{nonce}.db",
            std::process::id()
        ));
        let candidates = [
            path.clone(),
            path.with_file_name(format!(
                "{}-wal",
                path.file_name().expect("file name").to_string_lossy()
            )),
            path.with_file_name(format!(
                "{}-shm",
                path.file_name().expect("file name").to_string_lossy()
            )),
            path.with_extension("plaintext.backup"),
            path.with_extension("sqlcipher.tmp"),
        ];
        for candidate in &candidates {
            std::fs::write(candidate, b"local data").expect("seed local database artifact");
        }

        let removed = remove_local_database_files(&path).expect("remove local database artifacts");

        assert_eq!(removed.len(), candidates.len());
        for candidate in &candidates {
            assert!(!candidate.exists());
        }
        assert!(remove_local_database_files(&path)
            .expect("second reset should be idempotent")
            .is_empty());
    }
}
