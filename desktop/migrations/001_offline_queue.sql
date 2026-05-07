-- Desktop offline queue and sync schema.
-- Applied through the Rust-owned SQLCipher local DB service.

-- Offline message cache.
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

-- Offline document cache.
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

-- Offline case cache.
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

-- Offline contract cache.
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

-- Sync log and retry queue.
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    data_json TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at DATETIME,
    needs_human BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_log(status);
CREATE INDEX IF NOT EXISTS idx_sync_entity ON sync_log(entity_type, entity_id);
-- idx_sync_retry_due is created by the frontend best-effort migration after
-- legacy sync_log tables have been column-patched. Keeping it out of the
-- Tauri startup migration prevents old local databases from crashing app launch
-- when they do not yet have next_retry_at.

-- Application settings and sync cursors.
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Local knowledge cache for top-secret mode.
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

-- Conversation history.
CREATE TABLE IF NOT EXISTS local_conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    system_prompt TEXT,
    model TEXT,
    mode TEXT DEFAULT 'cloud',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0,
    sync_version INTEGER DEFAULT 0
);

-- Offline task queue.
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

-- Harness artifact local cache for cross-device sync.
CREATE TABLE IF NOT EXISTS local_artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_artifacts_session ON local_artifacts(session_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_synced ON local_artifacts(synced);

-- Migration bookkeeping owned by the app schema.
CREATE TABLE IF NOT EXISTS db_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO db_migrations (version, name) VALUES (1, 'initial_schema');
INSERT OR IGNORE INTO db_migrations (version, name) VALUES (2, 'harness_offline_support');
