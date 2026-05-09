import { expect, test } from '@playwright/test'

import { loginAsAdmin } from './helpers/auth'

test.describe('桌面主工作站设置入口', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    const workstationProbeFixtures = testInfo.title.includes('desktop runtime')
      ? {
          knowledge: {
            bases: {
              items: [
                { id: 'kb-1', name: '制度库', knowledge_type: 'policy', doc_count: 5, is_public: false, created_at: '2026-05-08T00:00:00Z' },
                { id: 'kb-2', name: '合同库', knowledge_type: 'contract', doc_count: 7, is_public: false, created_at: '2026-05-08T00:00:00Z' },
              ],
              total: 2,
              page: 1,
              page_size: 100,
            },
          },
          mcp: {
            servers: [
              { id: 'mcp-1', name: 'files', type: 'stdio', is_enabled: true, cached_tools: [{ name: 'search' }, { name: 'read' }], created_at: '2026-05-08T00:00:00Z' },
              { id: 'mcp-2', name: 'browser', type: 'sse', is_enabled: false, cached_tools: [{ name: 'open' }], created_at: '2026-05-08T00:00:00Z' },
            ],
          },
        }
      : undefined

    await loginAsAdmin(page, workstationProbeFixtures)
  })

  test('direct and legacy links open the workstation tab', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await expect(page.getByRole('tab', { name: '工作站' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('desktop-workstation-panel')).toBeVisible()
    await expect(page.getByText('桌面主工作站')).toBeVisible()
    await expect(page.getByText('非桌面预览')).toBeVisible()

    await page.goto('/settings?tab=privacy')

    await expect(page.getByRole('tab', { name: '工作站' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('desktop-workstation-panel')).toBeVisible()
  })

  test('tab changes write back to the URL', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await page.getByRole('tab', { name: '服务集成' }).click()

    await expect(page).toHaveURL(/\/settings\?tab=mcp$/)
    await expect(page.getByRole('tab', { name: '服务集成' })).toHaveAttribute('aria-selected', 'true')
  })

  test('non-desktop preview keeps desktop-only actions disabled', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await expect(page.getByRole('button', { name: '配置模型' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '同步状态' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '查看任务' })).toBeDisabled()
    await expect(page.getByText('请在桌面客户端启用')).toHaveCount(3)
  })

  test('desktop runtime shows local model and queue probes', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string) => {
          if (cmd === 'get_app_state') {
            return {
              mode: 'hybrid',
              sync_status: 'idle',
              last_sync_time: null,
              backend_url: 'http://localhost:8001',
              is_online: true,
              user_token: 'token-redacted',
              unread_count: 0,
            }
          }
          if (cmd === 'check_local_llm_status') {
            return { available: true, url: 'http://localhost:11434', status: 200 }
          }
          if (cmd === 'list_local_models') {
            return { available: true, models: [{ name: 'qwen2.5:7b' }] }
          }
          if (cmd === 'get_queue_stats') {
            return { queued: 2, local_processing: 0, local_completed: 0, synced: 0, failed: 1, total: 3 }
          }
          if (cmd === 'get_current_mode') {
            return '"hybrid"'
          }
          return null
        },
      }
    })

    await page.goto('/settings?tab=workstation')

    await expect(page.getByText('桌面在线')).toBeVisible()
    await expect(page.getByTestId('workstation-probe-local-model')).toContainText('可用')
    await expect(page.getByTestId('workstation-probe-local-model')).toContainText('1 个模型')
    await expect(page.getByTestId('workstation-probe-knowledge')).toContainText('2 个库')
    await expect(page.getByTestId('workstation-probe-knowledge')).toContainText('12 份文档')
    await expect(page.getByTestId('workstation-probe-mcp')).toContainText('2 个服务')
    await expect(page.getByTestId('workstation-probe-mcp')).toContainText('1 个启用')
    await expect(page.getByTestId('workstation-probe-mcp')).toContainText('3 个工具缓存')
    await expect(page.getByTestId('workstation-probe-offline-queue')).toContainText('3 条')
    await expect(page.getByTestId('workstation-probe-offline-queue')).toContainText('1 条失败需处理')
    await expect(page.getByTestId('workstation-probe-remote-control')).toContainText('待验收')
  })

  test('desktop runtime can update local mode and backend endpoint', async ({ page }) => {
    await page.addInitScript(() => {
      const appState = {
        mode: 'hybrid',
        sync_status: 'idle',
        last_sync_time: null,
        backend_url: 'http://localhost:8001',
        is_online: true,
        user_token: 'token-redacted',
        unread_count: 0,
      }
      const profiles: Array<{ id: string; name: string; mode: string; backend_url: string }> = []
      ;(window as any).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string, args?: Record<string, unknown>) => {
          if (cmd === 'get_app_state') return { ...appState }
          if (cmd === 'get_current_mode') return `"${appState.mode}"`
          if (cmd === 'switch_mode') {
            appState.mode = args?.mode as string
            appState.sync_status = appState.mode === 'top-secret' ? 'offline' : 'idle'
            return { success: true, message: `已切换至${appState.mode}` }
          }
          if (cmd === 'set_backend_url') {
            appState.backend_url = args?.url as string
            return null
          }
          if (cmd === 'list_workstation_profiles') return [...profiles]
          if (cmd === 'create_workstation_profile') {
            const profile = {
              id: 'profile-1',
              name: args?.name as string,
              mode: args?.mode as string,
              backend_url: args?.backendUrl as string,
            }
            profiles.push(profile)
            return profile
          }
          if (cmd === 'update_workstation_profile') {
            const index = profiles.findIndex((profile) => profile.id === args?.id)
            const profile = {
              id: args?.id as string,
              name: args?.name as string,
              mode: args?.mode as string,
              backend_url: args?.backendUrl as string,
            }
            profiles[index] = profile
            return profile
          }
          if (cmd === 'apply_workstation_profile') {
            const profile = profiles.find((item) => item.id === args?.id)
            if (!profile) return { success: false, message: 'missing profile' }
            appState.mode = profile.mode
            appState.backend_url = profile.backend_url
            appState.sync_status = profile.mode === 'top-secret' ? 'offline' : 'idle'
            return { success: true, message: '工作站配置档已应用', profile }
          }
          if (cmd === 'delete_workstation_profile') {
            const index = profiles.findIndex((profile) => profile.id === args?.id)
            profiles.splice(index, 1)
            return null
          }
          if (cmd === 'check_local_llm_status') return { available: true, url: 'http://localhost:11434', status: 200 }
          if (cmd === 'list_local_models') return { available: true, models: [{ name: 'qwen2.5:7b' }] }
          if (cmd === 'get_queue_stats') return { queued: 0, local_processing: 0, local_completed: 0, synced: 0, failed: 0, total: 0 }
          return null
        },
      }
    })

    await page.goto('/settings?tab=workstation')

    await expect(page.getByTestId('desktop-workstation-config')).toBeVisible()
    await expect(page.getByTestId('workstation-backend-current')).toContainText('http://localhost:8001')

    await page.getByTestId('workstation-mode-top-secret').click()

    await expect(page.getByTestId('workstation-mode-top-secret')).toBeDisabled()
    await expect(page.getByTestId('workstation-probe-remote-control')).toContainText('已阻断')

    await page.getByTestId('workstation-backend-url').fill('https://staging.anxin.example/')
    await page.getByTestId('workstation-backend-save').click()

    await expect(page.getByTestId('workstation-backend-current')).toContainText('https://staging.anxin.example')

    await page.getByTestId('workstation-profile-name').fill('预发环境')
    await page.getByTestId('workstation-profile-backend-url').fill('https://staging.anxin.example')
    await page.getByTestId('workstation-profile-save').click()

    await expect(page.getByTestId('workstation-profile-profile-1')).toContainText('预发环境')
    await expect(page.getByTestId('workstation-profile-profile-1')).toContainText('混合')
    await expect(page.getByTestId('workstation-profile-profile-1')).toContainText('https://staging.anxin.example')

    await page.getByTestId('workstation-profile-edit-profile-1').click()
    await page.getByTestId('workstation-profile-mode-cloud').click()
    await page.getByTestId('workstation-profile-backend-url').fill('https://api.anxin.example')
    await page.getByTestId('workstation-profile-save').click()

    await expect(page.getByTestId('workstation-profile-profile-1')).toContainText('云端')
    await expect(page.getByTestId('workstation-profile-profile-1')).toContainText('https://api.anxin.example')

    await page.getByTestId('workstation-profile-apply-profile-1').click()

    await expect(page.getByTestId('workstation-mode-cloud')).toBeDisabled()
    await expect(page.getByTestId('workstation-backend-current')).toContainText('https://api.anxin.example')

    await page.getByTestId('workstation-profile-delete-profile-1').click()

    await expect(page.getByText('尚未保存配置档')).toBeVisible()
  })
})

test.describe('桌面主工作站移动宽度', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile', 'mobile viewport coverage only')
    await loginAsAdmin(page)
  })

  test('resource cards stay within the mobile viewport', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await expect(page.getByTestId('desktop-workstation-panel')).toBeVisible()
    await expect(page.getByText('非桌面预览')).toBeVisible()

    const cardBoxes = await page
      .locator('[data-testid^="desktop-workstation-resource-"]')
      .evaluateAll((nodes) =>
        nodes.map((node) => {
          const rect = node.getBoundingClientRect()
          return {
            left: rect.left,
            right: rect.right,
            width: rect.width,
            viewport: window.innerWidth,
          }
        }),
      )

    expect(cardBoxes).toHaveLength(6)
    for (const box of cardBoxes) {
      expect(box.left).toBeGreaterThanOrEqual(0)
      expect(box.right).toBeLessThanOrEqual(box.viewport + 1)
      expect(box.width).toBeGreaterThan(280)
    }
  })
})
