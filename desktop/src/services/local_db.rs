/// 本地 SQLite 数据库管理
///
/// 通过 tauri-plugin-sql 前端直接操作 SQLite，
/// 此模块提供 Rust 侧的初始化和迁移支持。

/// 数据库初始化 SQL（首次启动时执行）
pub const INIT_SQL: &str = r#"
-- 离线消息缓存
CREATE TABLE IF NOT EXISTS local_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    content TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0,
    sync_version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON local_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_synced ON local_messages(synced);

-- 离线文档缓存
CREATE TABLE IF NOT EXISTS local_documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    file_path TEXT,
    file_size INTEGER DEFAULT 0,
    mime_type TEXT,
    category TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0,
    sync_version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_documents_synced ON local_documents(synced);
CREATE INDEX IF NOT EXISTS idx_documents_category ON local_documents(category);

-- 离线案件缓存
CREATE TABLE IF NOT EXISTS local_cases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    case_type TEXT,
    priority TEXT DEFAULT 'medium',
    data_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0,
    sync_version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cases_status ON local_cases(status);

-- 离线合同缓存
CREATE TABLE IF NOT EXISTS local_contracts (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    contract_type TEXT,
    status TEXT DEFAULT 'draft',
    parties_json TEXT,
    review_result_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0,
    sync_version INTEGER DEFAULT 0
);

-- 同步日志
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    data_json TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_log(status);
CREATE INDEX IF NOT EXISTS idx_sync_entity ON sync_log(entity_type, entity_id);

-- 应用设置
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 知识库缓存（绝密模式下使用）
CREATE TABLE IF NOT EXISTS local_knowledge (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    tags TEXT,
    embedding_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_category ON local_knowledge(category);

-- 对话历史
CREATE TABLE IF NOT EXISTS local_conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    system_prompt TEXT,
    model TEXT,
    mode TEXT DEFAULT 'cloud',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0
);

-- 数据库版本管理
CREATE TABLE IF NOT EXISTS db_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 插入初始版本记录
INSERT OR IGNORE INTO db_migrations (version, name) VALUES (1, 'initial_schema');
"#;

/// 获取数据库初始化 SQL
pub fn get_init_sql() -> &'static str {
    INIT_SQL
}
