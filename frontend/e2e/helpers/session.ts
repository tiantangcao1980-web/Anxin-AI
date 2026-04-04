import type { Page, Route } from '@playwright/test'

type AuthSeed = {
  role: string
  userId?: string
  name?: string
  email?: string
  expired?: boolean
}

type MockOptions = {
  contracts?: {
    list?: unknown
    create?: unknown
    review?: unknown
  }
  documents?: {
    list?: unknown
    analyze?: unknown
  }
  tasks?: {
    list?: unknown
    transition?: unknown
  }
  lawyer?: {
    consultation?: unknown
    lawyers?: unknown
    delegation?: unknown
  }
}

function createMockToken(role: string, userId = 'e2e-user', expired = false) {
  const encodeBase64Url = (value: string) =>
    Buffer.from(value, 'utf8').toString('base64url')

  const header = encodeBase64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = encodeBase64Url(
    JSON.stringify({
      sub: userId,
      role,
      exp: expired
        ? Math.floor(Date.now() / 1000) - 60
        : Math.floor(Date.now() / 1000) + 60 * 60,
    }),
  )

  return `${header}.${payload}.signature`
}

function buildUnified(data: unknown) {
  return {
    code: 0,
    data,
    message: 'ok',
    request_id: 'e2e-request',
  }
}

async function fulfillJson(route: Route, data: unknown) {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(data),
  })
}

export async function installApiMocks(page: Page, options: MockOptions = {}) {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())

    if (pathname.endsWith('/auth/login') && request.method() === 'POST') {
      const accessToken = createMockToken('admin', 'e2e-admin')
      return fulfillJson(
        route,
        buildUnified({
          access_token: accessToken,
          refresh_token: 'e2e-refresh-token',
          token_type: 'bearer',
          user: {
            id: 'e2e-admin',
            email: 'admin@anxinfawu.com',
            name: 'E2E Admin',
            role: 'admin',
          },
        }),
      )
    }

    if (pathname.endsWith('/auth/me') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified({
          id: 'e2e-admin',
          email: 'admin@anxinfawu.com',
          name: 'E2E Admin',
          role: 'admin',
        }),
      )
    }

    if (pathname.includes('/notifications')) {
      return fulfillJson(route, buildUnified({ data: [], total: 0 }))
    }

    if (pathname.endsWith('/chat/history') && request.method() === 'GET') {
      return fulfillJson(route, buildUnified({ conversations: [], messages: [] }))
    }

    if (pathname.includes('/chat/conversations/') && pathname.endsWith('/canvas')) {
      return fulfillJson(route, buildUnified(null))
    }

    if (pathname.includes('/harness/stats')) {
      return fulfillJson(route, {
        status: 'ok',
        data: {
          cost: { total_tokens: 1024, total_cost_usd: 0.12, by_model: {}, by_agent: {} },
          tools: { total: 8, enabled: 8 },
          policy: { total_checks: 12, deny_count: 1 },
          tasks: { total: 5, success: 5, failed: 0 },
        },
      })
    }

    if (pathname.includes('/harness/tools')) {
      return fulfillJson(route, {
        status: 'ok',
        data: [
          { name: 'search_knowledge' },
          { name: 'draft_contract' },
          { name: 'risk_assessment' },
        ],
      })
    }

    if (pathname.includes('/harness/policy/check')) {
      return fulfillJson(route, {
        status: 'ok',
        data: { decision: 'deny' },
      })
    }

    if (pathname.endsWith('/contracts/') || pathname.endsWith('/contracts')) {
      if (request.method() === 'GET') {
        return fulfillJson(
          route,
          buildUnified(
            options.contracts?.list ?? { items: [], total: 0, page: 1, page_size: 20 },
          ),
        )
      }

      if (request.method() === 'POST') {
        return fulfillJson(
          route,
          buildUnified(
            options.contracts?.create ?? {
              id: 'contract-e2e',
              title: '待审查合同',
              contract_type: 'other',
              status: 'draft',
              created_at: '2026-04-03T00:00:00Z',
              updated_at: '2026-04-03T00:00:00Z',
            },
          ),
        )
      }
    }

    if (/\/contracts\/[^/]+\/review$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.contracts?.review ?? {
            contract_id: 'contract-e2e',
            risk_level: 'medium',
            risk_score: 0.42,
            summary: '已完成合同审查',
            risks: [],
            suggestions: [],
            key_terms: {},
          },
        ),
      )
    }

    if (pathname.endsWith('/documents/') || pathname.endsWith('/documents')) {
      return fulfillJson(
        route,
        buildUnified(
          options.documents?.list ?? { items: [], total: 0, page: 1, page_size: 20 },
        ),
      )
    }

    if (/\/documents\/[^/]+\/analyze$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.documents?.analyze ?? {
            document_id: 'document-e2e',
            summary: '已完成文档分析',
            key_points: [],
            entities: [],
            dates: [],
            amounts: [],
            risks: [],
          },
        ),
      )
    }

    if (pathname.includes('/cases/')) {
      return fulfillJson(
        route,
        buildUnified({ items: [], total: 0, page: 1, page_size: 20 }),
      )
    }

    if (pathname.endsWith('/tasks/') || pathname.endsWith('/tasks')) {
      return fulfillJson(
        route,
        buildUnified(options.tasks?.list ?? { items: [], total: 0 }),
      )
    }

    if (/\/tasks\/[^/]+\/transition$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.tasks?.transition ?? {
            id: 'task-e2e',
            status: 'in_progress',
          },
        ),
      )
    }

    if (pathname.includes('/leads/')) {
      return fulfillJson(route, buildUnified({ items: [], total: 0 }))
    }

    if (pathname.endsWith('/lawyer/consultations') && request.method() === 'POST') {
      return fulfillJson(
        route,
        buildUnified(
          options.lawyer?.consultation ?? {
            consultation_id: 'consultation-e2e',
            anonymous_summary: '劳动争议匿名摘要',
          },
        ),
      )
    }

    if (pathname.endsWith('/lawyer/lawyers') && request.method() === 'GET') {
      return fulfillJson(
        route,
        buildUnified(
          options.lawyer?.lawyers ?? {
            items: [],
            total: 0,
          },
        ),
      )
    }

    if (/\/lawyer\/consultations\/[^/]+\/delegate$/.test(pathname)) {
      return fulfillJson(
        route,
        buildUnified(
          options.lawyer?.delegation ?? {
            id: 'delegation-e2e',
            status: 'submitted',
          },
        ),
      )
    }

    if (pathname.includes('/auth/features')) {
      return fulfillJson(
        route,
        buildUnified({
          email_verify_enabled: false,
          sms_enabled: false,
          oauth_wechat_enabled: false,
          oauth_alipay_enabled: false,
        }),
      )
    }

    return fulfillJson(route, buildUnified({}))
  })
}

export async function seedAuthState(page: Page, seed: AuthSeed) {
  await page.addInitScript((input: AuthSeed) => {
    const encodeBase64Url = (value: string) =>
      btoa(value).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')

    const header = encodeBase64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    const payload = encodeBase64Url(
      JSON.stringify({
        sub: input.userId ?? 'e2e-user',
        role: input.role,
        exp: input.expired
          ? Math.floor(Date.now() / 1000) - 60
          : Math.floor(Date.now() / 1000) + 60 * 60,
      }),
    )
    const token = `${header}.${payload}.signature`
    const user = {
      id: input.userId ?? 'e2e-user',
      email: input.email ?? `${input.role}@example.com`,
      name: input.name ?? 'E2E User',
      role: input.role,
    }

    localStorage.setItem('access_token', token)
    localStorage.setItem('refresh_token', 'e2e-refresh-token')
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          user,
          token,
          isAuthenticated: true,
        },
        version: 0,
      }),
    )
    localStorage.setItem('user_info', JSON.stringify(user))

    const sockets: Array<{ url: string; emitMessage: (payload: unknown) => void }> = []

    const emitChatPayload = (socket: MockWebSocket, payload: unknown, delay = 50) => {
      window.setTimeout(() => socket.emitMessage(payload), delay)
    }

    class MockWebSocket extends EventTarget {
      static CONNECTING = 0
      static OPEN = 1
      static CLOSING = 2
      static CLOSED = 3

      url: string
      readyState = MockWebSocket.CONNECTING
      onopen: ((event: Event) => void) | null = null
      onmessage: ((event: MessageEvent) => void) | null = null
      onerror: ((event: Event) => void) | null = null
      onclose: ((event: CloseEvent) => void) | null = null

      constructor(url: string) {
        super()
        this.url = url
        sockets.push(this)

        queueMicrotask(() => {
          this.readyState = MockWebSocket.OPEN
          const event = new Event('open')
          this.onopen?.(event)
          this.dispatchEvent(event)
        })
      }

      send(data?: string) {
        if (!data || !this.url.includes('/chat/ws/')) return

        try {
          const parsed = JSON.parse(data) as {
            content?: string
            type?: string
            original_content?: string
          }

          if (parsed.type === 'clarification_response') {
            emitChatPayload(this, {
              type: 'done',
              content: '已收到补充信息，我将根据您的要求继续生成法律文书。',
              agent: '需求分析Agent',
            })
            return
          }

          const content = parsed.content ?? ''

          if (content.includes('帮我起草一份合同')) {
            emitChatPayload(this, {
              type: 'clarification_request',
              message: '请补充合同类型和交易背景，以便我为您准确起草。',
              original_content: content,
              questions: [
                {
                  question: '请选择合同类型',
                  options: ['买卖合同', '租赁合同', '服务合同'],
                },
              ],
            })
            return
          }

          if (content.includes('劳动法规定试用期最长多久')) {
            emitChatPayload(this, {
              type: 'done',
              content: '根据《劳动合同法》，试用期最长不得超过六个月，具体取决于劳动合同期限。',
              agent: '法律咨询Agent',
            })
            return
          }

          if (content.includes('租赁合同模板')) {
            emitChatPayload(this, {
              type: 'done',
              content: '您可以前往法律智库浏览并下载租赁合同模板，也可以告诉我具体场景后为您定制。',
              agent: '模板助手',
            })
            return
          }

          if (content.trim() === '你好') {
            emitChatPayload(this, {
              type: 'done',
              content: '您好！很高兴为您服务，请告诉我您需要处理的法律问题。',
              agent: 'AI 法务助手',
            })
            return
          }

          emitChatPayload(this, {
            type: 'done',
            content: '已收到您的问题，正在为您整理专业意见。',
            agent: 'AI 法务助手',
          })
        } catch {
          // Ignore malformed mock payloads to keep tests deterministic.
        }
      }

      close(code = 1000, reason = 'mock close') {
        this.readyState = MockWebSocket.CLOSED
        const event = new CloseEvent('close', { code, reason, wasClean: true })
        this.onclose?.(event)
        this.dispatchEvent(event)
      }

      emitMessage(payload: unknown) {
        const event = new MessageEvent('message', {
          data: JSON.stringify(payload),
        })
        this.onmessage?.(event)
        this.dispatchEvent(event)
      }
    }

    const globalWindow = window as unknown as {
      WebSocket: typeof WebSocket
      __mockSockets?: Array<{ url: string; emitMessage: (payload: unknown) => void }>
    }
    globalWindow.__mockSockets = sockets
    globalWindow.WebSocket = MockWebSocket as unknown as typeof WebSocket
  }, seed)
}
