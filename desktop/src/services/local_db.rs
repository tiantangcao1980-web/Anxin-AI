#![allow(dead_code)]

/// 本地 SQLite 数据库管理
///
/// 通过 Rust-owned SQLCipher 连接提供本地 SQLite 能力，
/// 此模块提供初始化和迁移 SQL。

pub const LOCAL_DB_URL: &str = "sqlcipher:anxin_local.db";

/// 数据库初始化 SQL（首次启动时执行）
pub const INIT_SQL: &str = include_str!("../../migrations/001_offline_queue.sql");

#[derive(Clone, Debug)]
pub struct SqlMigration {
    pub version: i64,
    pub description: &'static str,
    pub sql: &'static str,
}

pub fn sqlite_migrations() -> Vec<SqlMigration> {
    vec![SqlMigration {
        version: 1,
        description: "offline_queue_and_sync_schema",
        sql: INIT_SQL,
    }]
}

/// 获取数据库初始化 SQL
pub fn build_init_sql() -> &'static str {
    INIT_SQL
}

pub fn get_init_sql() -> &'static str {
    build_init_sql()
}

#[cfg(test)]
mod tests {
    use super::build_init_sql;
    use super::{sqlite_migrations, LOCAL_DB_URL};

    #[test]
    fn build_init_sql_contains_sync_tables() {
        let sql = build_init_sql();

        assert!(sql.contains("CREATE TABLE IF NOT EXISTS offline_tasks"));
        assert!(sql.contains("CREATE TABLE IF NOT EXISTS app_settings"));
        assert!(sql.contains("CREATE TABLE IF NOT EXISTS sync_log"));
        assert!(sql.contains("next_retry_at DATETIME"));
        assert!(sql.contains("needs_human BOOLEAN DEFAULT 0"));
        assert!(sql.contains("sync_version INTEGER DEFAULT 0"));
    }

    #[test]
    fn sqlite_migrations_register_initial_schema() {
        let migrations = sqlite_migrations();

        assert_eq!(LOCAL_DB_URL, "sqlcipher:anxin_local.db");
        assert_eq!(migrations.len(), 1);
        assert_eq!(migrations[0].version, 1);
        assert_eq!(migrations[0].description, "offline_queue_and_sync_schema");
        assert!(migrations[0]
            .sql
            .contains("CREATE TABLE IF NOT EXISTS sync_log"));
    }
}
