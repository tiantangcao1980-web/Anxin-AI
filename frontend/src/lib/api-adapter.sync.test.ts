import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  buildConflictResolutionRequest,
  buildSyncPushPayload,
  calculateSyncRetryState,
  getDesktopSQLiteSecurityStatus,
  isDesktopDataNetworkAllowed,
  isSyncRetryDue,
  MAX_SYNC_RETRIES,
  normalizeRemoteSyncRecord,
  normalizeSyncApiBase,
  runLocalSyncWithDependencies,
  type SQLiteDB,
} from './api-adapter'

interface FakeSyncLogRow {
  id: number
  entity_type: string
  entity_id: string
  action: string
  data_json: string | null
  timestamp: string | null
  retry_count: number | null
  next_retry_at: string | null
  needs_human: number | null
  status: string
  error_message: string | null
}

class FakeSQLiteDB implements SQLiteDB {
  syncLog: FakeSyncLogRow[]
  settings = new Map<string, string>()
  messages = new Map<string, Record<string, unknown>>()
  documents = new Map<string, Record<string, unknown>>()

  constructor(options: {
    syncLog?: FakeSyncLogRow[]
    settings?: Record<string, string>
  } = {}) {
    this.syncLog = options.syncLog ?? []
    Object.entries(options.settings ?? {}).forEach(([key, value]) => this.settings.set(key, value))
  }

  async execute(sql: string, bindValues: unknown[] = []): Promise<{ rowsAffected: number }> {
    const normalized = this.normalizeSql(sql)

    if (normalized.includes('INSERT OR REPLACE INTO app_settings')) {
      this.settings.set(String(bindValues[0]), String(bindValues[1]))
      return { rowsAffected: 1 }
    }

    if (normalized.includes('UPDATE sync_log') && normalized.includes("status = 'synced'")) {
      const row = this.findSyncRow(Number(bindValues[0]))
      row.status = 'synced'
      row.error_message = null
      row.retry_count = 0
      row.next_retry_at = null
      row.needs_human = 0
      return { rowsAffected: 1 }
    }

    if (normalized.includes('UPDATE sync_log') && normalized.includes("status = 'failed'")) {
      const row = this.findSyncRow(Number(bindValues[4]))
      row.status = 'failed'
      row.error_message = String(bindValues[0])
      row.retry_count = Number(bindValues[1])
      row.next_retry_at = bindValues[2] === null ? null : String(bindValues[2])
      row.needs_human = Number(bindValues[3])
      return { rowsAffected: 1 }
    }

    if (normalized.includes('UPDATE sync_log') && normalized.includes("status = 'conflict'")) {
      const row = this.findSyncRow(Number(bindValues[1]))
      row.status = 'conflict'
      row.error_message = String(bindValues[0])
      row.next_retry_at = null
      row.needs_human = 1
      return { rowsAffected: 1 }
    }

    if (normalized.includes('UPDATE local_messages SET synced = 1')) {
      this.messages.set(String(bindValues[1]), {
        ...(this.messages.get(String(bindValues[1])) ?? {}),
        synced: 1,
        sync_version: Number(bindValues[0]),
      })
      return { rowsAffected: 1 }
    }

    if (normalized.includes('INSERT OR REPLACE INTO local_documents')) {
      this.documents.set(String(bindValues[0]), {
        id: bindValues[0],
        title: bindValues[1],
        content: bindValues[2],
        file_path: bindValues[3],
        file_size: bindValues[4],
        mime_type: bindValues[5],
        category: bindValues[6],
        updated_at: bindValues[7],
        synced: 1,
        sync_version: bindValues[8],
      })
      return { rowsAffected: 1 }
    }

    throw new Error(`Unexpected execute SQL in sync test: ${normalized}`)
  }

  async select<T>(sql: string, bindValues: unknown[] = []): Promise<T[]> {
    const normalized = this.normalizeSql(sql)

    if (normalized.includes('SELECT value FROM app_settings')) {
      const value = this.settings.get(String(bindValues[0]))
      return (value === undefined ? [] : [{ value }]) as T[]
    }

    if (normalized.includes('COUNT(*) AS count') && normalized.includes("status = 'failed'")) {
      const cutoff = String(bindValues[1])
      const maxRetries = Number(bindValues[0])
      return [{
        count: this.syncLog.filter((row) => (
          row.status === 'failed'
          && Number(row.needs_human ?? 0) === 0
          && Number(row.retry_count ?? 0) < maxRetries
          && row.next_retry_at !== null
          && row.next_retry_at > cutoff
        )).length,
      }] as T[]
    }

    if (normalized.includes('COUNT(*) AS count') && normalized.includes("status = 'conflict'")) {
      return [{
        count: this.syncLog.filter((row) => (
          row.status === 'conflict'
          || (row.status === 'failed' && Number(row.needs_human ?? 0) === 1)
        )).length,
      }] as T[]
    }

    if (normalized.includes('FROM sync_log') && normalized.includes('ORDER BY id ASC')) {
      const maxRetries = Number(bindValues[0])
      const now = String(bindValues[1])
      return this.syncLog
        .filter((row) => (
          row.status === 'pending'
          || (
            row.status === 'failed'
            && Number(row.needs_human ?? 0) === 0
            && Number(row.retry_count ?? 0) < maxRetries
            && (row.next_retry_at === null || row.next_retry_at <= now)
          )
        ))
        .sort((left, right) => left.id - right.id)
        .slice(0, Number(bindValues[2])) as T[]
    }

    throw new Error(`Unexpected select SQL in sync test: ${normalized}`)
  }

  private normalizeSql(sql: string): string {
    return sql.replace(/\s+/g, ' ').trim()
  }

  private findSyncRow(id: number): FakeSyncLogRow {
    const row = this.syncLog.find((candidate) => candidate.id === id)
    if (!row) throw new Error(`Unknown sync log row ${id}`)
    return row
  }
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('desktop sync helpers', () => {
  it('normalizes backend roots to the sync API base', () => {
    expect(normalizeSyncApiBase('http://localhost:8000')).toBe('http://localhost:8000/api/v1')
    expect(normalizeSyncApiBase('http://localhost:8000/api')).toBe('http://localhost:8000/api/v1')
    expect(normalizeSyncApiBase('http://localhost:8000/api/v1/')).toBe('http://localhost:8000/api/v1')
    expect(normalizeSyncApiBase(null, '/api/v1')).toBe('/api/v1')
  })

  it('blocks desktop data-network operations in top-secret mode', async () => {
    expect(isDesktopDataNetworkAllowed('top-secret')).toBe(false)
    expect(isDesktopDataNetworkAllowed('hybrid')).toBe(true)
    expect(isDesktopDataNetworkAllowed('cloud')).toBe(true)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    const result = await runLocalSyncWithDependencies({
      db: new FakeSQLiteDB(),
      apiBase: 'https://api.example.test/api/v1',
      token: 'token-a',
      mode: 'top-secret',
    })

    expect(result).toMatchObject({
      success: false,
      pushed: 0,
      pulled: 0,
      push_ok: false,
      pull_ok: false,
      message: '绝密模式下不允许同步本地数据到外部服务',
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('builds the backend push payload without leaking local sync_log ids', () => {
    const payload = buildSyncPushPayload([
      {
        entity_type: 'message',
        entity_id: 'msg-1',
        action: 'create',
        data: { content: 'hello' },
        timestamp: '2026-05-06T10:00:00Z',
        version: 3,
      },
    ], 'desktop-a', 12)

    expect(payload).toEqual({
      device_id: 'desktop-a',
      last_sync_version: 12,
      records: [
        {
          entity_type: 'message',
          entity_id: 'msg-1',
          action: 'create',
          data: { content: 'hello' },
          timestamp: '2026-05-06T10:00:00Z',
          version: 3,
        },
      ],
    })
    expect(payload.records[0]).not.toHaveProperty('id')
  })

  it('normalizes remote records defensively for local application', () => {
    const record = normalizeRemoteSyncRecord({
      entity_type: 'document',
      entity_id: 'doc-1',
      action: 'update',
      data: ['bad'],
      timestamp: '2026-05-06T10:00:00Z',
      version: '2',
      server_version: '9',
      device_id: 123,
    })

    expect(record).toMatchObject({
      entity_type: 'document',
      entity_id: 'doc-1',
      action: 'update',
      data: {},
      timestamp: '2026-05-06T10:00:00Z',
      version: 2,
      server_version: 9,
      device_id: '123',
    })
  })

  it('maps conflict choices to backend resolve payloads', () => {
    const conflict = {
      log_id: 7,
      entity_type: 'document',
      entity_id: 'doc-1',
      local_data: { title: '本地版本' },
      remote_data: { title: '云端版本' },
      local_timestamp: null,
      remote_timestamp: null,
    }

    expect(buildConflictResolutionRequest(conflict, 'keep_local')).toEqual({
      entity_type: 'document',
      entity_id: 'doc-1',
      resolution: 'merge',
      merged_data: { title: '本地版本' },
    })
    expect(buildConflictResolutionRequest(conflict, 'keep_remote')).toEqual({
      entity_type: 'document',
      entity_id: 'doc-1',
      resolution: 'keep_remote',
    })
    expect(buildConflictResolutionRequest(conflict, 'merge', { title: '合并版本' })).toEqual({
      entity_type: 'document',
      entity_id: 'doc-1',
      resolution: 'merge',
      merged_data: { title: '合并版本' },
    })
  })

  it('schedules failed sync rows with exponential backoff before human handoff', () => {
    const now = new Date('2026-05-06T10:00:00.000Z')

    expect(calculateSyncRetryState(0, now)).toEqual({
      retry_count: 1,
      next_retry_at: '2026-05-06T10:00:30.000Z',
      needs_human: false,
    })
    expect(calculateSyncRetryState(2, now)).toEqual({
      retry_count: 3,
      next_retry_at: '2026-05-06T10:05:00.000Z',
      needs_human: false,
    })
    expect(calculateSyncRetryState(MAX_SYNC_RETRIES - 1, now)).toEqual({
      retry_count: MAX_SYNC_RETRIES,
      next_retry_at: null,
      needs_human: true,
    })
  })

  it('treats missing or expired retry timestamps as due', () => {
    const now = new Date('2026-05-06T10:00:00.000Z')

    expect(isSyncRetryDue(null, now)).toBe(true)
    expect(isSyncRetryDue('bad-date', now)).toBe(true)
    expect(isSyncRetryDue('2026-05-06T09:59:59.000Z', now)).toBe(true)
    expect(isSyncRetryDue('2026-05-06T10:00:01.000Z', now)).toBe(false)
  })

  it('runs a local push and pull cycle against injected desktop SQLite dependencies', async () => {
    const db = new FakeSQLiteDB({
      settings: {
        'sync.last_server_version': '5',
      },
      syncLog: [
        {
          id: 1,
          entity_type: 'message',
          entity_id: 'msg-1',
          action: 'create',
          data_json: JSON.stringify({
            id: 'msg-1',
            conversation_id: 'conv-1',
            content: 'hello',
            role: 'user',
            sync_version: 0,
          }),
          timestamp: '2026-05-06T10:00:00.000Z',
          retry_count: 0,
          next_retry_at: null,
          needs_human: 0,
          status: 'pending',
          error_message: null,
        },
      ],
    })

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === 'https://api.example.test/api/v1/sync/push') {
        expect(init?.method).toBe('POST')
        const body = JSON.parse(String(init?.body))
        expect(body.device_id).toBe('desktop-a')
        expect(body.last_sync_version).toBe(5)
        expect(body.records).toHaveLength(1)
        expect(body.records[0]).not.toHaveProperty('id')
        return new Response(JSON.stringify({
          accepted: 1,
          conflicts: [],
          server_version: 6,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }

      expect(url).toBe('https://api.example.test/api/v1/sync/pull?since_version=6&limit=100')
      return new Response(JSON.stringify({
        records: [
          {
            entity_type: 'document',
            entity_id: 'doc-1',
            action: 'update',
            data: { title: '远端文档', content: 'remote body' },
            timestamp: '2026-05-06T10:01:00.000Z',
            server_version: 8,
          },
        ],
        server_version: 8,
        has_more: false,
      }), { status: 200, headers: { 'Content-Type': 'application/json' } })
    })

    const result = await runLocalSyncWithDependencies({
      db,
      apiBase: 'https://api.example.test/api/v1',
      token: 'token-a',
      deviceId: 'desktop-a',
      now: () => new Date('2026-05-06T10:02:00.000Z'),
      mode: 'hybrid',
    })

    expect(result).toMatchObject({
      success: true,
      pushed: 1,
      pulled: 1,
      conflicts: 0,
      push_ok: true,
      pull_ok: true,
      sync_time: '2026-05-06T10:02:00.000Z',
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(db.syncLog[0]).toMatchObject({ status: 'synced', retry_count: 0, needs_human: 0 })
    expect(db.messages.get('msg-1')).toMatchObject({ synced: 1, sync_version: 6 })
    expect(db.documents.get('doc-1')).toMatchObject({ title: '远端文档', sync_version: 8 })
    expect(db.settings.get('sync.last_server_version')).toBe('8')
    expect(db.settings.get('sync.last_sync_time')).toBe('2026-05-06T10:02:00.000Z')
  })

  it('marks failed push rows for bounded retry before the next sync attempt', async () => {
    const db = new FakeSQLiteDB({
      syncLog: [
        {
          id: 2,
          entity_type: 'message',
          entity_id: 'msg-2',
          action: 'create',
          data_json: JSON.stringify({ id: 'msg-2', conversation_id: 'conv-1', content: 'retry me' }),
          timestamp: '2026-05-06T10:00:00.000Z',
          retry_count: 0,
          next_retry_at: null,
          needs_human: 0,
          status: 'pending',
          error_message: null,
        },
      ],
    })

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === 'https://api.example.test/api/v1/sync/push') {
        return new Response(JSON.stringify({ message: 'temporarily unavailable' }), { status: 503 })
      }

      expect(url).toBe('https://api.example.test/api/v1/sync/pull?since_version=0&limit=100')
      return new Response(JSON.stringify({
        records: [],
        server_version: 0,
        has_more: false,
      }), { status: 200, headers: { 'Content-Type': 'application/json' } })
    })

    const result = await runLocalSyncWithDependencies({
      db,
      apiBase: 'https://api.example.test/api/v1',
      token: 'token-a',
      deviceId: 'desktop-a',
      mode: 'hybrid',
    })

    expect(result).toMatchObject({
      success: false,
      pushed: 0,
      pulled: 0,
      deferred: 1,
      needs_human: 0,
      push_ok: false,
      pull_ok: true,
      sync_time: null,
    })
    expect(db.syncLog[0].status).toBe('failed')
    expect(db.syncLog[0].error_message).toBe('push failed: 503')
    expect(db.syncLog[0].retry_count).toBe(1)
    expect(db.syncLog[0].next_retry_at).toBeTruthy()
    expect(db.syncLog[0].needs_human).toBe(0)
  })

  it('reports the current desktop SQLite encryption contract and reset phrase', () => {
    expect(getDesktopSQLiteSecurityStatus()).toEqual({
      storage_owner: 'rust-sqlcipher-keyring',
      engine: 'rusqlite/sqlcipher',
      encrypted: true,
      keyring_backed: true,
      release_blocking: false,
      reason: '桌面同步通过 Rust Tauri command 打开 SQLCipher 数据库，生产密钥存储在系统 keyring。',
      reset_confirmation: 'ERASE LOCAL DATA',
    })
  })
})
