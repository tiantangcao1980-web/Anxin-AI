import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore, type IMMessage } from '@/lib/store'
import {
  _routeMessage,
  buildAuthPayload,
  getIMLastAckMessageId,
  rememberIMLastAckMessageId,
} from './useIMWebSocket'

function createFakeStorage(): Storage {
  const values = new Map<string, string>()
  return {
    get length() {
      return values.size
    },
    clear: () => values.clear(),
    getItem: (key: string) => values.get(key) ?? null,
    key: (index: number) => Array.from(values.keys())[index] ?? null,
    removeItem: (key: string) => {
      values.delete(key)
    },
    setItem: (key: string, value: string) => {
      values.set(key, value)
    },
  }
}

function makeMessage(id: string): IMMessage {
  return {
    id,
    conversation_id: 'conversation-1',
    sender_id: 'sender-1',
    content: `message ${id}`,
    message_type: 'text',
    is_recalled: false,
    created_at: '2026-05-06T12:00:00Z',
  }
}

function createRouteStore() {
  return {
    addMessage: vi.fn(),
    setTyping: vi.fn(),
    clearTyping: vi.fn(),
    recallMessage: vi.fn(),
    updateReadReceipt: vi.fn(),
    addNotification: vi.fn(),
  }
}

describe('useIMWebSocket offline ACK protocol', () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: createFakeStorage(),
      configurable: true,
    })
    useAuthStore.setState({
      user: { id: 'user-1', email: 'u@example.com', name: 'User', role: 'client' },
      token: null,
      isAuthenticated: true,
    })
  })

  it('stores ACK cursors per user and includes the cursor in the auth packet', () => {
    rememberIMLastAckMessageId('user-1', 'message-9')
    rememberIMLastAckMessageId('user-2', 'message-2')

    expect(getIMLastAckMessageId('user-1')).toBe('message-9')
    expect(getIMLastAckMessageId('user-2')).toBe('message-2')
    expect(buildAuthPayload('token-1')).toEqual({
      token: 'token-1',
      last_ack_message_id: 'message-9',
    })
  })

  it('routes offline messages into the store and ACKs each valid message', () => {
    const store = createRouteStore()
    const sendAck = vi.fn(() => true)
    const first = makeMessage('message-1')
    const second = makeMessage('message-2')

    _routeMessage(
      {
        type: 'offline_messages',
        messages: [first, { id: 'invalid' }, second],
      },
      store,
      sendAck
    )

    expect(store.addMessage).toHaveBeenNthCalledWith(1, first)
    expect(store.addMessage).toHaveBeenNthCalledWith(2, second)
    expect(sendAck).toHaveBeenNthCalledWith(1, 'message-1')
    expect(sendAck).toHaveBeenNthCalledWith(2, 'message-2')
  })

  it('persists the cursor only after the server confirms ACK', () => {
    const store = createRouteStore()

    _routeMessage({ type: 'ack_ok', message_id: 'message-3' }, store)

    expect(getIMLastAckMessageId('user-1')).toBe('message-3')
  })
})
