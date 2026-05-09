import { describe, expect, it } from 'vitest'
import {
  buildConversationSyncRecords,
  pullSyncRecords,
  pushSyncRecords,
  type SyncApiClient,
} from './sync'

describe('uni-mobile sync client', () => {
  it('builds conversation continuation records without local-only ids', () => {
    const records = buildConversationSyncRecords({
      conversationId: 'conv-cross-1',
      title: '跨端会话',
      messageId: 'msg-mobile-1',
      content: '移动端继续回复',
      timestamp: '2026-05-06T10:01:00Z',
    })

    expect(records).toEqual([
      {
        entity_type: 'conversation',
        entity_id: 'conv-cross-1',
        action: 'upsert',
        data: {
          id: 'conv-cross-1',
          title: '跨端会话',
          mode: 'hybrid',
        },
        timestamp: '2026-05-06T10:01:00Z',
        version: 1,
      },
      {
        entity_type: 'message',
        entity_id: 'msg-mobile-1',
        action: 'create',
        data: {
          id: 'msg-mobile-1',
          conversation_id: 'conv-cross-1',
          content: '移动端继续回复',
          role: 'user',
        },
        timestamp: '2026-05-06T10:01:00Z',
        version: 1,
      },
    ])
    expect(records[0]).not.toHaveProperty('id')
  })

  it('uses the shared backend sync endpoints for push and pull', async () => {
    const calls: Array<{ method: 'GET' | 'POST'; url: string; data?: unknown }> = []
    const client: SyncApiClient = {
      async post<T>(url: string, data?: unknown): Promise<T> {
        calls.push({ method: 'POST', url, data })
        return {
          accepted: 1,
          rejected: 0,
          conflicts: [],
          server_version: 3,
        } as T
      },
      async get<T>(url: string): Promise<T> {
        calls.push({ method: 'GET', url })
        return {
          records: [
            {
              entity_type: 'message',
              entity_id: 'msg-desktop-1',
              action: 'create',
              data: { conversation_id: 'conv-cross-1', content: '桌面端先发起' },
              timestamp: '2026-05-06T10:00:00Z',
              version: 1,
              server_version: 2,
              device_id: 'desktop-a',
            },
          ],
          server_version: 3,
          has_more: false,
        } as T
      },
    }

    const records = buildConversationSyncRecords({
      conversationId: 'conv-cross-1',
      title: '跨端会话',
      messageId: 'msg-mobile-1',
      content: '移动端继续回复',
      timestamp: '2026-05-06T10:01:00Z',
    })

    await expect(pushSyncRecords({
      device_id: 'uni-mobile-a',
      last_sync_version: 2,
      records,
    }, client)).resolves.toMatchObject({ accepted: 1, server_version: 3 })
    await expect(pullSyncRecords({
      sinceVersion: 2,
      entityTypes: ['conversation', 'message'],
      limit: 50,
    }, client)).resolves.toMatchObject({
      records: [{ entity_id: 'msg-desktop-1', device_id: 'desktop-a' }],
      has_more: false,
    })

    expect(calls).toEqual([
      {
        method: 'POST',
        url: '/sync/push',
        data: {
          device_id: 'uni-mobile-a',
          last_sync_version: 2,
          records,
        },
      },
      {
        method: 'GET',
        url: '/sync/pull?since_version=2&limit=50&entity_types=conversation%2Cmessage',
      },
    ])
  })
})
