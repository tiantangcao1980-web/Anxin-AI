import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAppModeStore } from '@/lib/store'
import { isTauri } from '@/lib/tauri-bridge'
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

export function DesktopWorkstationPanel() {
  const navigate = useNavigate()
  const mode = useAppModeStore((state) => state.mode)
  const desktopClient = isTauri()
  const resources = useMemo(
    () => buildDesktopWorkstationResources(mode, desktopClient ? 'desktop' : 'preview'),
    [desktopClient, mode]
  )

  return (
    <div className="space-y-4">
      <Card className="border-border rounded-xl">
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className={heading.section}>桌面主工作站</CardTitle>
              <CardDescription className={heading.muted}>
                {desktopClient ? '当前客户端能力状态' : '桌面能力预览，完整本地能力须在桌面客户端启用'}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
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
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {resources.map((resource) => {
              const ResourceIcon = RESOURCE_ICON[resource.id]
              return (
                <div
                  key={resource.id}
                  className="flex min-h-[142px] flex-col justify-between rounded-lg border border-border bg-surface-1 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="rounded-lg bg-muted p-2 text-muted-foreground">
                        <ResourceIcon className={iconSize.md} />
                      </div>
                      <div>
                        <h3 className={heading.card}>{resource.title}</h3>
                        <p className="mt-1 text-sm text-muted-foreground">{resource.summary}</p>
                      </div>
                    </div>
                    <span className={`shrink-0 rounded px-2 py-1 text-xs font-medium ${STATUS_CLASS[resource.status]}`}>
                      {resource.statusLabel}
                    </span>
                  </div>
                  <div className="mt-4 flex items-center justify-between gap-3">
                    <span className="text-xs text-muted-foreground">
                      {resource.action.disabledReason ?? '策略已就绪'}
                    </span>
                    <Button
                      size="sm"
                      variant={resource.action.enabled ? 'outline' : 'ghost'}
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
