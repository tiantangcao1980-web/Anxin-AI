import { test, expect, type Page, type TestInfo } from '@playwright/test'
import { installApiMocks, seedAuthState } from './helpers/session'

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
    await installApiMocks(page)
    await seedAuthState(page, {
      role: 'admin',
      userId: 'e2e-user',
      name: 'E2E User',
      email: 'e2e@example.com',
    })
    await installMockWebSocket(page)
    await page.goto('/chat')
    await expect(page.getByText('安心智能助手', { exact: true }).first()).toBeVisible()
    await waitForSocket(page)
  })

  test('agent_task_start 自动切到工作台', async ({ page }) => {
    await emitSocketEvent(page, {
      type: 'agent_task_start',
      task_id: 'task-smart-1',
      agent: '文书起草Agent',
      description: '正在起草法律意见书',
    })

    await expect(page.locator('[data-workbench-shell="chat"]')).toBeVisible()
    await expect(page.locator('[data-workbench-tab="smart"]')).toBeVisible()
    await expect(page.getByText('多智能体协作')).toBeVisible()
    await expect(page.getByRole('button', { name: /文书起草Agent/ })).toBeVisible()
  })

  test('workspace_artifact_created 会进入工作台运行产物', async ({ page }) => {
    await emitSocketEvent(page, {
      type: 'workspace_artifact_created',
      artifact: {
        id: 'runtime-task-e2e',
        artifact_type: 'agent_runtime_summary',
        title: '长任务运行摘要',
        created_at: '2026-05-09T12:00:00.000Z',
        content: {
          summary: '合同风险摘要已生成',
          elapsed_seconds: 3.2,
        },
        metadata: {
          source: 'legal_workforce.process_task_streaming',
          runtime_generated: true,
          status: 'ready_for_review',
        },
      },
    })

    await expect(page.locator('[data-workbench-shell="chat"]')).toBeVisible()
    await expect(page.getByText('运行产物')).toBeVisible()
    await expect(page.getByText('长任务运行摘要')).toBeVisible()
    await expect(page.getByText('合同风险摘要已生成')).toBeVisible()
    await expect(page.getByText('ready_for_review')).toBeVisible()
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
    await expect(page).toHaveURL(/\/documents/)
    await expect(page.getByTestId('document-workbench-shell')).toHaveAttribute('data-entry-mode', 'chat')
    await expect(page.getByText('买卖合同草稿').first()).toBeVisible()
  })

  test('查看完整文档会打开统一文档工作台', async ({ page }) => {
    await emitSocketEvent(page, {
      type: 'canvas_open',
      title: '测试法律意见书',
      content: '# 测试法律意见书',
      type_name: 'document',
    })

    await page.getByRole('button', { name: /^工作台/ }).click()
    await page.getByRole('button', { name: /查看完整文档/ }).click()

    await expect(page).toHaveURL(/\/documents/)
    await expect(page.getByTestId('document-workbench-shell')).toBeVisible()
  })

  test('工作台支持将待确认事项插入到文档正文', async ({ page }) => {
    await emitSocketEvent(page, {
      type: 'canvas_open',
      title: '测试法律意见书',
      content: '# 测试法律意见书',
      type_name: 'document',
      metadata: {
        draft_mode: '高可用草案',
        completeness_score: 0.62,
        validation_score: 0.81,
        missing_fields: [
          {
            key: '合同金额与付款安排',
            label: '合同金额与付款安排',
            severity: 'high',
            group: '交易条件',
            suggestion: '建议补充：明确合同总价、付款节点、付款条件',
          },
        ],
      },
    })

    await page.evaluate(() => {
      window.sessionStorage.setItem(
        'document-workbench-entry',
        JSON.stringify({
          entryMode: 'chat',
          initialDocument: {
            id: 'chat-doc-1',
            title: '测试法律意见书',
            content: '# 测试法律意见书',
            type: 'document',
            metadata: {
              draft_mode: '高可用草案',
              completeness_score: 0.62,
              validation_score: 0.81,
              missing_fields: [
                {
                  key: '合同金额与付款安排',
                  label: '合同金额与付款安排',
                  severity: 'high',
                  group: '交易条件',
                  suggestion: '建议补充：明确合同总价、付款节点、付款条件',
                },
              ],
            },
          },
        }),
      )
    })
    await page.goto('/documents')
    await expect(page.getByTestId('document-workbench-shell')).toBeVisible()
    await page.locator('aside').getByText('AI', { exact: true }).click()
    await expect(page.getByText('待确认事项')).toBeVisible()
    await page.getByRole('button', { name: '插入建议' }).click()
    await expect(page.locator('textarea')).toContainText('建议补充：明确合同总价、付款节点、付款条件')
    await expect(page.getByText('当前文档暂无待确认事项')).toBeVisible()
  })

  test('工作台支持按缺项生成补写段落', async ({ page }) => {
    await page.route('**/api/v1/documents/generate-paragraph', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200,
          message: 'success',
          request_id: 'test-request',
          data: {
            title: 'AI补写段落：法律后果提示',
            content: '若贵方逾期未履行付款义务，我方将依法提起诉讼并主张违约责任。',
          },
        }),
      })
    })

    await emitSocketEvent(page, {
      type: 'canvas_open',
      title: '测试法律意见书',
      content: '# 测试法律意见书',
      type_name: 'document',
      metadata: {
        draft_mode: '高可用草案',
        completeness_score: 0.62,
        validation_score: 0.81,
        missing_fields: [
          {
            key: '法律后果提示',
            label: '法律后果提示',
            severity: 'medium',
            group: '风险控制',
            suggestion: '建议补充：说明逾期不履行将面临的诉讼、仲裁或其他法律后果',
          },
        ],
      },
    })

    await page.evaluate(() => {
      window.sessionStorage.setItem(
        'document-workbench-entry',
        JSON.stringify({
          entryMode: 'chat',
          initialDocument: {
            id: 'chat-doc-2',
            title: '测试法律意见书',
            content: '# 测试法律意见书',
            type: 'document',
            metadata: {
              draft_mode: '高可用草案',
              completeness_score: 0.62,
              validation_score: 0.81,
              missing_fields: [
                {
                  key: '法律后果提示',
                  label: '法律后果提示',
                  severity: 'medium',
                  group: '风险控制',
                  suggestion: '建议补充：说明逾期不履行将面临的诉讼、仲裁或其他法律后果',
                },
              ],
            },
          },
        }),
      )
    })
    await page.goto('/documents')
    await expect(page.getByTestId('document-workbench-shell')).toBeVisible()
    await page.locator('aside').getByText('AI', { exact: true }).click()
    await page.getByRole('button', { name: '生成补写段落' }).click()
    await expect(page.locator('textarea')).toContainText('## AI补写段落：法律后果提示')
    await expect(page.locator('textarea')).toContainText('若贵方逾期未履行付款义务，我方将依法提起诉讼并主张违约责任。')
    await expect(page.getByText('当前文档暂无待确认事项')).toBeVisible()
  })

  test('已处理缺项会进入工作台历史页签', async ({ page }) => {
    await page.route('**/api/v1/documents/generate-paragraph', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200,
          message: 'success',
          request_id: 'test-request',
          data: {
            title: 'AI补写段落：法律后果提示',
            content: '若贵方逾期未履行付款义务，我方将依法提起诉讼并主张违约责任。',
          },
        }),
      })
    })

    await emitSocketEvent(page, {
      type: 'canvas_open',
      title: '测试法律意见书',
      content: '# 测试法律意见书',
      type_name: 'document',
      metadata: {
        draft_mode: '高可用草案',
        completeness_score: 0.62,
        validation_score: 0.81,
        missing_fields: [
          {
            key: '法律后果提示',
            label: '法律后果提示',
            severity: 'medium',
            group: '风险控制',
            suggestion: '建议补充：说明逾期不履行将面临的诉讼、仲裁或其他法律后果',
          },
        ],
      },
    })

    await page.evaluate(() => {
      window.sessionStorage.setItem(
        'document-workbench-entry',
        JSON.stringify({
          entryMode: 'chat',
          initialDocument: {
            id: 'chat-doc-3',
            title: '测试法律意见书',
            content: '# 测试法律意见书',
            type: 'document',
            metadata: {
              draft_mode: '高可用草案',
              completeness_score: 0.62,
              validation_score: 0.81,
              missing_fields: [
                {
                  key: '法律后果提示',
                  label: '法律后果提示',
                  severity: 'medium',
                  group: '风险控制',
                  suggestion: '建议补充：说明逾期不履行将面临的诉讼、仲裁或其他法律后果',
                },
              ],
            },
          },
        }),
      )
    })
    await page.goto('/documents')
    await expect(page.getByTestId('document-workbench-shell')).toBeVisible()
    await page.locator('aside').getByText('AI', { exact: true }).click()
    await page.getByRole('button', { name: '生成补写段落' }).click()
    await page.getByRole('tab', { name: '历史' }).click()

    await expect(page.getByText('已处理待确认事项')).toBeVisible()
    await expect(page.getByText('法律后果提示 · AI补写')).toBeVisible()
  })

  test('点击已处理缺项历史记录可定位到正文段落', async ({ page }) => {
    await page.route('**/api/v1/documents/generate-paragraph', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200,
          message: 'success',
          request_id: 'test-request',
          data: {
            title: 'AI补写段落：法律后果提示',
            content: '若贵方逾期未履行付款义务，我方将依法提起诉讼并主张违约责任。',
          },
        }),
      })
    })

    await emitSocketEvent(page, {
      type: 'canvas_open',
      title: '测试法律意见书',
      content: '# 测试法律意见书',
      type_name: 'document',
      metadata: {
        draft_mode: '高可用草案',
        completeness_score: 0.62,
        validation_score: 0.81,
        missing_fields: [
          {
            key: '法律后果提示',
            label: '法律后果提示',
            severity: 'medium',
            group: '风险控制',
            suggestion: '建议补充：说明逾期不履行将面临的诉讼、仲裁或其他法律后果',
          },
        ],
      },
    })

    await page.evaluate(() => {
      window.sessionStorage.setItem(
        'document-workbench-entry',
        JSON.stringify({
          entryMode: 'chat',
          initialDocument: {
            id: 'chat-doc-4',
            title: '测试法律意见书',
            content: '# 测试法律意见书',
            type: 'document',
            metadata: {
              draft_mode: '高可用草案',
              completeness_score: 0.62,
              validation_score: 0.81,
              missing_fields: [
                {
                  key: '法律后果提示',
                  label: '法律后果提示',
                  severity: 'medium',
                  group: '风险控制',
                  suggestion: '建议补充：说明逾期不履行将面临的诉讼、仲裁或其他法律后果',
                },
              ],
            },
          },
        }),
      )
    })
    await page.goto('/documents')
    await expect(page.getByTestId('document-workbench-shell')).toBeVisible()
    await page.locator('aside').getByText('AI', { exact: true }).click()
    await page.getByRole('button', { name: '生成补写段落' }).click()
    await page.getByRole('tab', { name: '历史' }).click()
    await page.getByRole('button', { name: '法律后果提示 · AI补写' }).click()

    await expect(page.locator('textarea')).toBeFocused()
    await expect
      .poll(() =>
        page.locator('textarea').evaluate((element) => {
          const textarea = element as HTMLTextAreaElement
          return textarea.value.slice(textarea.selectionStart, textarea.selectionEnd)
        }),
      )
      .toContain('## AI补写段落：法律后果提示')
  })

  test('持续收到工作流事件时不应过早显示请求超时', async ({ page }, testInfo) => {
    // 心跳重置逻辑测试：每个事件都应重置 processing timeout，避免过早超时。
    // 并行跑浏览器调度抖动下 50ms 太紧，给 200ms timeout + 80ms gap 保留余量，
    // 仍然 gap (80ms) < timeout (200ms)，逻辑关系不变。
    testInfo.setTimeout(15_000)
    await page.evaluate(() => {
      void ((window as any).__TEST_PROCESSING_TIMEOUT_MS = 200)
    })

    await emitSocketEvent(page, {
      type: 'agent_start',
      agent: '协调调度Agent',
      message: '正在分析您的需求...',
    })
    await page.waitForTimeout(80)
    await emitSocketEvent(page, {
      type: 'agent_working',
      agent: '文书起草Agent',
      message: '正在执行任务...',
    })
    await page.waitForTimeout(80)
    await emitSocketEvent(page, {
      type: 'agent_result',
      agent: '文书起草Agent',
      content: '已生成草稿',
      step: 1,
      total_steps: 1,
    })

    await expect(page.getByText('请求超时，服务器未在规定时间内响应。请稍后重试。')).toHaveCount(0)
  })
})
