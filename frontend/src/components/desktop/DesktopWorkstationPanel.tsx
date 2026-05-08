import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { knowledgeApi, mcpApi } from '@/lib/api'
import { useAppModeStore } from '@/lib/store'
import { checkLocalLLMStatus, getQueueStats, isTauri, listLocalModels } from '@/lib/tauri-bridge'
import { heading, iconSize, statusBadge } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import {
  buildDesktopWorkstationResources,
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

export function DesktopWorkstationPanel() {
  const navigate = useNavigate()
  const mode = useAppModeStore((state) => state.mode)
  const desktopClient = isTauri()
  const [probes, setProbes] = useState<WorkstationProbeState>(PREVIEW_PROBES)
  const resources = useMemo(
    () => buildDesktopWorkstationResources(mode, desktopClient ? 'desktop' : 'preview'),
    [desktopClient, mode]
  )

  useEffect(() => {
    let cancelled = false

    if (!desktopClient) {
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

    Promise.allSettled([
      checkLocalLLMStatus(),
      listLocalModels(),
      getQueueStats(),
      mode === 'top-secret' ? Promise.resolve(null) : knowledgeApi.listBases({ page_size: 100 }),
      mode === 'top-secret' ? Promise.resolve(null) : mcpApi.listServers(),
    ]).then(([llmResult, modelsResult, queueResult, knowledgeResult, mcpResult]) => {
      if (cancelled) return

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
  }, [desktopClient, mode])

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
