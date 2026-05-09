import { api } from './api'

export type SyncEntityType = 'conversation' | 'message' | 'document' | 'case' | 'contract' | 'setting'
export type SyncAction = 'create' | 'update' | 'delete' | 'upsert'

export interface SyncRecord {
  entity_type: SyncEntityType
  entity_id: string
  action: SyncAction
  data: Record<string, unknown>
  timestamp: string
  version: number
}

export interface SyncPushRequest {
  device_id: string
  last_sync_version: number
  records: SyncRecord[]
}

export interface SyncPushResponse {
  accepted: number
  rejected: number
  conflicts: Array<Record<string, unknown>>
  server_version: number
}

export interface SyncPullRequest {
  sinceVersion?: number
  entityTypes?: SyncEntityType[]
  limit?: number
}

export interface SyncPullRecord extends SyncRecord {
  id?: number | string
  server_version: number
  device_id?: string
  synced_at?: string
}

export interface SyncPullResponse {
  records: SyncPullRecord[]
  server_version: number
  has_more: boolean
}

export interface SyncApiClient {
  post<T>(url: string, data?: unknown, routeToken?: string): Promise<T>
  get<T>(url: string, routeToken?: string): Promise<T>
}

function syncPullPath(request: SyncPullRequest = {}): string {
  const params = new URLSearchParams({
    since_version: String(request.sinceVersion ?? 0),
    limit: String(request.limit ?? 100),
  })
  if (request.entityTypes?.length) {
    params.set('entity_types', request.entityTypes.join(','))
  }
  return `/sync/pull?${params.toString()}`
}

export function buildConversationSyncRecords(input: {
  conversationId: string
  title: string
  messageId: string
  content: string
  role?: 'user' | 'assistant' | 'system'
  timestamp: string
}): SyncRecord[] {
  return [
    {
      entity_type: 'conversation',
      entity_id: input.conversationId,
      action: 'upsert',
      data: {
        id: input.conversationId,
        title: input.title,
        mode: 'hybrid',
      },
      timestamp: input.timestamp,
      version: 1,
    },
    {
      entity_type: 'message',
      entity_id: input.messageId,
      action: 'create',
      data: {
        id: input.messageId,
        conversation_id: input.conversationId,
        content: input.content,
        role: input.role ?? 'user',
      },
      timestamp: input.timestamp,
      version: 1,
    },
  ]
}

export function pushSyncRecords(
  request: SyncPushRequest,
  client: SyncApiClient = api,
): Promise<SyncPushResponse> {
  return client.post<SyncPushResponse>('/sync/push', request)
}

export function pullSyncRecords(
  request: SyncPullRequest = {},
  client: SyncApiClient = api,
): Promise<SyncPullResponse> {
  return client.get<SyncPullResponse>(syncPullPath(request))
}
