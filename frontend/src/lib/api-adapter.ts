/**
 * API 适配器
 *
 * 根据当前运行模式（绝密/混合/云端）路由 API 请求。
 * - Cloud：直接调用云端 API
 * - Hybrid：优先本地缓存，回退云端
 * - TopSecret：仅本地 SQLite + 本地 LLM
 */

import { getBackendUrl, isTauri, type AppMode } from './tauri-bridge'
import { API_BASE_URL, buildApiHeaders } from './api'
import { getTokenStorage } from './platform/storage'

// ===== 本地 SQLite 操作 =====

export interface SQLiteDB {
  execute(sql: string, bindValues?: unknown[]): Promise<{ rowsAffected: number }>
  select<T>(sql: string, bindValues?: unknown[]): Promise<T[]>
}

interface PendingSyncRow {
  id: number
  entity_type: string
  entity_id: string
  action: string
  data_json: string | null
  timestamp: string | null
  retry_count: number | null
  next_retry_at: string | null
  needs_human: number | null
}

interface LocalSyncRecord {
  entity_type: string
  entity_id: string
  action: string
  data: Record<string, unknown>
  timestamp: string
  version: number
}

interface RemoteSyncRecord extends LocalSyncRecord {
  id?: number | string
  server_version?: number
  device_id?: string
  synced_at?: string
}

export interface DesktopSyncResult {
  success: boolean
  message: string
  sync_time: string | null
  pushed: number
  pulled: number
  conflicts: number
  deferred: number
  needs_human: number
  push_ok: boolean
  pull_ok: boolean
}

export type SyncConflictResolution = 'keep_local' | 'keep_remote' | 'merge'

export interface LocalSyncConflict {
  log_id: number
  entity_type: string
  entity_id: string
  local_data: Record<string, unknown>
  remote_data: Record<string, unknown>
  local_timestamp: string | null
  remote_timestamp: string | null
}

export interface DesktopSQLiteSecurityStatus {
  storage_owner: 'rust-sqlcipher-keyring'
  engine: 'rusqlite/sqlcipher'
  encrypted: boolean
  keyring_backed: boolean
  release_blocking: boolean
  reason: string
  reset_confirmation: 'ERASE LOCAL DATA'
}

export interface DesktopLocalDataResetResult {
  dbPath: string
  keyringDeleted: boolean
  removedFiles: string[]
}

const SYNC_BATCH_LIMIT = 100
const SYNC_RETRY_DELAYS_MS = [
  30_000,
  2 * 60_000,
  5 * 60_000,
  15 * 60_000,
  30 * 60_000,
]
export const MAX_SYNC_RETRIES = SYNC_RETRY_DELAYS_MS.length
const LAST_SYNC_VERSION_KEY = 'sync.last_server_version'
const LAST_SYNC_TIME_KEY = 'sync.last_sync_time'
const DEVICE_ID_KEY = 'sync.device_id'

let localDb: SQLiteDB | null = null

export function getDesktopSQLiteSecurityStatus(): DesktopSQLiteSecurityStatus {
  return {
    storage_owner: 'rust-sqlcipher-keyring',
    engine: 'rusqlite/sqlcipher',
    encrypted: true,
    keyring_backed: true,
    release_blocking: false,
    reason: '桌面同步通过 Rust Tauri command 打开 SQLCipher 数据库，生产密钥存储在系统 keyring。',
    reset_confirmation: 'ERASE LOCAL DATA',
  }
}

async function invokeSecureSql<T>(cmd: string, args: Record<string, unknown>): Promise<T> {
  const internals = (window as unknown as {
    __TAURI_INTERNALS__?: {
      invoke?: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>
    }
  }).__TAURI_INTERNALS__

  if (!internals?.invoke) {
    throw new Error('Tauri invoke 不可用')
  }

  return internals.invoke<T>(cmd, args)
}

export async function resetDesktopLocalData(
  confirmation: string,
): Promise<DesktopLocalDataResetResult> {
  if (!isTauri()) {
    throw new Error('桌面本地数据重置仅支持 Tauri 桌面端')
  }

  localDb = null
  return invokeSecureSql<DesktopLocalDataResetResult>('secure_db_reset_local_data', {
    confirmation,
  })
}

/** 获取本地数据库连接 */
async function getLocalDB(): Promise<SQLiteDB | null> {
  if (!isTauri()) return null
  if (localDb) return localDb

  try {
    localDb = {
      execute: (sql: string, bindValues: unknown[] = []) => (
        invokeSecureSql<{ rowsAffected: number }>('secure_sql_execute', { sql, bindValues })
      ),
      select: <T>(sql: string, bindValues: unknown[] = []) => (
        invokeSecureSql<T[]>('secure_sql_select', { sql, bindValues })
      ),
    }
    return localDb
  } catch (error) {
    console.error('[LocalDB] 连接失败:', error)
    return null
  }
}

async function executeBestEffort(db: SQLiteDB, sql: string, bindValues?: unknown[]) {
  try {
    await db.execute(sql, bindValues)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (!/duplicate column|already exists/i.test(message)) {
      console.debug('[LocalDB] 兼容迁移跳过:', message)
    }
  }
}

/** 初始化本地数据库表 */
export async function initLocalDatabase() {
  const db = await getLocalDB()
  if (!db) return

  // 通过 Rust secure SQL commands 执行初始化
  // 表结构在 Rust 侧的 local_db.rs 中定义，前端侧创建基础表
  const tables = [
    `CREATE TABLE IF NOT EXISTS local_messages (
      id TEXT PRIMARY KEY,
      conversation_id TEXT NOT NULL,
      content TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'user',
      agent TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      synced BOOLEAN DEFAULT 0,
      sync_version INTEGER DEFAULT 0
    )`,
    `CREATE TABLE IF NOT EXISTS local_documents (
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
    )`,
    `CREATE TABLE IF NOT EXISTS local_conversations (
      id TEXT PRIMARY KEY,
      title TEXT,
      system_prompt TEXT,
      model TEXT,
      mode TEXT DEFAULT 'cloud',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      synced BOOLEAN DEFAULT 0,
      sync_version INTEGER DEFAULT 0
    )`,
    `CREATE TABLE IF NOT EXISTS local_cases (
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
    )`,
    `CREATE TABLE IF NOT EXISTS local_contracts (
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
    )`,
    `CREATE TABLE IF NOT EXISTS app_settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`,
    `CREATE TABLE IF NOT EXISTS sync_log (
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
    )`,
    `CREATE TABLE IF NOT EXISTS offline_tasks (
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
    )`,
    `CREATE TABLE IF NOT EXISTS local_artifacts (
      id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      artifact_type TEXT NOT NULL,
      data_json TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      synced BOOLEAN DEFAULT 0
    )`,
  ]

  for (const sql of tables) {
    try {
      await db.execute(sql)
    } catch (error) {
      console.error('[LocalDB] 建表失败:', error)
    }
  }

  const migrations = [
    `ALTER TABLE local_messages ADD COLUMN sync_version INTEGER DEFAULT 0`,
    `ALTER TABLE local_documents ADD COLUMN file_size INTEGER DEFAULT 0`,
    `ALTER TABLE local_documents ADD COLUMN mime_type TEXT`,
    `ALTER TABLE local_documents ADD COLUMN sync_version INTEGER DEFAULT 0`,
    `ALTER TABLE local_conversations ADD COLUMN sync_version INTEGER DEFAULT 0`,
    `ALTER TABLE sync_log ADD COLUMN data_json TEXT`,
    `ALTER TABLE sync_log ADD COLUMN error_message TEXT`,
    `ALTER TABLE sync_log ADD COLUMN retry_count INTEGER DEFAULT 0`,
    `ALTER TABLE sync_log ADD COLUMN next_retry_at DATETIME`,
    `ALTER TABLE sync_log ADD COLUMN needs_human BOOLEAN DEFAULT 0`,
    `CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_log(status)`,
    `CREATE INDEX IF NOT EXISTS idx_sync_entity ON sync_log(entity_type, entity_id)`,
    `CREATE INDEX IF NOT EXISTS idx_sync_retry_due ON sync_log(status, next_retry_at)`,
    `CREATE INDEX IF NOT EXISTS idx_messages_synced ON local_messages(synced)`,
    `CREATE INDEX IF NOT EXISTS idx_documents_synced ON local_documents(synced)`,
    `CREATE INDEX IF NOT EXISTS idx_offline_tasks_status ON offline_tasks(status)`,
    `CREATE INDEX IF NOT EXISTS idx_artifacts_session ON local_artifacts(session_id)`,
    `CREATE INDEX IF NOT EXISTS idx_artifacts_synced ON local_artifacts(synced)`,
  ]

  for (const sql of migrations) {
    await executeBestEffort(db, sql)
  }
}

// ===== 本地消息操作 =====

export async function saveLocalMessage(message: {
  id: string
  conversationId: string
  content: string
  role: string
  agent?: string
}) {
  const db = await getLocalDB()
  if (!db) return

  await db.execute(
    `INSERT OR REPLACE INTO local_messages (id, conversation_id, content, role, agent, synced)
     VALUES (?, ?, ?, ?, ?, 0)`,
    [message.id, message.conversationId, message.content, message.role, message.agent ?? null]
  )

  // 记录同步日志
  const data = {
    id: message.id,
    conversation_id: message.conversationId,
    content: message.content,
    role: message.role,
    agent: message.agent ?? null,
  }
  await db.execute(
    `INSERT INTO sync_log (entity_type, entity_id, action, data_json, status)
     VALUES ('message', ?, 'create', ?, 'pending')`,
    [message.id, JSON.stringify(data)]
  )
}

export async function getLocalMessages(conversationId: string) {
  const db = await getLocalDB()
  if (!db) return []

  return db.select<{
    id: string
    conversation_id: string
    content: string
    role: string
    agent: string | null
    created_at: string
  }>(
    `SELECT * FROM local_messages WHERE conversation_id = ? ORDER BY created_at ASC`,
    [conversationId]
  )
}

// ===== 本地对话操作 =====

export async function saveLocalConversation(conv: {
  id: string
  title: string
  systemPrompt?: string
  model?: string
  mode: string
}) {
  const db = await getLocalDB()
  if (!db) return

  await db.execute(
    `INSERT OR REPLACE INTO local_conversations (id, title, system_prompt, model, mode, updated_at)
     VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`,
    [conv.id, conv.title, conv.systemPrompt ?? null, conv.model ?? null, conv.mode]
  )

  await db.execute(
    `INSERT INTO sync_log (entity_type, entity_id, action, data_json, status)
     VALUES ('conversation', ?, 'update', ?, 'pending')`,
    [conv.id, JSON.stringify({
      id: conv.id,
      title: conv.title,
      system_prompt: conv.systemPrompt ?? null,
      model: conv.model ?? null,
      mode: conv.mode,
    })]
  )
}

export async function getLocalConversations() {
  const db = await getLocalDB()
  if (!db) return []

  return db.select<{
    id: string
    title: string
    system_prompt: string | null
    model: string | null
    mode: string
    created_at: string
    updated_at: string
  }>(`SELECT * FROM local_conversations ORDER BY updated_at DESC`)
}

// ===== 本地设置 =====

export async function getLocalSetting(key: string): Promise<string | null> {
  const db = await getLocalDB()
  if (!db) return null

  const rows = await db.select<{ value: string }>(
    `SELECT value FROM app_settings WHERE key = ?`,
    [key]
  )
  return rows.length > 0 ? rows[0].value : null
}

export async function setLocalSetting(key: string, value: string) {
  const db = await getLocalDB()
  if (!db) return

  await db.execute(
    `INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)`,
    [key, value]
  )
}

// ===== 桌面同步 =====

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

export function normalizeSyncApiBase(configuredUrl: string | null | undefined, fallback = API_BASE_URL): string {
  const raw = (configuredUrl || fallback || '/api/v1').trim()
  const trimmed = trimTrailingSlash(raw)

  if (!trimmed) return '/api/v1'
  if (/\/api\/v\d+$/i.test(trimmed)) return trimmed
  if (/\/api$/i.test(trimmed)) return `${trimmed}/v1`
  return `${trimmed}/api/v1`
}

function parseJsonObject(value: string | null | undefined): Record<string, unknown> {
  if (!value) return {}
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

function toNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function calculateSyncRetryState(
  currentRetryCount: number | null | undefined,
  now = new Date(),
): { retry_count: number; next_retry_at: string | null; needs_human: boolean } {
  const retryCount = Math.max(0, Math.floor(toNumber(currentRetryCount, 0))) + 1

  if (retryCount >= MAX_SYNC_RETRIES) {
    return {
      retry_count: retryCount,
      next_retry_at: null,
      needs_human: true,
    }
  }

  const delay = SYNC_RETRY_DELAYS_MS[Math.min(retryCount - 1, SYNC_RETRY_DELAYS_MS.length - 1)]
  return {
    retry_count: retryCount,
    next_retry_at: new Date(now.getTime() + delay).toISOString(),
    needs_human: false,
  }
}

export function isSyncRetryDue(nextRetryAt: string | null | undefined, now = new Date()): boolean {
  if (!nextRetryAt) return true
  const dueAt = Date.parse(nextRetryAt)
  return !Number.isFinite(dueAt) || dueAt <= now.getTime()
}

async function readSetting(db: SQLiteDB, key: string): Promise<string | null> {
  const rows = await db.select<{ value: string }>(
    `SELECT value FROM app_settings WHERE key = ?`,
    [key]
  )
  return rows[0]?.value ?? null
}

async function writeSetting(db: SQLiteDB, key: string, value: string) {
  await db.execute(
    `INSERT OR REPLACE INTO app_settings (key, value, updated_at)
     VALUES (?, ?, CURRENT_TIMESTAMP)`,
    [key, value]
  )
}

async function getDeviceId(db: SQLiteDB): Promise<string> {
  const existing = await readSetting(db, DEVICE_ID_KEY)
  if (existing) return existing

  const generated = globalThis.crypto?.randomUUID?.() ?? `desktop-${Date.now()}-${Math.random().toString(16).slice(2)}`
  await writeSetting(db, DEVICE_ID_KEY, generated)
  return generated
}

async function readLastSyncVersion(db: SQLiteDB): Promise<number> {
  return toNumber(await readSetting(db, LAST_SYNC_VERSION_KEY), 0)
}

async function writeLastSyncVersion(db: SQLiteDB, version: number) {
  await writeSetting(db, LAST_SYNC_VERSION_KEY, String(Math.max(0, Math.floor(version))))
}

async function resolveBackendApiBase(): Promise<string> {
  const storage = getTokenStorage()
  const storedUrl = await storage.getBackendUrl()
  const nativeUrl = storedUrl ? null : await getBackendUrl()
  return normalizeSyncApiBase(storedUrl || nativeUrl || API_BASE_URL)
}

async function readEntityPayload(db: SQLiteDB, entityType: string, entityId: string): Promise<Record<string, unknown>> {
  switch (entityType) {
    case 'message': {
      const rows = await db.select<Record<string, unknown>>(
        `SELECT id, conversation_id, content, role, agent, created_at, sync_version
         FROM local_messages WHERE id = ?`,
        [entityId]
      )
      return rows[0] ?? {}
    }
    case 'document': {
      const rows = await db.select<Record<string, unknown>>(
        `SELECT id, title, content, file_path, file_size, mime_type, category, created_at, updated_at, sync_version
         FROM local_documents WHERE id = ?`,
        [entityId]
      )
      return rows[0] ?? {}
    }
    case 'conversation': {
      const rows = await db.select<Record<string, unknown>>(
        `SELECT id, title, system_prompt, model, mode, created_at, updated_at, sync_version
         FROM local_conversations WHERE id = ?`,
        [entityId]
      )
      return rows[0] ?? {}
    }
    case 'case': {
      const rows = await db.select<Record<string, unknown>>(
        `SELECT id, title, description, status, case_type, priority, data_json, created_at, updated_at, sync_version
         FROM local_cases WHERE id = ?`,
        [entityId]
      )
      return rows[0] ?? {}
    }
    case 'contract': {
      const rows = await db.select<Record<string, unknown>>(
        `SELECT id, title, content, contract_type, status, parties_json, review_result_json, created_at, updated_at, sync_version
         FROM local_contracts WHERE id = ?`,
        [entityId]
      )
      return rows[0] ?? {}
    }
    case 'setting': {
      const value = await readSetting(db, entityId)
      return value === null ? {} : { key: entityId, value }
    }
    default:
      return {}
  }
}

async function hydratePendingRecord(db: SQLiteDB, row: PendingSyncRow): Promise<LocalSyncRecord> {
  const explicitData = parseJsonObject(row.data_json)
  const entityData = Object.keys(explicitData).length > 0
    ? explicitData
    : await readEntityPayload(db, row.entity_type, row.entity_id)

  return {
    entity_type: row.entity_type,
    entity_id: row.entity_id,
    action: row.action,
    data: entityData,
    timestamp: row.timestamp ?? new Date().toISOString(),
    version: toNumber(entityData.sync_version, 0),
  }
}

export function buildSyncPushPayload(
  records: LocalSyncRecord[],
  deviceId: string,
  lastSyncVersion: number,
) {
  return {
    device_id: deviceId,
    records,
    last_sync_version: lastSyncVersion,
  }
}

export function normalizeRemoteSyncRecord(record: Record<string, unknown>): RemoteSyncRecord {
  return {
    entity_type: String(record.entity_type ?? ''),
    entity_id: String(record.entity_id ?? ''),
    action: String(record.action ?? 'update'),
    data: record.data && typeof record.data === 'object' && !Array.isArray(record.data)
      ? record.data as Record<string, unknown>
      : {},
    timestamp: String(record.timestamp ?? record.synced_at ?? new Date().toISOString()),
    version: toNumber(record.version, 0),
    server_version: toNumber(record.server_version, 0),
    device_id: record.device_id === undefined ? undefined : String(record.device_id),
    synced_at: record.synced_at === undefined ? undefined : String(record.synced_at),
  }
}

function normalizeConflict(row: {
  id: number
  entity_type: string
  entity_id: string
  error_message: string | null
}): LocalSyncConflict {
  const details = parseJsonObject(row.error_message)
  return {
    log_id: row.id,
    entity_type: String(details.entity_type ?? row.entity_type),
    entity_id: String(details.entity_id ?? row.entity_id),
    local_data: details.local_data && typeof details.local_data === 'object' && !Array.isArray(details.local_data)
      ? details.local_data as Record<string, unknown>
      : {},
    remote_data: details.remote_data && typeof details.remote_data === 'object' && !Array.isArray(details.remote_data)
      ? details.remote_data as Record<string, unknown>
      : {},
    local_timestamp: details.local_timestamp ? String(details.local_timestamp) : null,
    remote_timestamp: details.remote_timestamp ? String(details.remote_timestamp) : null,
  }
}

export function buildConflictResolutionRequest(
  conflict: LocalSyncConflict,
  resolution: SyncConflictResolution,
  mergedData?: Record<string, unknown>,
) {
  if (resolution === 'keep_local') {
    return {
      entity_type: conflict.entity_type,
      entity_id: conflict.entity_id,
      resolution: 'merge',
      merged_data: conflict.local_data,
    }
  }

  if (resolution === 'merge') {
    return {
      entity_type: conflict.entity_type,
      entity_id: conflict.entity_id,
      resolution,
      merged_data: mergedData ?? conflict.local_data,
    }
  }

  return {
    entity_type: conflict.entity_type,
    entity_id: conflict.entity_id,
    resolution,
  }
}

async function readPendingSyncRows(db: SQLiteDB): Promise<PendingSyncRow[]> {
  const now = new Date().toISOString()
  return db.select<PendingSyncRow>(
    `SELECT id, entity_type, entity_id, action, data_json, timestamp, retry_count, next_retry_at, needs_human
     FROM sync_log
     WHERE (
       status = 'pending'
       OR (
         status = 'failed'
         AND COALESCE(needs_human, 0) = 0
         AND COALESCE(retry_count, 0) < ?
         AND (next_retry_at IS NULL OR next_retry_at <= ?)
       )
     )
     ORDER BY id ASC
     LIMIT ?`,
    [MAX_SYNC_RETRIES, now, SYNC_BATCH_LIMIT]
  )
}

async function markRowsSynced(db: SQLiteDB, rows: PendingSyncRow[], serverVersion: number) {
  for (const row of rows) {
    await db.execute(
      `UPDATE sync_log
       SET status = 'synced',
           error_message = NULL,
           retry_count = 0,
           next_retry_at = NULL,
           needs_human = 0
       WHERE id = ?`,
      [row.id]
    )
    await markLocalEntitySynced(db, row.entity_type, row.entity_id, serverVersion)
  }
}

async function markRowsFailed(db: SQLiteDB, rows: PendingSyncRow[], message: string) {
  for (const row of rows) {
    const retry = calculateSyncRetryState(row.retry_count)
    await db.execute(
      `UPDATE sync_log
       SET status = 'failed',
           error_message = ?,
           retry_count = ?,
           next_retry_at = ?,
           needs_human = ?
       WHERE id = ?`,
      [message, retry.retry_count, retry.next_retry_at, retry.needs_human ? 1 : 0, row.id]
    )
  }
}

async function markRowsConflicted(db: SQLiteDB, rows: PendingSyncRow[], conflicts: Record<string, unknown>[]) {
  const conflictKeys = new Set(conflicts.map((conflict) => `${conflict.entity_type}:${conflict.entity_id}`))
  for (const row of rows) {
    if (!conflictKeys.has(`${row.entity_type}:${row.entity_id}`)) continue
    await db.execute(
      `UPDATE sync_log
       SET status = 'conflict',
           error_message = ?,
           next_retry_at = NULL,
           needs_human = 1
       WHERE id = ?`,
      [JSON.stringify(conflicts.find((conflict) => (
        conflict.entity_type === row.entity_type && conflict.entity_id === row.entity_id
      )) ?? {}), row.id]
    )
  }
}

async function markLocalEntitySynced(db: SQLiteDB, entityType: string, entityId: string, serverVersion: number) {
  const statements: Record<string, string> = {
    message: `UPDATE local_messages SET synced = 1, sync_version = ? WHERE id = ?`,
    document: `UPDATE local_documents SET synced = 1, sync_version = ? WHERE id = ?`,
    conversation: `UPDATE local_conversations SET synced = 1, sync_version = ? WHERE id = ?`,
    case: `UPDATE local_cases SET synced = 1, sync_version = ? WHERE id = ?`,
    contract: `UPDATE local_contracts SET synced = 1, sync_version = ? WHERE id = ?`,
  }
  const sql = statements[entityType]
  if (sql) {
    await executeBestEffort(db, sql, [serverVersion, entityId])
  }
}

async function countDeferredSyncRows(db: SQLiteDB): Promise<number> {
  const rows = await db.select<{ count: number }>(
    `SELECT COUNT(*) AS count
     FROM sync_log
     WHERE status = 'failed'
       AND COALESCE(needs_human, 0) = 0
       AND COALESCE(retry_count, 0) < ?
       AND next_retry_at IS NOT NULL
       AND next_retry_at > ?`,
    [MAX_SYNC_RETRIES, new Date().toISOString()]
  )
  return toNumber(rows[0]?.count, 0)
}

async function countNeedsHumanSyncRows(db: SQLiteDB): Promise<number> {
  const rows = await db.select<{ count: number }>(
    `SELECT COUNT(*) AS count
     FROM sync_log
     WHERE status = 'conflict'
        OR (status = 'failed' AND COALESCE(needs_human, 0) = 1)`
  )
  return toNumber(rows[0]?.count, 0)
}

async function pushPendingRecords(
  db: SQLiteDB,
  apiBase: string,
  token: string,
  deviceId: string,
): Promise<{
  ok: boolean
  pushed: number
  conflicts: number
  deferred: number
  needsHuman: number
  serverVersion: number
}> {
  const pendingRows = await readPendingSyncRows(db)
  const lastSyncVersion = await readLastSyncVersion(db)

  if (pendingRows.length === 0) {
    return {
      ok: true,
      pushed: 0,
      conflicts: 0,
      deferred: await countDeferredSyncRows(db),
      needsHuman: await countNeedsHumanSyncRows(db),
      serverVersion: lastSyncVersion,
    }
  }

  const records = await Promise.all(pendingRows.map((row) => hydratePendingRecord(db, row)))
  const response = await fetch(`${apiBase}/sync/push`, {
    method: 'POST',
    headers: buildApiHeaders(undefined, { token }),
    body: JSON.stringify(buildSyncPushPayload(records, deviceId, lastSyncVersion)),
  })

  if (!response.ok) {
    await markRowsFailed(db, pendingRows, `push failed: ${response.status}`)
    return {
      ok: false,
      pushed: 0,
      conflicts: 0,
      deferred: await countDeferredSyncRows(db),
      needsHuman: await countNeedsHumanSyncRows(db),
      serverVersion: lastSyncVersion,
    }
  }

  const body = await response.json() as {
    accepted?: number
    conflicts?: Record<string, unknown>[]
    server_version?: number
  }
  const conflicts = body.conflicts ?? []
  const conflictKeys = new Set(conflicts.map((conflict) => `${conflict.entity_type}:${conflict.entity_id}`))
  const acceptedRows = pendingRows.filter((row) => !conflictKeys.has(`${row.entity_type}:${row.entity_id}`))
  const serverVersion = toNumber(body.server_version, lastSyncVersion)

  await markRowsSynced(db, acceptedRows, serverVersion)
  await markRowsConflicted(db, pendingRows, conflicts)
  await writeLastSyncVersion(db, serverVersion)

  return {
    ok: true,
    pushed: toNumber(body.accepted, acceptedRows.length),
    conflicts: conflicts.length,
    deferred: await countDeferredSyncRows(db),
    needsHuman: await countNeedsHumanSyncRows(db),
    serverVersion,
  }
}

async function applyRemoteRecord(db: SQLiteDB, record: RemoteSyncRecord) {
  const data = record.data
  const serverVersion = record.server_version ?? 0
  const entityId = record.entity_id

  if (record.action === 'delete') {
    const deleteStatements: Record<string, string> = {
      message: `DELETE FROM local_messages WHERE id = ?`,
      document: `DELETE FROM local_documents WHERE id = ?`,
      conversation: `DELETE FROM local_conversations WHERE id = ?`,
      case: `DELETE FROM local_cases WHERE id = ?`,
      contract: `DELETE FROM local_contracts WHERE id = ?`,
    }
    const sql = deleteStatements[record.entity_type]
    if (sql) await db.execute(sql, [entityId])
    return
  }

  switch (record.entity_type) {
    case 'message':
      await db.execute(
        `INSERT OR REPLACE INTO local_messages
         (id, conversation_id, content, role, agent, created_at, synced, sync_version)
         VALUES (?, ?, ?, ?, ?, ?, 1, ?)`,
        [
          entityId,
          data.conversation_id ?? data.conversationId ?? '',
          data.content ?? '',
          data.role ?? 'user',
          data.agent ?? null,
          data.created_at ?? record.timestamp,
          serverVersion,
        ]
      )
      break
    case 'document':
      await db.execute(
        `INSERT OR REPLACE INTO local_documents
         (id, title, content, file_path, file_size, mime_type, category, updated_at, synced, sync_version)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`,
        [
          entityId,
          data.title ?? '未命名文档',
          data.content ?? null,
          data.file_path ?? data.filePath ?? null,
          data.file_size ?? data.fileSize ?? 0,
          data.mime_type ?? data.mimeType ?? null,
          data.category ?? null,
          data.updated_at ?? record.timestamp,
          serverVersion,
        ]
      )
      break
    case 'conversation':
      await db.execute(
        `INSERT OR REPLACE INTO local_conversations
         (id, title, system_prompt, model, mode, updated_at, synced, sync_version)
         VALUES (?, ?, ?, ?, ?, ?, 1, ?)`,
        [
          entityId,
          data.title ?? '未命名对话',
          data.system_prompt ?? data.systemPrompt ?? null,
          data.model ?? null,
          data.mode ?? 'cloud',
          data.updated_at ?? record.timestamp,
          serverVersion,
        ]
      )
      break
    case 'case':
      await db.execute(
        `INSERT OR REPLACE INTO local_cases
         (id, title, description, status, case_type, priority, data_json, updated_at, synced, sync_version)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`,
        [
          entityId,
          data.title ?? '未命名案件',
          data.description ?? null,
          data.status ?? 'pending',
          data.case_type ?? data.caseType ?? null,
          data.priority ?? 'medium',
          data.data_json ?? JSON.stringify(data),
          data.updated_at ?? record.timestamp,
          serverVersion,
        ]
      )
      break
    case 'contract':
      await db.execute(
        `INSERT OR REPLACE INTO local_contracts
         (id, title, content, contract_type, status, parties_json, review_result_json, updated_at, synced, sync_version)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`,
        [
          entityId,
          data.title ?? '未命名合同',
          data.content ?? null,
          data.contract_type ?? data.contractType ?? null,
          data.status ?? 'draft',
          data.parties_json ?? JSON.stringify(data.parties ?? []),
          data.review_result_json ?? JSON.stringify(data.review_result ?? data.reviewResult ?? null),
          data.updated_at ?? record.timestamp,
          serverVersion,
        ]
      )
      break
    case 'setting':
      await writeSetting(db, entityId, String(data.value ?? ''))
      break
    default:
      if (record.entity_type.startsWith('harness_artifact_')) {
        const artifactType = record.entity_type.replace('harness_artifact_', '')
        await db.execute(
          `INSERT OR REPLACE INTO local_artifacts
           (id, session_id, artifact_type, data_json, created_at, synced)
           VALUES (?, ?, ?, ?, ?, 1)`,
          [
            entityId,
            data.session_id ?? String(entityId).split(':')[0],
            data.artifact_type ?? artifactType,
            JSON.stringify(data.data ?? data),
            record.timestamp,
          ]
        )
      }
  }
}

async function pullIncrementalUpdates(
  db: SQLiteDB,
  apiBase: string,
  token: string,
): Promise<{ ok: boolean; pulled: number; serverVersion: number }> {
  let cursor = await readLastSyncVersion(db)
  let pulled = 0
  let hasMore = true

  while (hasMore) {
    const response = await fetch(`${apiBase}/sync/pull?since_version=${cursor}&limit=${SYNC_BATCH_LIMIT}`, {
      headers: buildApiHeaders(undefined, { token, json: false }),
    })

    if (!response.ok) {
      return { ok: false, pulled, serverVersion: cursor }
    }

    const body = await response.json() as {
      records?: Record<string, unknown>[]
      server_version?: number
      has_more?: boolean
    }
    const records = (body.records ?? []).map(normalizeRemoteSyncRecord)
    for (const record of records) {
      await applyRemoteRecord(db, record)
      cursor = Math.max(cursor, record.server_version ?? 0)
      pulled += 1
    }

    cursor = Math.max(cursor, toNumber(body.server_version, cursor))
    hasMore = Boolean(body.has_more && records.length > 0)
  }

  await writeLastSyncVersion(db, cursor)
  return { ok: true, pulled, serverVersion: cursor }
}

export async function runLocalSyncWithDependencies(params: {
  db: SQLiteDB
  apiBase: string
  token: string
  deviceId?: string
  now?: () => Date
}): Promise<DesktopSyncResult> {
  const deviceId = params.deviceId ?? await getDeviceId(params.db)
  const push = await pushPendingRecords(params.db, params.apiBase, params.token, deviceId)
  const pull = await pullIncrementalUpdates(params.db, params.apiBase, params.token)
  const success = push.ok && pull.ok
  const syncTime = success ? (params.now?.() ?? new Date()).toISOString() : null
  const notices = []

  if (push.deferred > 0) {
    notices.push(`${push.deferred} 条记录等待退避重试`)
  }
  if (push.needsHuman > 0) {
    notices.push(`${push.needsHuman} 条记录需要人工处理`)
  }

  if (syncTime) {
    await writeSetting(params.db, LAST_SYNC_TIME_KEY, syncTime)
  }

  return {
    success,
    message: success
      ? ['同步完成', ...notices].join('，')
      : ['同步未完成，请检查网络或登录状态', ...notices].join('，'),
    sync_time: syncTime,
    pushed: push.pushed,
    pulled: pull.pulled,
    conflicts: push.conflicts,
    deferred: push.deferred,
    needs_human: push.needsHuman,
    push_ok: push.ok,
    pull_ok: pull.ok,
  }
}

export async function getPendingLocalSyncCount(): Promise<number | null> {
  const db = await getLocalDB()
  if (!db) return null
  await initLocalDatabase()
  const rows = await db.select<{ count: number }>(
    `SELECT COUNT(*) AS count
     FROM sync_log
     WHERE status = 'pending'
        OR (
          status = 'failed'
          AND COALESCE(needs_human, 0) = 0
          AND COALESCE(retry_count, 0) < ?
        )`,
    [MAX_SYNC_RETRIES]
  )
  return toNumber(rows[0]?.count, 0)
}

export async function listLocalSyncConflicts(): Promise<LocalSyncConflict[] | null> {
  const db = await getLocalDB()
  if (!db) return null
  await initLocalDatabase()

  const rows = await db.select<{
    id: number
    entity_type: string
    entity_id: string
    error_message: string | null
  }>(
    `SELECT id, entity_type, entity_id, error_message
     FROM sync_log
     WHERE status = 'conflict'
     ORDER BY timestamp ASC, id ASC`
  )
  return rows.map(normalizeConflict)
}

export async function resolveLocalSyncConflict(
  logId: number,
  resolution: SyncConflictResolution,
  mergedData?: Record<string, unknown>,
): Promise<{ success: boolean; message: string } | null> {
  const db = await getLocalDB()
  if (!db) return null
  await initLocalDatabase()

  const rows = await db.select<{
    id: number
    entity_type: string
    entity_id: string
    error_message: string | null
  }>(
    `SELECT id, entity_type, entity_id, error_message
     FROM sync_log
     WHERE id = ? AND status = 'conflict'
     LIMIT 1`,
    [logId]
  )
  const row = rows[0]
  if (!row) {
    return { success: false, message: '未找到待解决的同步冲突' }
  }

  const conflict = normalizeConflict(row)
  if (resolution === 'keep_remote') {
    await applyRemoteRecord(db, {
      entity_type: conflict.entity_type,
      entity_id: conflict.entity_id,
      action: 'update',
      data: conflict.remote_data,
      timestamp: conflict.remote_timestamp ?? new Date().toISOString(),
      version: 0,
      server_version: 0,
    })
    await db.execute(
      `UPDATE sync_log
       SET status = 'synced',
           error_message = NULL,
           retry_count = 0,
           next_retry_at = NULL,
           needs_human = 0
       WHERE id = ?`,
      [logId]
    )
    return { success: true, message: '已保留云端版本' }
  }

  const token = await getTokenStorage().getAccessToken()
  if (!token) {
    return { success: false, message: '请先登录后再解决同步冲突' }
  }

  const apiBase = await resolveBackendApiBase()
  const response = await fetch(`${apiBase}/sync/resolve`, {
    method: 'POST',
    headers: buildApiHeaders(undefined, { token }),
    body: JSON.stringify(buildConflictResolutionRequest(conflict, resolution, mergedData)),
  })

  if (!response.ok) {
    return { success: false, message: `同步冲突解决失败: ${response.status}` }
  }

  if (resolution === 'merge' && mergedData) {
    await applyRemoteRecord(db, {
      entity_type: conflict.entity_type,
      entity_id: conflict.entity_id,
      action: 'update',
      data: mergedData,
      timestamp: new Date().toISOString(),
      version: 0,
      server_version: await readLastSyncVersion(db),
    })
  }

  await db.execute(
    `UPDATE sync_log
     SET status = 'synced',
         error_message = NULL,
         retry_count = 0,
         next_retry_at = NULL,
         needs_human = 0
     WHERE id = ?`,
    [logId]
  )
  await markLocalEntitySynced(db, conflict.entity_type, conflict.entity_id, await readLastSyncVersion(db))
  return { success: true, message: resolution === 'keep_local' ? '已保留本地版本' : '已提交合并版本' }
}

export async function triggerLocalSync(): Promise<DesktopSyncResult | null> {
  const db = await getLocalDB()
  if (!db) return null

  await initLocalDatabase()

  const storage = getTokenStorage()
  const token = await storage.getAccessToken()
  if (!token) {
    return {
      success: false,
      message: '请先登录后再同步',
      sync_time: null,
      pushed: 0,
      pulled: 0,
      conflicts: 0,
      deferred: 0,
      needs_human: 0,
      push_ok: false,
      pull_ok: false,
    }
  }

  const apiBase = await resolveBackendApiBase()
  return runLocalSyncWithDependencies({ db, apiBase, token })
}

// ===== 模式感知请求 =====

/**
 * 根据运行模式路由 API 请求
 *
 * - cloud: 直接调用云端 API
 * - hybrid: 优先云端，失败时回退本地缓存
 * - top-secret: 仅本地操作
 */
export async function adaptedFetch(
  endpoint: string,
  options: RequestInit = {},
  mode: AppMode = 'cloud'
): Promise<Response> {
  if (mode === 'top-secret') {
    // 绝密模式：拒绝网络请求，返回本地数据
    throw new Error('绝密模式下不允许网络请求，请使用本地 API')
  }

  // 云端或混合模式：正常发送请求
  const response = await fetch(endpoint, {
    ...options,
    headers: buildApiHeaders(options.headers, {
      json: !(options.body instanceof FormData),
      privacyMode: mode === 'hybrid' ? 'hybrid' : 'cloud',
    }),
  })

  if (!response.ok && mode === 'hybrid') {
    // 混合模式下网络失败，可以回退到本地缓存
    console.warn(`[Hybrid] 云端请求失败 (${response.status})，尝试使用本地缓存`)
  }

  return response
}
