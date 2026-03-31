import { test, expect, type Page, type TestInfo } from '@playwright/test'

async function installMockWebSocket(page: Page) {
  await page.addInitScript(() => {
    const encodeBase64Url = (value: string) =>
      btoa(value).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')

    const header = encodeBase64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    const payload = encodeBase64Url(
      JSON.stringify({
        sub: 'e2e-user',
        exp: Math.floor(Date.now() / 1000) + 60 * 60,
        role: 'admin',
      }),
    )
    const token = `${header}.${payload}.signature`

    localStorage.setItem('access_token', token)
    localStorage.setItem('refresh_token', 'e2e-refresh-token')
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          user: {
            id: 'e2e-user',
            email: 'e2e@example.com',
            name: 'E2E User',
            role: 'admin',
          },
          token,
          isAuthenticated: true,
        },
        version: 0,
      }),
    )
    localStorage.setItem(
      'user_info',
      JSON.stringify({
        id: 'e2e-user',
        email: 'e2e@example.com',
        name: 'E2E User',
        role: 'admin',
      }),
    )

    const sockets: any[] = []

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
      sent: string[] = []

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

      send(data: string) {
        this.sent.push(data)
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

    const globalWindow = window as any
    globalWindow.__mockSockets = sockets
    globalWindow.WebSocket = MockWebSocket
  })
}

async function waitForSocket(page: Page) {
  await page.waitForFunction(() => Array.isArray((window as any).__mockSockets) && (window as any).__mockSockets.length > 0)
}

async function emitSocketEvent(page: Page, payload: Record<string, unknown>) {
  await page.evaluate((eventPayload) => {
    const sockets = ((window as any).__mockSockets || []) as Array<{ url?: string; emitMessage: (payload: unknown) => void }>
    const targets = sockets.filter((socket) => socket.url?.includes('/chat/ws/'))

    if (targets.length === 0) {
      throw new Error('mock websocket not initialized')
    }

    targets.forEach((socket) => socket.emitMessage(eventPayload))
  }, payload)
}

test.describe('右侧面板双模式', () => {
  test.beforeEach(async ({ page }, testInfo: TestInfo) => {
    test.skip(testInfo.project.name === 'mobile', 'desktop only')
    await installMockWebSocket(page)
    await page.goto('/chat')
    await expect(page.getByText('AI 法务助手', { exact: true }).first()).toBeVisible()
    await waitForSocket(page)
  })

  test('agent_task_start 自动切到工作台', async ({ page }) => {
    await emitSocketEvent(page, {
      type: 'agent_task_start',
      task_id: 'task-smart-1',
      agent: '文书起草Agent',
      description: '正在起草法律意见书',
    })

    await expect(page.getByText('多智能体协作')).toBeVisible()
    await expect(page.getByRole('button', { name: /文书起草Agent/ })).toBeVisible()
  })

  test('canvas_open 自动切到文档模式', async ({ page }) => {
    await emitSocketEvent(page, {
      type: 'canvas_open',
      title: '测试法律意见书',
      content: '# 测试法律意见书\n\n第一条 合同目的\n\n第二条 争议解决',
      type_name: 'document',
    })

    await expect(page.locator('input[value="测试法律意见书"]')).toBeVisible()
    await expect(page.getByText('已保存')).toBeVisible()
  })

  test('工作台里的查看完整文档按钮可切回文档', async ({ page }) => {
    await emitSocketEvent(page, {
      type: 'agent_task_start',
      task_id: 'task-smart-2',
      agent: '文书起草Agent',
      description: '正在整理合同条款',
    })

    await emitSocketEvent(page, {
      type: 'agent_result',
      agent: '文书起草Agent',
      content: '已生成合同草稿',
      step: 1,
      total_steps: 1,
    })

    await emitSocketEvent(page, {
      type: 'canvas_open',
      title: '买卖合同草稿',
      content: '# 买卖合同\n\n甲方：测试公司\n\n乙方：示例公司',
      type_name: 'contract',
    })

    await expect(page.locator('input[value="买卖合同草稿"]')).toBeVisible()

    await page.getByRole('button', { name: /^工作台/ }).click()
    await expect(page.getByRole('button', { name: /查看完整文档/ })).toBeVisible()

    await page.getByRole('button', { name: /查看完整文档/ }).click()
    await expect(page.locator('input[value="买卖合同草稿"]')).toBeVisible()
  })
})
