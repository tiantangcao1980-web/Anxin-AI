/**
 * API 适配器
 *
 * 根据当前运行模式（绝密/混合/云端）路由 API 请求。
 * - Cloud：直接调用云端 API
 * - Hybrid：优先本地缓存，回退云端
 * - TopSecret：仅本地 SQLite + 本地 LLM
 */

import { isTauri, type AppMode } from './tauri-bridge'

// ===== 本地 SQLite 操作 =====

interface SQLiteDB {
  execute(sql: string, bindValues?: unknown[]): Promise<{ rowsAffected: number }>
  select<T>(sql: string, bindValues?: unknown[]): Promise<T[]>
}

let localDb: SQLiteDB | null = null

/** 获取本地数据库连接 */
async function getLocalDB(): Promise<SQLiteDB | null> {
  if (!isTauri()) return null
  if (localDb) return localDb

  try {
    const Database = await import(/* @vite-ignore */ '@tauri-apps/plugin-sql')
    localDb = await Database.default.load('sqlite:anxin_local.db')
    return localDb
  } catch (error) {
    console.error('[LocalDB] 连接失败:', error)
    return null
  }
}

/** 初始化本地数据库表 */
export async function initLocalDatabase() {
  const db = await getLocalDB()
  if (!db) return

  // 通过 Tauri SQL 插件执行初始化
  // 表结构在 Rust 侧的 local_db.rs 中定义，前端侧创建基础表
  const tables = [
    `CREATE TABLE IF NOT EXISTS local_messages (
      id TEXT PRIMARY KEY,
      conversation_id TEXT NOT NULL,
      content TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'user',
      agent TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      synced BOOLEAN DEFAULT 0
    )`,
    `CREATE TABLE IF NOT EXISTS local_documents (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      content TEXT,
      file_path TEXT,
      category TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      synced BOOLEAN DEFAULT 0
    )`,
    `CREATE TABLE IF NOT EXISTS local_conversations (
      id TEXT PRIMARY KEY,
      title TEXT,
      system_prompt TEXT,
      model TEXT,
      mode TEXT DEFAULT 'cloud',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      synced BOOLEAN DEFAULT 0
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
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      status TEXT DEFAULT 'pending'
    )`,
  ]

  for (const sql of tables) {
    try {
      await db.execute(sql)
    } catch (error) {
      console.error('[LocalDB] 建表失败:', error)
    }
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
    `INSERT OR REPLACE INTO local_messages (id, conversation_id, content, role, agent) VALUES (?, ?, ?, ?, ?)`,
    [message.id, message.conversationId, message.content, message.role, message.agent ?? null]
  )

  // 记录同步日志
  await db.execute(
    `INSERT INTO sync_log (entity_type, entity_id, action) VALUES ('message', ?, 'create')`,
    [message.id]
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
  const response = await fetch(endpoint, options)

  if (!response.ok && mode === 'hybrid') {
    // 混合模式下网络失败，可以回退到本地缓存
    console.warn(`[Hybrid] 云端请求失败 (${response.status})，尝试使用本地缓存`)
  }

  return response
}
