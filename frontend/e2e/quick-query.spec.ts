import { expect, test } from '@playwright/test'

test.describe('桌面快问窗口', () => {
  test('uses local LLM in desktop local modes and exposes a hide command', async ({ page }) => {
    await page.addInitScript(() => {
      const win = window as any
      win.__quickQueryInvocations = []
      win.__TAURI_INTERNALS__ = {
        invoke: async (cmd: string, args?: Record<string, unknown>) => {
          win.__quickQueryInvocations.push({ cmd, args })
          if (cmd === 'secure_sql_execute') return { rowsAffected: 0 }
          if (cmd === 'secure_sql_select') return []
          if (cmd === 'get_app_state') {
            return {
              mode: 'top-secret',
              sync_status: 'offline',
              last_sync_time: null,
              backend_url: 'http://localhost:8001',
              is_online: false,
              user_token: null,
              unread_count: 0,
            }
          }
          if (cmd === 'get_current_mode') return '"top-secret"'
          if (cmd === 'local_llm_chat') {
            return {
              success: true,
              source: 'local',
              model: 'qwen2.5:7b',
              message: '先核验解除条款、通知期限和违约责任。',
            }
          }
          if (cmd === 'hide_quick_query_window') return null
          return null
        },
      }
    })

    await page.goto('/desktop/quick-query')

    await expect(page.getByRole('heading', { name: '安心快问' })).toBeVisible()
    await page.getByPlaceholder('输入需要快速确认的问题').fill('合同解除有什么风险？')
    await page.keyboard.press('Enter')

    await expect(page.getByText('合同解除有什么风险？')).toBeVisible()
    await expect(page.getByText('先核验解除条款、通知期限和违约责任。')).toBeVisible()
    await expect(page.getByText('local · qwen2.5:7b')).toBeVisible()

    const invokedCommands = await page.evaluate(() =>
      (window as any).__quickQueryInvocations.map((entry: { cmd: string }) => entry.cmd),
    )
    expect(invokedCommands).toContain('get_current_mode')
    expect(invokedCommands).toContain('local_llm_chat')

    await page.getByRole('button', { name: '关闭快问' }).click()
    await expect
      .poll(() =>
        page.evaluate(() =>
          (window as any).__quickQueryInvocations.filter(
            (entry: { cmd: string }) => entry.cmd === 'hide_quick_query_window',
          ).length,
        ),
      )
      .toBeGreaterThan(0)
  })
})
