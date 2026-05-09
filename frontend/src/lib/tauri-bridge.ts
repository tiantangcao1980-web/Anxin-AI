/**
 * Tauri 桥接层
 *
 * 统一封装 Tauri IPC 调用，提供平台检测和原生功能接口。
 * 在 Web 环境下所有函数安全降级为空操作或默认值。
 */

import { extractDesktopFileDropPaths, type DesktopDragDropPayload } from './desktopFileDropEvents'

// ===== 平台检测 =====

/** 是否运行在 Tauri 环境中 */
export function isTauri(): boolean {
  if (typeof window === 'undefined') return false
  // 必须同时满足：Tauri 内部对象存在 + 包含 invoke 方法（排除 Vite dev webview 误判）
  const internals = (window as any).__TAURI_INTERNALS__
  return !!(internals && typeof internals.invoke === 'function')
}

/** 获取运行平台 */
export function getPlatform(): 'web' | 'desktop' | 'mobile' {
  if (!isTauri()) return 'web'
  const ua = navigator.userAgent.toLowerCase()
  if (ua.includes('android') || ua.includes('iphone') || ua.includes('ipad')) {
    return 'mobile'
  }
  return 'desktop'
}

/** 是否为桌面端 */
export function isDesktop(): boolean {
  return getPlatform() === 'desktop'
}

/** 是否为移动端 */
export function isMobile(): boolean {
  return getPlatform() === 'mobile'
}

// ===== Tauri IPC 调用 =====

// Tauri 包动态加载 — 使用 @vite-ignore 避免 Vite 静态分析

/** 安全调用 Tauri IPC 命令 */
async function invokeCommand<T>(cmd: string, args?: Record<string, unknown>): Promise<T | null> {
  if (!isTauri()) return null
  try {
    // 直接使用 Tauri 注入的 __TAURI_INTERNALS__.invoke，避免动态 import 解析失败
    const internals = (window as any).__TAURI_INTERNALS__
    if (internals?.invoke) {
      return await internals.invoke(cmd, args)
    }
    return null
  } catch (error) {
    console.debug(`[Tauri] ${cmd} 调用失败:`, error)
    return null
  }
}

async function invokeRequiredCommand<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (!isTauri()) {
    throw new Error('仅桌面客户端支持此操作')
  }
  const internals = (window as any).__TAURI_INTERNALS__
  if (!internals?.invoke) {
    throw new Error('桌面运行时不可用')
  }
  return await internals.invoke(cmd, args)
}

// ===== 运行模式 =====

export type AppMode = 'top-secret' | 'hybrid' | 'cloud'

export interface AppState {
  mode: AppMode
  sync_status: 'idle' | 'syncing' | 'error' | 'offline'
  last_sync_time: string | null
  backend_url: string
  is_online: boolean
  user_token: string | null
  unread_count: number
}

export interface WorkstationProfile {
  id: string
  name: string
  mode: AppMode
  backend_url: string
}

/** 获取应用状态 */
export async function getAppState(): Promise<AppState | null> {
  return invokeCommand<AppState>('get_app_state')
}

/** 切换运行模式 */
export async function switchMode(mode: AppMode): Promise<{ success: boolean; message: string } | null> {
  return invokeCommand('switch_mode', { mode })
}

/** 获取当前模式 */
export async function getCurrentMode(): Promise<AppMode> {
  if (!isTauri()) return 'cloud'
  const result = await invokeCommand<string>('get_current_mode')
  return (result?.replace(/"/g, '') as AppMode) || 'cloud'
}

/** 获取后端 URL */
export async function getBackendUrl(): Promise<string> {
  if (!isTauri()) return ''
  const result = await invokeCommand<string>('get_backend_url')
  return result || ''
}

/** 设置后端 URL */
export async function setBackendUrl(url: string): Promise<{ success: boolean; message: string }> {
  if (!isTauri()) {
    return { success: false, message: '仅桌面客户端支持后端地址配置' }
  }
  try {
    const internals = (window as any).__TAURI_INTERNALS__
    await internals.invoke('set_backend_url', { url })
    return { success: true, message: '后端地址已更新' }
  } catch (error) {
    return { success: false, message: error instanceof Error ? error.message : '后端地址保存失败' }
  }
}

export async function listWorkstationProfiles(): Promise<WorkstationProfile[]> {
  if (!isTauri()) return []
  const profiles = await invokeRequiredCommand<WorkstationProfile[] | null>('list_workstation_profiles')
  return Array.isArray(profiles) ? profiles : []
}

export async function createWorkstationProfile(input: {
  name: string
  mode: AppMode
  backendUrl: string
}): Promise<WorkstationProfile | null> {
  return invokeRequiredCommand<WorkstationProfile>('create_workstation_profile', {
    name: input.name,
    mode: input.mode,
    backendUrl: input.backendUrl,
  })
}

export async function updateWorkstationProfile(input: {
  id: string
  name: string
  mode: AppMode
  backendUrl: string
}): Promise<WorkstationProfile | null> {
  return invokeRequiredCommand<WorkstationProfile>('update_workstation_profile', {
    id: input.id,
    name: input.name,
    mode: input.mode,
    backendUrl: input.backendUrl,
  })
}

export async function deleteWorkstationProfile(id: string): Promise<boolean> {
  if (!isTauri()) return false
  await invokeRequiredCommand<void>('delete_workstation_profile', { id })
  return true
}

export async function applyWorkstationProfile(id: string): Promise<{ success: boolean; message: string } | null> {
  return invokeRequiredCommand('apply_workstation_profile', { id })
}

// ===== 移动远控桌面 host =====

export interface RemoteControlPairingPayload {
  pairing_id: string
  mobile_device_id?: string
  desktop_device_id: string
  requested_scopes?: string[]
  privacy_mode?: string
  status: string
  expires_at?: string | null
  confirmed_at?: string | null
}

export interface RemoteControlHostCycleSummary {
  claimed: number
  completed: number
  failed: number
  unsupported: number
  command_ids: string[]
}

export async function remoteControlConfirmPairing(input: {
  pairingId: string
  desktopDeviceId: string
}): Promise<RemoteControlPairingPayload | null> {
  return invokeRequiredCommand<RemoteControlPairingPayload>('remote_control_confirm_pairing', {
    pairingId: input.pairingId,
    desktopDeviceId: input.desktopDeviceId,
  })
}

export async function remoteControlRunHostCycle(input: {
  desktopDeviceId: string
  pairingId: string
  routeToken: string
  hostInstanceId: string
  limit?: number
}): Promise<RemoteControlHostCycleSummary | null> {
  return invokeRequiredCommand<RemoteControlHostCycleSummary>('remote_control_run_host_cycle', {
    desktopDeviceId: input.desktopDeviceId,
    pairingId: input.pairingId,
    routeToken: input.routeToken,
    hostInstanceId: input.hostInstanceId,
    limit: input.limit ?? 5,
  })
}

// ===== 同步 =====

/** 触发手动同步 */
export async function triggerSync(): Promise<{
  success: boolean
  message: string
  sync_time?: string | null
  pushed?: number
  pulled?: number
  conflicts?: number
  deferred?: number
  needs_human?: number
  push_ok?: boolean
  pull_ok?: boolean
} | null> {
  if (isTauri()) {
    try {
      const { triggerLocalSync } = await import('./api-adapter')
      const result = await triggerLocalSync()
      if (result) return result
    } catch (error) {
      console.debug('[Tauri] 本地 SQLite 同步失败，降级到 Rust IPC:', error)
    }
  }
  return invokeCommand('trigger_sync')
}

/** 获取同步状态 */
export async function getSyncStatus() {
  return invokeCommand('get_sync_status')
}

/** 获取待同步记录数 */
export async function getPendingSyncCount(): Promise<number> {
  if (isTauri()) {
    try {
      const { getPendingLocalSyncCount } = await import('./api-adapter')
      const result = await getPendingLocalSyncCount()
      if (result !== null) return result
    } catch (error) {
      console.debug('[Tauri] 本地待同步统计失败，降级到 Rust IPC:', error)
    }
  }
  const result = await invokeCommand<number>('get_pending_sync_count')
  return result ?? 0
}

/** 获取本地同步冲突列表 */
export async function getSyncConflicts() {
  if (!isTauri()) return []
  try {
    const { listLocalSyncConflicts } = await import('./api-adapter')
    return await listLocalSyncConflicts() ?? []
  } catch (error) {
    console.debug('[Tauri] 读取本地同步冲突失败:', error)
    return []
  }
}

/** 解决本地同步冲突 */
export async function resolveSyncConflict(
  logId: number,
  resolution: 'keep_local' | 'keep_remote' | 'merge',
  mergedData?: Record<string, unknown>,
) {
  if (!isTauri()) return { success: false, message: '仅桌面端支持同步冲突处理' }
  try {
    const { resolveLocalSyncConflict } = await import('./api-adapter')
    const result = await resolveLocalSyncConflict(logId, resolution, mergedData)
    return result ?? { success: false, message: '本地同步数据库不可用' }
  } catch (error) {
    console.debug('[Tauri] 解决本地同步冲突失败:', error)
    return { success: false, message: '同步冲突处理失败' }
  }
}

// ===== 本地 LLM =====

export interface LocalLLMResponse {
  success: boolean
  source: string
  model: string
  message: string | null
  total_duration?: number
}

export interface LocalLLMConfig {
  default_model: string
  endpoint_url: string
  stores_secrets: boolean
  message?: string
}

export interface LocalModelListResponse {
  available?: boolean
  models?: unknown[]
  message?: string
}

/** 调用本地 LLM */
export async function localLLMChat(
  message: string,
  model?: string,
  systemPrompt?: string
): Promise<LocalLLMResponse | null> {
  return invokeCommand('local_llm_chat', {
    message,
    model: model ?? null,
    systemPrompt: systemPrompt ?? null,
  })
}

/** 读取本地 LLM 非敏感配置 */
export async function getLocalLLMConfig(): Promise<LocalLLMConfig | null> {
  return invokeCommand('get_local_llm_config')
}

/** 设置本地默认模型名称 */
export async function setDefaultLocalModel(model: string): Promise<{ success: boolean; default_model: string; message: string } | null> {
  return invokeCommand('set_default_local_model', { model })
}

/** 列出本地可用模型 */
export async function listLocalModels(): Promise<LocalModelListResponse | null> {
  return invokeCommand('list_local_models')
}

/** 检查本地 LLM 状态 */
export async function checkLocalLLMStatus() {
  return invokeCommand('check_local_llm_status')
}

// ===== 桌面本机通知 =====

export type DesktopNotificationKind = 'case_progress' | 'risk_alert' | 'system' | 'sync'

export interface DesktopNotificationPayload {
  kind: DesktopNotificationKind
  title: string
  body: string
  relatedId?: string
}

export interface DesktopNotificationResponse {
  success: boolean
  kind: DesktopNotificationKind
  title: string
  body: string
  relatedId?: string
  localOnly: boolean
  safeInTopSecret: boolean
  privacyMode: AppMode
  message: string
}

export type DesktopNotificationPermissionState = 'granted' | 'denied' | 'prompt' | 'prompt_with_rationale'

export interface DesktopNotificationPermissionResponse {
  state: DesktopNotificationPermissionState
  granted: boolean
  canRequest: boolean
  localOnly: boolean
  safeInTopSecret: boolean
  requiresExternalPush: boolean
  privacyMode: AppMode
  message: string
}

function shouldFallbackToNotificationPlugin(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error)
  return /not found|unknown command|not registered|not allowed/i.test(message)
}

function normalizeWebNotificationPermission(value: NotificationPermission): DesktopNotificationPermissionState {
  if (value === 'granted') return 'granted'
  if (value === 'denied') return 'denied'
  return 'prompt'
}

function buildDesktopNotificationPermissionFallback(
  state: DesktopNotificationPermissionState,
  privacyMode: AppMode,
  requested: boolean
): DesktopNotificationPermissionResponse {
  const action = requested ? '授权请求' : '权限状态'
  const label = state === 'granted'
    ? '已授权'
    : state === 'denied'
      ? '已拒绝'
      : state === 'prompt_with_rationale'
        ? '需说明后授权'
        : '待授权'

  return {
    state,
    granted: state === 'granted',
    canRequest: state === 'prompt' || state === 'prompt_with_rationale',
    localOnly: true,
    safeInTopSecret: true,
    requiresExternalPush: false,
    privacyMode,
    message: `${action}: ${label}`,
  }
}

async function sendPluginNotification(title: string, body: string): Promise<void> {
  const { sendNotification: notify } = await import(/* @vite-ignore */ '@tauri-apps/plugin-notification')
  await notify({ title, body })
}

/** 生成桌面本机通知预览，不触发 OS 通知。 */
export async function previewDesktopNotification(
  payload: DesktopNotificationPayload
): Promise<DesktopNotificationResponse | null> {
  return invokeCommand<DesktopNotificationResponse>('preview_desktop_notification', { payload })
}

/** 读取桌面本机通知权限状态；仅检查本机 OS/WebView 通知，不接入外部推送。 */
export async function getDesktopNotificationPermission(): Promise<DesktopNotificationPermissionResponse | null> {
  if (!isTauri()) return null
  try {
    return await invokeRequiredCommand<DesktopNotificationPermissionResponse>('get_desktop_notification_permission')
  } catch (error) {
    if (!shouldFallbackToNotificationPlugin(error)) {
      console.debug('[Tauri] 本机通知权限读取失败:', error)
      return null
    }
  }

  try {
    const { isPermissionGranted } = await import(/* @vite-ignore */ '@tauri-apps/plugin-notification')
    const granted = await isPermissionGranted()
    const webState = typeof window !== 'undefined' && 'Notification' in window
      ? normalizeWebNotificationPermission(window.Notification.permission)
      : 'prompt'
    const privacyMode = await getCurrentMode().catch(() => 'cloud' as AppMode)
    return buildDesktopNotificationPermissionFallback(granted ? 'granted' : webState, privacyMode, false)
  } catch (pluginError) {
    console.debug('[Tauri] 通知插件权限读取失败:', pluginError)
    return null
  }
}

/** 请求桌面本机通知权限；结果仍标记为 local-only，不保存外部凭据。 */
export async function requestDesktopNotificationPermission(): Promise<DesktopNotificationPermissionResponse | null> {
  if (!isTauri()) return null
  try {
    return await invokeRequiredCommand<DesktopNotificationPermissionResponse>('request_desktop_notification_permission')
  } catch (error) {
    if (!shouldFallbackToNotificationPlugin(error)) {
      console.debug('[Tauri] 本机通知权限请求失败:', error)
      return null
    }
  }

  try {
    const { requestPermission } = await import(/* @vite-ignore */ '@tauri-apps/plugin-notification')
    const permission = await requestPermission()
    const privacyMode = await getCurrentMode().catch(() => 'cloud' as AppMode)
    return buildDesktopNotificationPermissionFallback(
      normalizeWebNotificationPermission(permission),
      privacyMode,
      true
    )
  } catch (pluginError) {
    console.debug('[Tauri] 通知插件权限请求失败:', pluginError)
    return null
  }
}

/** 发送桌面本机通知；不经过 APNs/FCM/服务端推送。 */
export async function sendDesktopNotification(
  payload: DesktopNotificationPayload
): Promise<DesktopNotificationResponse | null> {
  if (!isTauri()) return null
  try {
    return await invokeRequiredCommand<DesktopNotificationResponse>('send_desktop_notification', { payload })
  } catch (error) {
    if (!shouldFallbackToNotificationPlugin(error)) {
      console.error('[Tauri] 本机通知发送失败:', error)
      return null
    }

    try {
      await sendPluginNotification(payload.title, payload.body)
      const privacyMode = await getCurrentMode().catch(() => 'cloud' as AppMode)
      return {
        success: true,
        kind: payload.kind,
        title: payload.title,
        body: payload.body,
        relatedId: payload.relatedId,
        localOnly: true,
        safeInTopSecret: true,
        privacyMode,
        message: '本机通知已通过插件发送',
      }
    } catch (pluginError) {
      console.error('[Tauri] 通知插件降级发送失败:', pluginError)
      return null
    }
  }
}

// ===== 桌面快问窗口 =====

export async function hideQuickQueryWindow(): Promise<boolean> {
  if (!isTauri()) return false
  try {
    await invokeRequiredCommand<void>('hide_quick_query_window')
    return true
  } catch (error) {
    console.debug('[Tauri] 隐藏快问窗口失败:', error)
    return false
  }
}

// ===== 桌面文件拖入分析 =====

export const FILE_DROP_QUEUED_EVENT = 'desktop://file-queued'

export interface FileDropQueuedTask {
  task_id: string
  file_name: string
  task_type: string
  action_label: string
}

export interface UnsupportedFileDrop {
  file_name: string
  reason: string
}

export interface FileDropQueueReport {
  queued: FileDropQueuedTask[]
  unsupported: UnsupportedFileDrop[]
}

export async function queueFileDropPaths(paths: string[]): Promise<FileDropQueueReport | null> {
  if (!isTauri()) return null
  return invokeRequiredCommand<FileDropQueueReport>('queue_file_drop_paths', { paths })
}

export async function listenFileDropQueued(
  onQueued: (report: FileDropQueueReport) => void,
): Promise<() => void> {
  return listenEvent<FileDropQueueReport>(FILE_DROP_QUEUED_EVENT, onQueued)
}

export async function listenDesktopFileDrops(onDrop: (paths: string[]) => void): Promise<() => void> {
  if (!isTauri()) return () => {}

  try {
    const { getCurrentWebview } = await import(/* @vite-ignore */ '@tauri-apps/api/webview')
    return await getCurrentWebview().onDragDropEvent((event: { payload: DesktopDragDropPayload }) => {
      const paths = extractDesktopFileDropPaths(event.payload)
      if (paths.length > 0) {
        onDrop(paths)
      }
    })
  } catch (error) {
    console.debug('[Tauri] 监听桌面文件拖放失败:', error)
    return () => {}
  }
}

export async function minimizeCurrentWindow(): Promise<boolean> {
  if (!isTauri()) return false

  try {
    const { getCurrentWindow } = await import(/* @vite-ignore */ '@tauri-apps/api/window')
    await getCurrentWindow().minimize()
    return true
  } catch (error) {
    console.debug('[Tauri] 最小化窗口失败:', error)
    return false
  }
}

export async function toggleMaximizeCurrentWindow(): Promise<boolean> {
  if (!isTauri()) return false

  try {
    const { getCurrentWindow } = await import(/* @vite-ignore */ '@tauri-apps/api/window')
    await getCurrentWindow().toggleMaximize()
    return true
  } catch (error) {
    console.debug('[Tauri] 切换窗口最大化失败:', error)
    return false
  }
}

export async function closeCurrentWindow(): Promise<boolean> {
  if (!isTauri()) return false

  try {
    const { getCurrentWindow } = await import(/* @vite-ignore */ '@tauri-apps/api/window')
    await getCurrentWindow().close()
    return true
  } catch (error) {
    console.debug('[Tauri] 关闭窗口失败:', error)
    return false
  }
}

// ===== 离线任务队列（Harness Engineering）=====

/** 提交离线任务 */
export async function submitOfflineTask(
  taskType: string,
  description: string,
  conversationId?: string,
  priority?: number
): Promise<string | null> {
  return invokeCommand('submit_offline_task', {
    taskType,
    description,
    conversationId: conversationId ?? null,
    priority: priority ?? 2,
  })
}

/** 获取离线队列统计 */
export async function getQueueStats() {
  return invokeCommand('get_queue_stats')
}

export interface OfflineTaskSummary {
  id: string
  taskType: string
  title: string
  detail: string
  status: string
  priority: number
  createdAt: string
  updatedAt: string
  retryCount: number
  hasLocalResult: boolean
  errorMessage?: string
}

export interface OfflineQueueRetryReport {
  retried: number
  localOnly: boolean
  safeInTopSecret: boolean
  message: string
}

/** 列出最近离线任务。完整本地路径留在 SQLCipher 队列内，前端只拿摘要。 */
export async function listOfflineTasks(limit = 8): Promise<OfflineTaskSummary[]> {
  if (!isTauri()) return []
  return await invokeRequiredCommand<OfflineTaskSummary[]>('list_offline_tasks', { limit })
}

/** 将失败离线任务重新放回本地队列；只改本机 SQLCipher 状态，不触网。 */
export async function retryFailedOfflineTasks(): Promise<OfflineQueueRetryReport | null> {
  if (!isTauri()) return null
  return invokeRequiredCommand<OfflineQueueRetryReport>('retry_failed_offline_tasks')
}

/** 触发离线任务批量同步 */
export async function flushOfflineQueue(): Promise<string | null> {
  return invokeCommand('flush_offline_queue')
}

/** 推送 Harness Artifact 到云端 */
export async function pushHarnessArtifacts(
  sessionId: string,
  artifacts: Record<string, any>,
  deviceId: string
): Promise<string | null> {
  return invokeCommand('push_harness_artifacts', {
    sessionId,
    artifacts,
    deviceId,
  })
}

/** 拉取 Harness Artifact */
export async function pullHarnessArtifacts(
  sessionId: string,
  artifactTypes?: string[]
): Promise<Record<string, any> | null> {
  return invokeCommand('pull_harness_artifacts', {
    sessionId,
    artifactTypes: artifactTypes ?? null,
  })
}

// ===== CLI 命令接口 =====

/** 执行 CLI 命令 */
export async function cliExecute(
  command: string,
  args: Record<string, any> = {},
  apiKey?: string,
  routeToken?: string,
  routeKey?: string
) {
  return invokeCommand('cli_execute', {
    command,
    args,
    apiKey: apiKey ?? null,
    routeToken: routeToken ?? null,
    routeKey: routeKey ?? null,
  })
}

/** 创建 CLI API Key */
export async function cliCreateKey(name: string, scopes: string[] = ['read', 'chat'], expiresDays?: number) {
  return invokeCommand('cli_create_key', { name, scopes, expiresDays: expiresDays ?? 90 })
}

/** 列出 CLI API Keys */
export async function cliListKeys() {
  return invokeCommand('cli_list_keys')
}

// ===== 认证 =====

/** 保存认证 Token */
export async function saveAuthToken(token: string, refreshToken?: string) {
  return invokeCommand('save_auth_token', {
    token,
    refreshToken: refreshToken ?? null,
  })
}

/** 清除认证信息 */
export async function clearAuth() {
  return invokeCommand('clear_auth')
}

/** 获取应用信息 */
export async function getAppInfo() {
  return invokeCommand('get_app_info')
}

// ===== 系统通知 =====

/** 发送系统通知 */
export async function sendNotification(title: string, body: string) {
  if (!isTauri()) return
  try {
    const result = await sendDesktopNotification({ kind: 'system', title, body })
    if (!result?.success) {
      await sendPluginNotification(title, body)
    }
  } catch (error) {
    console.error('[Tauri] 通知发送失败:', error)
  }
}

/** 请求通知权限 */
export async function requestNotificationPermission(): Promise<boolean> {
  if (!isTauri()) return false
  const permission = await requestDesktopNotificationPermission()
  return Boolean(permission?.granted)
}

// ===== 文件操作 =====

/** 打开文件选择对话框 */
export async function pickFile(filters?: { name: string; extensions: string[] }[]) {
  if (!isTauri()) return null
  try {
    const { open } = await import(/* @vite-ignore */ '@tauri-apps/plugin-dialog')
    return await open({
      multiple: false,
      filters: filters ?? [
        { name: '文档', extensions: ['pdf', 'doc', 'docx', 'txt', 'md'] },
        { name: '表格', extensions: ['xlsx', 'xls', 'csv'] },
        { name: '所有文件', extensions: ['*'] },
      ],
    })
  } catch {
    return null
  }
}

/** 保存文件对话框 */
export async function saveFileDialog(defaultPath?: string) {
  if (!isTauri()) return null
  try {
    const { save } = await import(/* @vite-ignore */ '@tauri-apps/plugin-dialog')
    return await save({ defaultPath })
  } catch {
    return null
  }
}

// ===== 剪贴板 =====

/** 复制文本到剪贴板 */
export async function copyToClipboard(text: string) {
  if (isTauri()) {
    try {
      const { writeText } = await import(/* @vite-ignore */ '@tauri-apps/plugin-clipboard-manager')
      await writeText(text)
      return
    } catch { /* fallback */ }
  }
  await navigator.clipboard.writeText(text)
}

// ===== 事件监听 =====

/** 监听 Tauri 事件 */
export async function listenEvent<T>(event: string, handler: (payload: T) => void) {
  if (!isTauri()) return () => {}
  try {
    const { listen } = await import(/* @vite-ignore */ '@tauri-apps/api/event')
    const unlisten = await listen<T>(event, (e) => handler(e.payload))
    return unlisten
  } catch {
    return () => {}
  }
}

// ===== OTA 更新 =====

/** 检查并安装更新 */
export async function checkForUpdates(): Promise<{ available: boolean; version?: string } | null> {
  if (!isTauri()) return null
  try {
    const { check } = await import(/* @vite-ignore */ '@tauri-apps/plugin-updater')
    const update = await check()
    if (update) {
      return { available: true, version: update.version }
    }
    return { available: false }
  } catch (error) {
    console.error('[Tauri] 更新检查失败:', error)
    return null
  }
}
