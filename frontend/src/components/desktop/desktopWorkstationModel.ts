export type WorkstationMode = 'top-secret' | 'hybrid' | 'cloud'
export type WorkstationRuntime = 'desktop' | 'preview'

export type WorkstationResourceStatus = 'ready' | 'available' | 'restricted' | 'blocked' | 'pending'

export interface WorkstationModeOption {
  mode: WorkstationMode
  label: string
  description: string
}

export interface WorkstationAction {
  label: string
  path: string
  enabled: boolean
  safeInTopSecret: boolean
  disabledReason?: string
}

export interface WorkstationResource {
  id: 'privacy' | 'local-model' | 'knowledge' | 'skills-mcp' | 'sync' | 'remote-control'
  title: string
  status: WorkstationResourceStatus
  statusLabel: string
  summary: string
  action: WorkstationAction
}

const TOP_SECRET_RESTRICTION = '绝密模式下默认不出站'
const DESKTOP_CLIENT_REQUIRED = '请在桌面客户端启用'

export const WORKSTATION_MODE_OPTIONS: WorkstationModeOption[] = [
  {
    mode: 'top-secret',
    label: '绝密',
    description: '本地闭环，默认阻断外部数据通道',
  },
  {
    mode: 'hybrid',
    label: '混合',
    description: '本地优先，按策略连接组织服务',
  },
  {
    mode: 'cloud',
    label: '云端',
    description: '完整云端协同与外部能力接入',
  },
]

export function buildDesktopWorkstationResources(
  mode: WorkstationMode,
  runtime: WorkstationRuntime = 'desktop'
): WorkstationResource[] {
  const isTopSecret = mode === 'top-secret'
  const isDesktopRuntime = runtime === 'desktop'

  return [
    {
      id: 'privacy',
      title: '隐私模式',
      status: mode === 'top-secret' ? 'ready' : 'available',
      statusLabel: mode === 'top-secret' ? '本地闭环' : mode === 'hybrid' ? '本地优先' : '云端增强',
      summary: mode === 'top-secret' ? '外部数据通道默认关闭' : '按组织策略启用连接',
      action: {
        label: '查看模式',
        path: '/settings?tab=workstation',
        enabled: true,
        safeInTopSecret: true,
      },
    },
    {
      id: 'local-model',
      title: '本地模型',
      status: isDesktopRuntime ? 'available' : 'pending',
      statusLabel: isDesktopRuntime ? '可配置' : '需桌面端',
      summary: isDesktopRuntime ? 'Ollama 与本地兼容端点' : '桌面客户端内配置本地模型',
      action: {
        label: '配置模型',
        path: '/private-llm',
        enabled: isDesktopRuntime,
        safeInTopSecret: true,
        disabledReason: isDesktopRuntime ? undefined : DESKTOP_CLIENT_REQUIRED,
      },
    },
    {
      id: 'knowledge',
      title: '独立知识库',
      status: 'available',
      statusLabel: isTopSecret ? '仅本地' : '可同步',
      summary: isTopSecret ? '使用已下载资料与本地索引' : '可连接组织资料与本地索引',
      action: {
        label: '打开知识库',
        path: '/knowledge-base',
        enabled: true,
        safeInTopSecret: true,
      },
    },
    {
      id: 'skills-mcp',
      title: 'Skills / MCP',
      status: isTopSecret ? 'restricted' : 'available',
      statusLabel: isTopSecret ? '审批后启用' : '可治理',
      summary: isTopSecret ? '外部连接保持关闭' : '按 allowlist 与审批策略连接',
      action: {
        label: isTopSecret ? '查看治理' : '配置服务',
        path: '/settings?tab=mcp',
        enabled: true,
        safeInTopSecret: true,
      },
    },
    {
      id: 'sync',
      title: '跨端同步',
      status: isTopSecret ? 'blocked' : isDesktopRuntime ? 'available' : 'pending',
      statusLabel: isTopSecret ? '已阻断' : isDesktopRuntime ? '可用' : '需桌面端',
      summary: isTopSecret
        ? TOP_SECRET_RESTRICTION
        : isDesktopRuntime
          ? '可同步任务、知识与工作记录'
          : '桌面客户端内查看同步状态',
      action: {
        label: '同步状态',
        path: '/sync-conflicts',
        enabled: !isTopSecret && isDesktopRuntime,
        safeInTopSecret: false,
        disabledReason: isTopSecret ? TOP_SECRET_RESTRICTION : isDesktopRuntime ? undefined : DESKTOP_CLIENT_REQUIRED,
      },
    },
    {
      id: 'remote-control',
      title: '移动远控桌面',
      status: isTopSecret ? 'blocked' : 'pending',
      statusLabel: isTopSecret ? '已阻断' : isDesktopRuntime ? '待验收' : '需桌面端',
      summary: isTopSecret
        ? TOP_SECRET_RESTRICTION
        : isDesktopRuntime
          ? '等待设备配对与命令审计证据'
          : '桌面客户端作为受控主机',
      action: {
        label: '查看任务',
        path: '/settings?tab=workstation',
        enabled: !isTopSecret && isDesktopRuntime,
        safeInTopSecret: false,
        disabledReason: isTopSecret ? TOP_SECRET_RESTRICTION : isDesktopRuntime ? undefined : DESKTOP_CLIENT_REQUIRED,
      },
    },
  ]
}

export function getUnsafeEnabledTopSecretActions(resources: WorkstationResource[]): WorkstationAction[] {
  return resources
    .map((resource) => resource.action)
    .filter((action) => action.enabled && !action.safeInTopSecret)
}

export function normalizeWorkstationBackendUrl(input: string): { ok: true; value: string } | { ok: false; error: string } {
  const trimmed = input.trim()
  if (!trimmed) {
    return { ok: false, error: '后端地址不能为空' }
  }

  let parsed: URL
  try {
    parsed = new URL(trimmed)
  } catch {
    return { ok: false, error: '请输入完整的 http:// 或 https:// 地址' }
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    return { ok: false, error: '后端地址只允许 http 或 https 协议' }
  }

  if (!parsed.hostname) {
    return { ok: false, error: '后端地址缺少主机名' }
  }

  return { ok: true, value: parsed.toString().replace(/\/$/, '') }
}
