/**
 * Tauri 桥接层
 *
 * 统一封装 Tauri IPC 调用，提供平台检测和原生功能接口。
 * 在 Web 环境下所有函数安全降级为空操作或默认值。
 */

// ===== 平台检测 =====

/** 是否运行在 Tauri 环境中 */
export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
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

// 动态包名，避免 Vite 在 Web 模式下静态解析 @tauri-apps 包
const TAURI_CORE = '@tauri-apps' + '/api/core'
const TAURI_NOTIFICATION = '@tauri-apps' + '/plugin-notification'
const TAURI_DIALOG = '@tauri-apps' + '/plugin-dialog'
const TAURI_CLIPBOARD = '@tauri-apps' + '/plugin-clipboard-manager'
const TAURI_EVENT = '@tauri-apps' + '/api/event'
const TAURI_UPDATER = '@tauri-apps' + '/plugin-updater'

/** 安全调用 Tauri IPC 命令 */
async function invokeCommand<T>(cmd: string, args?: Record<string, unknown>): Promise<T | null> {
  if (!isTauri()) return null
  try {
    const mod = await import(TAURI_CORE)
    return await mod.invoke(cmd, args)
  } catch (error) {
    console.error(`[Tauri] ${cmd} 调用失败:`, error)
    return null
  }
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

// ===== 同步 =====

/** 触发手动同步 */
export async function triggerSync(): Promise<{ success: boolean; message: string } | null> {
  return invokeCommand('trigger_sync')
}

/** 获取同步状态 */
export async function getSyncStatus() {
  return invokeCommand('get_sync_status')
}

/** 获取待同步记录数 */
export async function getPendingSyncCount(): Promise<number> {
  const result = await invokeCommand<number>('get_pending_sync_count')
  return result ?? 0
}

// ===== 本地 LLM =====

export interface LocalLLMResponse {
  success: boolean
  source: string
  model: string
  message: string | null
  total_duration?: number
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

/** 列出本地可用模型 */
export async function listLocalModels() {
  return invokeCommand('list_local_models')
}

/** 检查本地 LLM 状态 */
export async function checkLocalLLMStatus() {
  return invokeCommand('check_local_llm_status')
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
    const { sendNotification: notify } = await import(TAURI_NOTIFICATION)
    await notify({ title, body })
  } catch (error) {
    console.error('[Tauri] 通知发送失败:', error)
  }
}

/** 请求通知权限 */
export async function requestNotificationPermission(): Promise<boolean> {
  if (!isTauri()) return false
  try {
    const { requestPermission } = await import(TAURI_NOTIFICATION)
    const perm = await requestPermission()
    return perm === 'granted'
  } catch {
    return false
  }
}

// ===== 文件操作 =====

/** 打开文件选择对话框 */
export async function pickFile(filters?: { name: string; extensions: string[] }[]) {
  if (!isTauri()) return null
  try {
    const { open } = await import(TAURI_DIALOG)
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
    const { save } = await import(TAURI_DIALOG)
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
      const { writeText } = await import(TAURI_CLIPBOARD)
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
