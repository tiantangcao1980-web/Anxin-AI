import { expect, test } from '@playwright/test'

import { loginAsAdmin } from './helpers/auth'

test.describe('桌面工作站设置入口', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    const pendingRemoteControl = testInfo.title.includes('remote-control host pending')
    const readyRemoteControl = testInfo.title.includes('remote-control host safe-probe')
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
          remoteControl: pendingRemoteControl
            ? {
                status: {
                  available: false,
                  status: 'pending_desktop_confirmation',
                  desktop_device_id: 'desktop-e2e-01',
                  pairing_id: 'pairing-e2e-pending',
                  queued_command_count: 0,
                  required_controls: ['device_pairing', 'desktop_confirmation', 'audit_log'],
                  message: '已有配对请求等待桌面端确认；确认前不会接受远控命令。',
                },
                auditEvents: {
                  items: [
                    {
                      id: 'audit-pairing-request',
                      pairing_id: 'pairing-e2e-pending',
                      action: 'remote_control.pairing.request',
                      status: 'success',
                      reason_code: 'pending_desktop_confirmation',
                      created_at: '2026-05-09T10:00:00Z',
                    },
                  ],
                  total: 1,
                },
              }
            : readyRemoteControl
              ? {
                  status: {
                    available: true,
                    status: 'queue_ready_execution_pending',
                    desktop_device_id: 'desktop-e2e-01',
                    pairing_id: 'pairing-e2e-ready',
                    queued_command_count: 1,
                    required_controls: ['capability_route_token', 'command_expiry_and_revocation', 'audit_log'],
                    message: '远控控制面已具备已确认配对和命令队列；仍需桌面 host 拉取。',
                  },
                  auditEvents: {
                    items: [
                      {
                        id: 'audit-command-claim',
                        pairing_id: 'pairing-e2e-ready',
                        command_id: 'command-e2e',
                        action: 'remote_control.command.claim',
                        status: 'success',
                        reason_code: 'claimed',
                        created_at: '2026-05-09T10:03:00Z',
                      },
                      {
                        id: 'audit-command-enqueue',
                        pairing_id: 'pairing-e2e-ready',
                        command_id: 'command-e2e',
                        action: 'remote_control.command.enqueue',
                        status: 'success',
                        reason_code: 'queued',
                        created_at: '2026-05-09T10:02:00Z',
                      },
                    ],
                    total: 2,
                  },
                }
              : undefined,
        }
      : undefined

    await loginAsAdmin(page, workstationProbeFixtures)
  })

  test('direct and legacy links open the workstation tab', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await expect(page.getByRole('tab', { name: '桌面工作站' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('desktop-workstation-panel')).toBeVisible()
    await expect(page.getByText('我的桌面工作站')).toBeVisible()
    await expect(page.getByText('非桌面预览')).toBeVisible()

    await page.goto('/settings?tab=privacy')

    await expect(page.getByRole('tab', { name: '桌面工作站' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('desktop-workstation-panel')).toBeVisible()
  })

  test('tab changes write back to the URL', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await page.getByRole('tab', { name: '工具连接' }).click()

    await expect(page).toHaveURL(/\/settings\?tab=mcp$/)
    await expect(page.getByRole('tab', { name: '工具连接' })).toHaveAttribute('aria-selected', 'true')
  })

  test('non-desktop preview keeps desktop-only actions disabled', async ({ page }) => {
    await page.goto('/settings?tab=workstation')

    await expect(page.getByRole('button', { name: '配置模型' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '同步状态' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '查看任务' })).toBeDisabled()
    await expect(page.locator('[data-testid^="desktop-workstation-resource-"]').getByText('请在桌面客户端启用')).toHaveCount(4)
    await expect(page.getByTestId('native-notification-permission-action')).toBeDisabled()
    await expect(page.getByTestId('native-notification-test')).toBeDisabled()
    await expect(page.getByTestId('remote-control-host-refresh')).toBeDisabled()
    await expect(page.getByTestId('remote-control-host-confirm')).toBeDisabled()
    await expect(page.getByTestId('remote-control-host-cycle')).toBeDisabled()
    await expect(page.getByTestId('remote-control-host-cancel-command')).toBeDisabled()
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
          if (cmd === 'get_desktop_notification_permission') {
            return {
              state: 'granted',
              granted: true,
              canRequest: false,
              localOnly: true,
              safeInTopSecret: true,
              requiresExternalPush: false,
              privacyMode: 'hybrid',
              message: '权限状态: 已授权',
            }
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
    await expect(page.getByTestId('workstation-probe-native-notification')).toContainText('可测试')
    await expect(page.getByTestId('native-notification-permission')).toContainText('已授权')
    await expect(page.getByTestId('native-notification-permission-action')).toBeEnabled()
    await expect(page.getByTestId('native-notification-test')).toBeEnabled()
    await expect(page.getByTestId('workstation-probe-remote-control')).toContainText('待验收')
  })

  test('desktop runtime remote-control host pending pairing can be confirmed', async ({ page }) => {
    await page.addInitScript(() => {
      const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = []
      ;(window as any).__remoteControlInvokes = calls
      ;(window as any).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string, args?: Record<string, unknown>) => {
          calls.push({ cmd, args })
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
          if (cmd === 'remote_control_confirm_pairing') {
            return {
              pairing_id: args?.pairingId,
              desktop_device_id: args?.desktopDeviceId,
              status: 'confirmed',
              confirmed_at: '2026-05-09T10:04:00Z',
            }
          }
          if (cmd === 'check_local_llm_status') return { available: true, url: 'http://localhost:11434', status: 200 }
          if (cmd === 'list_local_models') return { available: true, models: [{ name: 'qwen2.5:7b' }] }
          if (cmd === 'get_queue_stats') return { queued: 0, local_processing: 0, local_completed: 0, synced: 0, failed: 0, total: 0 }
          if (cmd === 'list_workstation_profiles') return []
          if (cmd === 'get_current_mode') return '"hybrid"'
          return null
        },
      }
    })

    await page.goto('/settings?tab=workstation')

    await expect(page.getByTestId('desktop-remote-control-host')).toContainText('待桌面确认')
    await expect(page.getByTestId('remote-control-host-pairing')).toContainText('pairin')
    await expect(page.getByTestId('remote-control-host-scope')).toContainText('设备配对')
    await expect(page.getByTestId('remote-control-host-confirm')).toBeEnabled()
    await expect(page.getByTestId('remote-control-host-cycle')).toBeDisabled()
    await expect(page.getByTestId('remote-control-host-audit-timeline')).toContainText('配对申请')

    await page.getByTestId('remote-control-host-confirm').click()

    await expect.poll(async () => page.evaluate(() => {
      const calls = (window as any).__remoteControlInvokes as Array<{ cmd: string; args?: Record<string, unknown> }>
      return calls.some((item) => item.cmd === 'remote_control_confirm_pairing' && item.args?.pairingId === 'pairing-e2e-pending')
    })).toBe(true)
  })

  test('desktop runtime remote-control host safe-probe and cancel controls stay governed', async ({ page }) => {
    await page.addInitScript(() => {
      const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = []
      ;(window as any).__remoteControlInvokes = calls
      ;(window as any).__TAURI_INTERNALS__ = {
        invoke: async (cmd: string, args?: Record<string, unknown>) => {
          calls.push({ cmd, args })
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
          if (cmd === 'remote_control_run_host_cycle') {
            return {
              claimed: 1,
              completed: 1,
              failed: 0,
              unsupported: 0,
              command_ids: ['command-e2e'],
            }
          }
          if (cmd === 'check_local_llm_status') return { available: true, url: 'http://localhost:11434', status: 200 }
          if (cmd === 'list_local_models') return { available: true, models: [{ name: 'qwen2.5:7b' }] }
          if (cmd === 'get_queue_stats') return { queued: 0, local_processing: 0, local_completed: 0, synced: 0, failed: 0, total: 0 }
          if (cmd === 'list_workstation_profiles') return []
          if (cmd === 'get_current_mode') return '"hybrid"'
          return null
        },
      }
    })

    await page.goto('/settings?tab=workstation')

    await expect(page.getByTestId('desktop-remote-control-host')).toContainText('可安全探针')
    await expect(page.getByTestId('remote-control-host-execution')).toContainText('1 条命令')
    await expect(page.getByTestId('remote-control-host-audit-timeline')).toContainText('桌面领取命令')
    await expect(page.getByTestId('remote-control-host-cycle')).toBeEnabled()
    await expect(page.getByTestId('remote-control-host-cancel-command')).toBeEnabled()
    await expect(page.getByTestId('desktop-remote-control-host')).not.toContainText('e2e-route-token')

    await page.getByTestId('remote-control-host-cycle').click()

    await expect(page.getByTestId('remote-control-host-execution')).toContainText('领取 1')
    await expect.poll(async () => page.evaluate(() => {
      const calls = (window as any).__remoteControlInvokes as Array<{ cmd: string; args?: Record<string, unknown> }>
      return calls.some((item) => item.cmd === 'remote_control_run_host_cycle' && item.args?.routeToken === 'e2e-route-token')
    })).toBe(true)

    await page.getByTestId('remote-control-host-cancel-command').click()

    await expect(page.getByTestId('remote-control-host-cancel-command')).toBeEnabled()
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
      let localModelDefault = 'qwen2.5:7b'
      let nativePermission = 'prompt'
      const profiles: Array<{ id: string; name: string; mode: string; backend_url: string }> = []
      const notifications: Array<Record<string, unknown> | undefined> = []
      const buildNativePermission = (requested = false) => ({
        state: nativePermission,
        granted: nativePermission === 'granted',
        canRequest: nativePermission === 'prompt',
        localOnly: true,
        safeInTopSecret: true,
        requiresExternalPush: false,
        privacyMode: appState.mode,
        message: `${requested ? '授权请求' : '权限状态'}: ${nativePermission === 'granted' ? '已授权' : '待授权'}`,
      })
      ;(window as any).__nativeNotificationInvokes = notifications
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
          if (cmd === 'get_local_llm_config') {
            return {
              default_model: localModelDefault,
              endpoint_url: 'http://localhost:11434',
              stores_secrets: false,
            }
          }
          if (cmd === 'set_default_local_model') {
            localModelDefault = args?.model as string
            return { success: true, default_model: localModelDefault, message: '本地默认模型已更新' }
          }
          if (cmd === 'get_desktop_notification_permission') {
            return buildNativePermission(false)
          }
          if (cmd === 'request_desktop_notification_permission') {
            nativePermission = 'granted'
            return buildNativePermission(true)
          }
          if (cmd === 'send_desktop_notification') {
            notifications.push(args?.payload as Record<string, unknown>)
            return {
              success: true,
              kind: (args?.payload as Record<string, unknown>)?.kind,
              title: (args?.payload as Record<string, unknown>)?.title,
              body: (args?.payload as Record<string, unknown>)?.body,
              relatedId: (args?.payload as Record<string, unknown>)?.relatedId,
              localOnly: true,
              safeInTopSecret: true,
              privacyMode: appState.mode,
              message: '案件进展本机通知已发送',
            }
          }
          if (cmd === 'list_local_models') return {
            available: true,
            models: [
              { name: 'qwen2.5:7b', size: 4_500_000_000, modified_at: '2026-05-09T10:00:00Z' },
              { name: 'llama3.1:8b', size: 8_100_000_000 },
            ],
          }
          if (cmd === 'get_queue_stats') return { queued: 0, local_processing: 0, local_completed: 0, synced: 0, failed: 0, total: 0 }
          return null
        },
      }
    })

    await page.goto('/settings?tab=workstation')

    await expect(page.getByTestId('desktop-workstation-config')).toBeVisible()
    await expect(page.getByTestId('workstation-backend-current')).toContainText('http://localhost:8001')
    await expect(page.getByTestId('desktop-local-model-manager')).toBeVisible()
    await expect(page.getByTestId('local-model-default')).toContainText('qwen2.5:7b')
    await expect(page.getByTestId('local-model-count')).toContainText('2 个')

    await page.getByTestId('local-model-input').fill('llama3.1:8b')
    await page.getByTestId('local-model-save').click()

    await expect(page.getByTestId('local-model-default')).toContainText('llama3.1:8b')
    await expect(page.getByTestId('desktop-native-notification-manager')).toContainText('可测试')
    await expect(page.getByTestId('native-notification-permission')).toContainText('待授权')
    await expect(page.getByTestId('native-notification-test')).toBeDisabled()

    await page.getByTestId('native-notification-permission-action').click()

    await expect(page.getByTestId('native-notification-permission')).toContainText('已授权')
    await expect(page.getByTestId('native-notification-test')).toBeEnabled()

    await page.getByTestId('native-notification-test').click()

    await expect.poll(async () => page.evaluate(() => {
      const calls = (window as any).__nativeNotificationInvokes as Array<Record<string, unknown> | undefined>
      return calls.some((payload) => payload?.kind === 'case_progress' && payload?.relatedId === 'desktop-workstation-smoke')
    })).toBe(true)

    await page.getByTestId('workstation-mode-top-secret').click()

    await expect(page.getByTestId('workstation-mode-top-secret')).toBeDisabled()
    await expect(page.getByTestId('workstation-probe-remote-control')).toContainText('已阻断')
    await expect(page.getByTestId('workstation-probe-native-notification')).toContainText('本地可用')

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

test.describe('桌面工作站移动宽度', () => {
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

    expect(cardBoxes).toHaveLength(7)
    for (const box of cardBoxes) {
      expect(box.left).toBeGreaterThanOrEqual(0)
      expect(box.right).toBeLessThanOrEqual(box.viewport + 1)
      expect(box.width).toBeGreaterThan(280)
    }
  })
})
