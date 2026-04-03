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

    if (pathname.includes('/notifications')) {
      return fulfillJson(route, buildUnified({ data: [], total: 0 }))
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

        queueMicrotask(() => {
          this.readyState = MockWebSocket.OPEN
          const event = new Event('open')
          this.onopen?.(event)
          this.dispatchEvent(event)
        })
      }

      send() {}

      close(code = 1000, reason = 'mock close') {
        this.readyState = MockWebSocket.CLOSED
        const event = new CloseEvent('close', { code, reason, wasClean: true })
        this.onclose?.(event)
        this.dispatchEvent(event)
      }
    }

    (window as unknown as { WebSocket: typeof WebSocket }).WebSocket =
      MockWebSocket as unknown as typeof WebSocket
  }, seed)
}
