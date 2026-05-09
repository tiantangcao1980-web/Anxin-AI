import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { knowledgeApi, mcpApi } from '@/lib/api'
import { useAppModeStore } from '@/lib/store'
import {
  checkLocalLLMStatus,
  applyWorkstationProfile,
  createWorkstationProfile,
  deleteWorkstationProfile,
  getAppState,
  getQueueStats,
  isTauri,
  listLocalModels,
  listWorkstationProfiles,
  setBackendUrl,
  switchMode,
  updateWorkstationProfile,
  type AppMode,
  type AppState,
  type WorkstationProfile,
} from '@/lib/tauri-bridge'
import { heading, iconSize, statusBadge } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import { cn } from '@/lib/utils'
import {
  buildDesktopWorkstationResources,
  normalizeWorkstationBackendUrl,
  WORKSTATION_MODE_OPTIONS,
  type WorkstationMode,
  type WorkstationResource,
  type WorkstationResourceStatus,
} from './desktopWorkstationModel'

const MODE_LABEL: Record<WorkstationMode, string> = {
  'top-secret': '绝密',
  hybrid: '混合',
  cloud: '云端',
}

const STATUS_CLASS: Record<WorkstationResourceStatus, string> = {
  ready: statusBadge.success,
  available: statusBadge.info,
  restricted: statusBadge.warning,
  blocked: statusBadge.error,
  pending: statusBadge.neutral,
}

const RESOURCE_ICON: Record<WorkstationResource['id'], typeof icons.LayoutDashboard> = {
  privacy: icons.ShieldCheck,
  'local-model': icons.Cpu,
  knowledge: icons.Database,
  'skills-mcp': icons.Server,
  sync: icons.RefreshCw,
  'remote-control': icons.Phone,
}

type ProbeStatus = 'preview' | 'loading' | 'ready'
type ServiceProbeStatus = ProbeStatus | 'skipped' | 'error'

interface WorkstationProbeState {
  status: ProbeStatus
  knowledgeStatus: ServiceProbeStatus
  mcpStatus: ServiceProbeStatus
  localModelAvailable: boolean
  localModelUrl: string
  localModelCount: number
  knowledgeBaseTotal: number
  knowledgeDocumentCount: number
  mcpServerCount: number
  mcpEnabledCount: number
  mcpToolCount: number
  queueTotal: number
  queueFailed: number
}

const PREVIEW_PROBES: WorkstationProbeState = {
  status: 'preview',
  knowledgeStatus: 'preview',
  mcpStatus: 'preview',
  localModelAvailable: false,
  localModelUrl: '',
  localModelCount: 0,
  knowledgeBaseTotal: 0,
  knowledgeDocumentCount: 0,
  mcpServerCount: 0,
  mcpEnabledCount: 0,
  mcpToolCount: 0,
  queueTotal: 0,
  queueFailed: 0,
}

const DEFAULT_PROFILE_FORM = {
  name: '',
  mode: 'hybrid' as AppMode,
  backendUrl: '',
}

export function DesktopWorkstationPanel() {
  const navigate = useNavigate()
  const mode = useAppModeStore((state) => state.mode)
  const setMode = useAppModeStore((state) => state.setMode)
  const setSyncStatus = useAppModeStore((state) => state.setSyncStatus)
  const setLastSyncTime = useAppModeStore((state) => state.setLastSyncTime)
  const setOnline = useAppModeStore((state) => state.setOnline)
  const desktopClient = isTauri()
  const [appState, setAppState] = useState<AppState | null>(null)
  const [backendUrlInput, setBackendUrlInput] = useState('')
  const [configBusy, setConfigBusy] = useState<'mode' | 'backend' | null>(null)
  const [profileBusy, setProfileBusy] = useState<'save' | 'apply' | 'delete' | null>(null)
  const [profiles, setProfiles] = useState<WorkstationProfile[]>([])
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null)
  const [profileForm, setProfileForm] = useState(DEFAULT_PROFILE_FORM)
  const [probes, setProbes] = useState<WorkstationProbeState>(PREVIEW_PROBES)
  const resources = useMemo(
    () => buildDesktopWorkstationResources(mode, desktopClient ? 'desktop' : 'preview'),
    [desktopClient, mode]
  )
  const applyAppState = useCallback((snapshot: AppState | null) => {
    if (!snapshot) return
    setAppState(snapshot)
    setBackendUrlInput(snapshot.backend_url ?? '')
    setMode(snapshot.mode)
    setSyncStatus(snapshot.sync_status)
    setLastSyncTime(snapshot.last_sync_time)
    setOnline(snapshot.is_online)
  }, [setLastSyncTime, setMode, setOnline, setSyncStatus])

  const refreshProfiles = useCallback(async () => {
    if (!desktopClient) {
      setProfiles([])
      return
    }
    setProfiles(await listWorkstationProfiles())
  }, [desktopClient])

  useEffect(() => {
    let cancelled = false

    if (!desktopClient) {
      setAppState(null)
      setBackendUrlInput('')
      setProfiles([])
      setEditingProfileId(null)
      setProfileForm(DEFAULT_PROFILE_FORM)
      setProbes(PREVIEW_PROBES)
      return () => {
        cancelled = true
      }
    }

    setProbes((current) => ({
      ...current,
      status: 'loading',
      knowledgeStatus: mode === 'top-secret' ? 'skipped' : 'loading',
      mcpStatus: mode === 'top-secret' ? 'skipped' : 'loading',
    }))

    refreshProfiles()

    Promise.allSettled([
      getAppState(),
      checkLocalLLMStatus(),
      listLocalModels(),
      getQueueStats(),
      mode === 'top-secret' ? Promise.resolve(null) : knowledgeApi.listBases({ page_size: 100 }),
      mode === 'top-secret' ? Promise.resolve(null) : mcpApi.listServers(),
    ]).then(([appStateResult, llmResult, modelsResult, queueResult, knowledgeResult, mcpResult]) => {
      if (cancelled) return

      const snapshot = appStateResult.status === 'fulfilled' ? appStateResult.value : null
      applyAppState(snapshot)
      const llm = llmResult.status === 'fulfilled' ? llmResult.value as Record<string, unknown> | null : null
      const models = modelsResult.status === 'fulfilled' ? modelsResult.value as Record<string, unknown> | null : null
      const queue = queueResult.status === 'fulfilled' ? queueResult.value as Record<string, unknown> | null : null
      const knowledge = knowledgeResult.status === 'fulfilled'
        ? knowledgeResult.value as { items?: Array<{ doc_count?: number }>; total?: number } | null
        : null
      const mcpServers = mcpResult.status === 'fulfilled' && Array.isArray(mcpResult.value) ? mcpResult.value : []
      const modelItems = Array.isArray(models?.models) ? models.models : []
      const knowledgeItems = Array.isArray(knowledge?.items) ? knowledge.items : []

      setProbes({
        status: 'ready',
        knowledgeStatus: mode === 'top-secret' ? 'skipped' : knowledgeResult.status === 'fulfilled' ? 'ready' : 'error',
        mcpStatus: mode === 'top-secret' ? 'skipped' : mcpResult.status === 'fulfilled' ? 'ready' : 'error',
        localModelAvailable: Boolean(llm?.available || models?.available),
        localModelUrl: typeof llm?.url === 'string' ? llm.url : '',
        localModelCount: modelItems.length,
        knowledgeBaseTotal: Number(knowledge?.total ?? knowledgeItems.length),
        knowledgeDocumentCount: knowledgeItems.reduce((total, item) => total + Number(item.doc_count ?? 0), 0),
        mcpServerCount: mcpServers.length,
        mcpEnabledCount: mcpServers.filter((server) => Boolean(server?.is_enabled)).length,
        mcpToolCount: mcpServers.reduce((total, server) => {
          return total + (Array.isArray(server?.cached_tools) ? server.cached_tools.length : 0)
        }, 0),
        queueTotal: Number(queue?.total ?? 0),
        queueFailed: Number(queue?.failed ?? 0),
      })
    })

    return () => {
      cancelled = true
    }
  }, [applyAppState, desktopClient, mode, refreshProfiles])

  const handleModeChange = async (nextMode: AppMode) => {
    if (!desktopClient) {
      toast.error('请在桌面客户端内切换工作站模式')
      return
    }
    if (nextMode === mode || configBusy) return

    setConfigBusy('mode')
    try {
      const result = await switchMode(nextMode)
      if (!result?.success) {
        toast.error(result?.message || '工作站模式切换失败')
        return
      }
      setMode(nextMode)
      toast.success(result.message || '工作站模式已更新')
      applyAppState(await getAppState())
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '工作站模式切换失败')
    } finally {
      setConfigBusy(null)
    }
  }

  const handleBackendSave = async () => {
    if (!desktopClient) {
      toast.error('请在桌面客户端内配置后端地址')
      return
    }
    if (configBusy) return

    const normalized = normalizeWorkstationBackendUrl(backendUrlInput)
    if (!normalized.ok) {
      toast.error(normalized.error)
      return
    }

    setConfigBusy('backend')
    try {
      const result = await setBackendUrl(normalized.value)
      if (!result.success) {
        toast.error(result.message)
        return
      }
      toast.success(result.message)
      applyAppState(await getAppState())
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '后端地址保存失败')
    } finally {
      setConfigBusy(null)
    }
  }

  const handleProfileEdit = (profile: WorkstationProfile) => {
    setEditingProfileId(profile.id)
    setProfileForm({
      name: profile.name,
      mode: profile.mode,
      backendUrl: profile.backend_url,
    })
  }

  const resetProfileForm = () => {
    setEditingProfileId(null)
    setProfileForm({
      ...DEFAULT_PROFILE_FORM,
      backendUrl: appState?.backend_url ?? '',
      mode,
    })
  }

  const handleProfileSave = async () => {
    if (!desktopClient) {
      toast.error('请在桌面客户端内保存工作站配置档')
      return
    }
    if (profileBusy) return
    const name = profileForm.name.trim()
    if (!name) {
      toast.error('配置档名称不能为空')
      return
    }
    const normalized = normalizeWorkstationBackendUrl(profileForm.backendUrl)
    if (!normalized.ok) {
      toast.error(normalized.error)
      return
    }

    setProfileBusy('save')
    try {
      const saved = editingProfileId
        ? await updateWorkstationProfile({
            id: editingProfileId,
            name,
            mode: profileForm.mode,
            backendUrl: normalized.value,
          })
        : await createWorkstationProfile({
            name,
            mode: profileForm.mode,
            backendUrl: normalized.value,
          })
      if (!saved) {
        toast.error('工作站配置档保存失败')
        return
      }
      toast.success(editingProfileId ? '工作站配置档已更新' : '工作站配置档已保存')
      await refreshProfiles()
      setEditingProfileId(null)
      setProfileForm(DEFAULT_PROFILE_FORM)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '工作站配置档保存失败')
    } finally {
      setProfileBusy(null)
    }
  }

  const handleProfileApply = async (profileId: string) => {
    if (!desktopClient || profileBusy) return
    setProfileBusy('apply')
    try {
      const result = await applyWorkstationProfile(profileId)
      if (!result?.success) {
        toast.error(result?.message || '工作站配置档应用失败')
        return
      }
      toast.success(result.message || '工作站配置档已应用')
      applyAppState(await getAppState())
      await refreshProfiles()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '工作站配置档应用失败')
    } finally {
      setProfileBusy(null)
    }
  }

  const handleProfileDelete = async (profileId: string) => {
    if (!desktopClient || profileBusy) return
    setProfileBusy('delete')
    try {
      await deleteWorkstationProfile(profileId)
      toast.success('工作站配置档已删除')
      if (editingProfileId === profileId) {
        resetProfileForm()
      }
      await refreshProfiles()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '工作站配置档删除失败')
    } finally {
      setProfileBusy(null)
    }
  }

  return (
    <div className="space-y-4" data-testid="desktop-workstation-panel">
      <Card className="border-border rounded-xl">
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className={heading.section}>桌面主工作站</CardTitle>
              <CardDescription className={heading.muted}>
                {desktopClient ? '当前客户端能力状态' : '桌面能力预览，完整本地能力须在桌面客户端启用'}
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={mode === 'top-secret' ? statusBadge.success : statusBadge.info}>
                {MODE_LABEL[mode]}模式
              </Badge>
              <Badge variant="outline">
                {desktopClient ? '桌面在线' : '非桌面预览'}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {resources.map((resource) => {
              const ResourceIcon = RESOURCE_ICON[resource.id]
              return (
                <div
                  key={resource.id}
                  data-testid={`desktop-workstation-resource-${resource.id}`}
                  className="flex min-h-[142px] min-w-0 flex-col justify-between rounded-lg border border-border bg-surface-1 p-4"
                >
                  <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex min-w-0 items-start gap-3">
                      <div className="shrink-0 rounded-lg bg-muted p-2 text-muted-foreground">
                        <ResourceIcon className={iconSize.md} />
                      </div>
                      <div className="min-w-0">
                        <h3 className={heading.card}>{resource.title}</h3>
                        <p className="mt-1 text-sm text-muted-foreground">{resource.summary}</p>
                      </div>
                    </div>
                    <span className={`w-fit shrink-0 rounded px-2 py-1 text-xs font-medium ${STATUS_CLASS[resource.status]}`}>
                      {resource.statusLabel}
                    </span>
                  </div>
                  <div className="mt-4 flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <span className="text-xs text-muted-foreground">
                      {resource.action.disabledReason ?? '策略已就绪'}
                    </span>
                    <Button
                      size="sm"
                      variant={resource.action.enabled ? 'outline' : 'ghost'}
                      className="w-full sm:w-auto"
                      disabled={!resource.action.enabled}
                      onClick={() => navigate(resource.action.path)}
                    >
                      {resource.action.label}
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="border-border rounded-xl" data-testid="desktop-workstation-config">
        <CardHeader className="pb-3">
          <CardTitle className={heading.card}>工作站配置</CardTitle>
          <CardDescription className={heading.muted}>
            {desktopClient ? '配置本机运行模式与后端环境，保存后立即作用于桌面运行时' : '仅桌面客户端可写入本机运行时配置'}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <Label className="text-sm font-medium text-foreground">运行模式</Label>
              <span className="text-xs text-muted-foreground">
                当前：{MODE_LABEL[mode]}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-3" role="group" aria-label="工作站运行模式">
              {WORKSTATION_MODE_OPTIONS.map((option) => {
                const selected = option.mode === mode
                return (
                  <button
                    key={option.mode}
                    type="button"
                    data-testid={`workstation-mode-${option.mode}`}
                    disabled={!desktopClient || Boolean(configBusy) || selected}
                    onClick={() => handleModeChange(option.mode)}
                    className={cn(
                      'min-h-[88px] rounded-lg border p-3 text-left transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      selected
                        ? 'border-primary bg-primary/10 text-foreground'
                        : 'border-border bg-surface-1 hover:border-primary/50 hover:bg-muted/50',
                      (!desktopClient || Boolean(configBusy) || selected) && 'cursor-not-allowed opacity-80'
                    )}
                  >
                    <span className="block text-sm font-semibold">{option.label}</span>
                    <span className="mt-1 block text-xs leading-5 text-muted-foreground">{option.description}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="workstation-backend-url" className="text-sm font-medium text-foreground">
                后端环境
              </Label>
              <span className="text-xs text-muted-foreground" data-testid="workstation-backend-current">
                {desktopClient ? appState?.backend_url || '读取中' : '需桌面端'}
              </span>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                id="workstation-backend-url"
                data-testid="workstation-backend-url"
                value={backendUrlInput}
                onChange={(event) => setBackendUrlInput(event.target.value)}
                placeholder="https://api.example.com"
                disabled={!desktopClient || configBusy === 'backend'}
                className="min-w-0"
              />
              <Button
                type="button"
                data-testid="workstation-backend-save"
                onClick={handleBackendSave}
                disabled={!desktopClient || configBusy === 'backend'}
                className="shrink-0"
              >
                保存
              </Button>
            </div>
            <p className="text-xs leading-5 text-muted-foreground">
              仅保存环境地址，不保存 API 密钥；绝密模式下业务数据通道仍由运行时 guard 阻断。
            </p>
          </div>

          <div className="space-y-3 xl:col-span-2" data-testid="workstation-profile-manager">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <Label className="text-sm font-medium text-foreground">环境配置档</Label>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  保存常用后端与运行模式组合，配置档不包含密钥、Token 或证书。
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                data-testid="workstation-profile-new"
                disabled={!desktopClient || Boolean(profileBusy)}
                onClick={resetProfileForm}
              >
                新建
              </Button>
            </div>

            <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div className="space-y-2">
                {profiles.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border bg-muted/30 p-3 text-sm text-muted-foreground">
                    {desktopClient ? '尚未保存配置档' : '仅桌面客户端可读取本机配置档'}
                  </div>
                ) : (
                  profiles.map((profile) => (
                    <div
                      key={profile.id}
                      data-testid={`workstation-profile-${profile.id}`}
                      className="rounded-lg border border-border bg-surface-1 p-3"
                    >
                      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">{profile.name}</p>
                          <p className="mt-1 break-all text-xs text-muted-foreground">
                            {MODE_LABEL[profile.mode]} · {profile.backend_url}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-wrap gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            data-testid={`workstation-profile-apply-${profile.id}`}
                            disabled={!desktopClient || Boolean(profileBusy)}
                            onClick={() => handleProfileApply(profile.id)}
                          >
                            应用
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            data-testid={`workstation-profile-edit-${profile.id}`}
                            disabled={!desktopClient || Boolean(profileBusy)}
                            onClick={() => handleProfileEdit(profile)}
                          >
                            编辑
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            data-testid={`workstation-profile-delete-${profile.id}`}
                            disabled={!desktopClient || Boolean(profileBusy)}
                            onClick={() => handleProfileDelete(profile.id)}
                          >
                            删除
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="space-y-3 rounded-lg border border-border bg-surface-1 p-3">
                <div className="grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
                  <div className="space-y-2">
                    <Label htmlFor="workstation-profile-name" className="text-xs font-medium text-muted-foreground">
                      名称
                    </Label>
                    <Input
                      id="workstation-profile-name"
                      data-testid="workstation-profile-name"
                      value={profileForm.name}
                      onChange={(event) => setProfileForm((current) => ({ ...current, name: event.target.value }))}
                      placeholder="预发环境"
                      disabled={!desktopClient || profileBusy === 'save'}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="workstation-profile-backend-url" className="text-xs font-medium text-muted-foreground">
                      后端地址
                    </Label>
                    <Input
                      id="workstation-profile-backend-url"
                      data-testid="workstation-profile-backend-url"
                      value={profileForm.backendUrl}
                      onChange={(event) => setProfileForm((current) => ({ ...current, backendUrl: event.target.value }))}
                      placeholder="https://staging.anxin.example"
                      disabled={!desktopClient || profileBusy === 'save'}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3" role="group" aria-label="配置档运行模式">
                  {WORKSTATION_MODE_OPTIONS.map((option) => {
                    const selected = option.mode === profileForm.mode
                    return (
                      <button
                        key={option.mode}
                        type="button"
                        data-testid={`workstation-profile-mode-${option.mode}`}
                        disabled={!desktopClient || Boolean(profileBusy)}
                        onClick={() => setProfileForm((current) => ({ ...current, mode: option.mode }))}
                        className={cn(
                          'min-h-[64px] rounded-lg border p-3 text-left transition-colors',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                          selected
                            ? 'border-primary bg-primary/10 text-foreground'
                            : 'border-border bg-background hover:border-primary/50 hover:bg-muted/50',
                          (!desktopClient || Boolean(profileBusy)) && 'cursor-not-allowed opacity-80'
                        )}
                      >
                        <span className="block text-sm font-semibold">{option.label}</span>
                        <span className="mt-1 block text-xs leading-5 text-muted-foreground">{option.description}</span>
                      </button>
                    )
                  })}
                </div>

                <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    data-testid="workstation-profile-cancel"
                    disabled={!desktopClient || Boolean(profileBusy)}
                    onClick={resetProfileForm}
                  >
                    取消
                  </Button>
                  <Button
                    type="button"
                    data-testid="workstation-profile-save"
                    disabled={!desktopClient || profileBusy === 'save'}
                    onClick={handleProfileSave}
                  >
                    {editingProfileId ? '更新配置档' : '保存配置档'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border rounded-xl" data-testid="desktop-workstation-probes">
        <CardHeader className="pb-3">
          <CardTitle className={heading.card}>工作站状态探针</CardTitle>
          <CardDescription className={heading.muted}>
            {desktopClient ? '只读读取桌面运行时与治理状态，不上传业务数据' : '非桌面环境仅展示待接入状态'}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          <ProbeCell
            testId="workstation-probe-local-model"
            label="本地模型"
            value={
              !desktopClient
                ? '需桌面端'
                : probes.status === 'loading'
                  ? '检测中'
                  : probes.localModelAvailable
                    ? '可用'
                    : '未连接'
            }
            detail={
              probes.localModelAvailable
                ? `${probes.localModelCount} 个模型${probes.localModelUrl ? ` · ${probes.localModelUrl}` : ''}`
                : 'Ollama / 本地兼容端点'
            }
          />
          <ProbeCell
            testId="workstation-probe-knowledge"
            label="独立知识库"
            value={getServiceProbeValue(desktopClient, probes.knowledgeStatus, `${probes.knowledgeBaseTotal} 个库`)}
            detail={getServiceProbeDetail(
              probes.knowledgeStatus,
              `${probes.knowledgeDocumentCount} 份文档，按组织权限只读`,
              '绝密模式不读取数据网络状态',
              '知识库索引状态'
            )}
          />
          <ProbeCell
            testId="workstation-probe-mcp"
            label="Skills / MCP"
            value={getServiceProbeValue(desktopClient, probes.mcpStatus, `${probes.mcpServerCount} 个服务`)}
            detail={getServiceProbeDetail(
              probes.mcpStatus,
              `${probes.mcpEnabledCount} 个启用 · ${probes.mcpToolCount} 个工具缓存`,
              '绝密模式不读取 MCP 管理状态',
              '服务治理状态'
            )}
          />
          <ProbeCell
            testId="workstation-probe-offline-queue"
            label="离线任务队列"
            value={
              !desktopClient
                ? '需桌面端'
                : probes.status === 'loading'
                  ? '检测中'
                  : `${probes.queueTotal} 条`
            }
            detail={probes.queueFailed > 0 ? `${probes.queueFailed} 条失败需处理` : '本地队列统计只读'}
          />
          <ProbeCell
            testId="workstation-probe-remote-control"
            label="移动远控安全闸"
            value={mode === 'top-secret' ? '已阻断' : desktopClient ? '待验收' : '需桌面端'}
            detail={mode === 'top-secret' ? '绝密模式禁止远控出站' : '需配对、确认、撤销和审计证据'}
          />
        </CardContent>
      </Card>

      <Card className="border-border rounded-xl">
        <CardHeader className="pb-3">
          <CardTitle className={heading.card}>发布缺口</CardTitle>
          <CardDescription className={heading.muted}>
            工作站入口只展示已落地或可治理的能力，未完成项继续保留阻断状态
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {[
            { label: '签名包运行时', value: '待签名/公证证据' },
            { label: '移动远控', value: '待设备配对验收' },
            { label: 'Skills 进化', value: '待评测/审批/回滚闭环' },
          ].map((item) => (
            <div key={item.label} className="rounded-lg border border-dashed border-border bg-muted/30 p-3">
              <p className="text-sm font-medium text-foreground">{item.label}</p>
              <p className="mt-1 text-xs text-muted-foreground">{item.value}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function getServiceProbeValue(desktopClient: boolean, status: ServiceProbeStatus, readyValue: string) {
  if (!desktopClient) return '需桌面端'
  if (status === 'preview') return '待接入'
  if (status === 'loading') return '检测中'
  if (status === 'skipped') return '已阻断'
  if (status === 'error') return '读取失败'
  return readyValue
}

function getServiceProbeDetail(
  status: ServiceProbeStatus,
  readyDetail: string,
  skippedDetail: string,
  defaultDetail: string
) {
  if (status === 'skipped') return skippedDetail
  if (status === 'error') return `${defaultDetail}读取失败`
  if (status === 'ready') return readyDetail
  return `${defaultDetail}只读读取`
}

function ProbeCell({
  testId,
  label,
  value,
  detail,
}: {
  testId: string
  label: string
  value: string
  detail: string
}) {
  return (
    <div data-testid={testId} className="rounded-lg border border-border bg-surface-1 p-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 text-sm font-semibold text-foreground">{value}</p>
      <p className="mt-1 break-words text-xs text-muted-foreground">{detail}</p>
    </div>
  )
}
