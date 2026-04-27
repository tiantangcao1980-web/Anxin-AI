/**
 * AppCard — 单个 provider 卡片
 *
 * 顶部：图标（icon_url，加载失败 fallback 首字母）+ 名称 + 状态徽章
 * 中部：一句话描述
 * 底部：账号标签（已连接时）+ 操作按钮（"+ 添加账户" / "已连接 ✓"）
 */

import { useState } from 'react'
import { Check, ExternalLink, Plus, RefreshCw, Unplug } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/components/ui/utils'

import type { AppAuthorization, AppProvider } from '@/lib/api/appAuthorizations'

import { ConnectedBadge } from './ConnectedBadge'

interface AppCardProps {
  provider: AppProvider
  authorization: AppAuthorization | null
  onConnect: (provider: AppProvider) => void
  onDisconnect: (provider: AppProvider, auth: AppAuthorization) => void
  onRefresh?: (provider: AppProvider, auth: AppAuthorization) => void
}

export function AppCard({
  provider,
  authorization,
  onConnect,
  onDisconnect,
  onRefresh,
}: AppCardProps) {
  const isConnected = authorization?.status === 'connected'
  const status = authorization?.status ?? 'none'
  const [iconError, setIconError] = useState(false)

  const initial = provider.display_name.trim().charAt(0).toUpperCase()

  return (
    <Card
      className={cn(
        'group flex h-full flex-col gap-3 p-4 transition-all',
        'hover:border-primary/40 hover:shadow-sm',
        isConnected && 'border-emerald-300/50 dark:border-emerald-700/40',
      )}
    >
      {/* 顶部：图标 + 名 + 状态 */}
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-xl',
            'bg-muted/60 ring-1 ring-border/50',
          )}
          aria-label={provider.display_name}
        >
          {provider.icon_url && !iconError ? (
            <img
              src={provider.icon_url}
              alt={provider.display_name}
              className="size-7 object-contain"
              onError={() => setIconError(true)}
              loading="lazy"
            />
          ) : (
            <span className="text-base font-semibold text-muted-foreground">
              {initial}
            </span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h3 className="truncate text-sm font-semibold text-foreground">
              {provider.display_name}
            </h3>
            <ConnectedBadge status={status} className="shrink-0" />
          </div>
          {provider.documentation_url && (
            <a
              href={provider.documentation_url}
              target="_blank"
              rel="noreferrer"
              className="mt-0.5 inline-flex items-center gap-0.5 text-[10px] text-muted-foreground transition-colors hover:text-primary"
              onClick={(e) => e.stopPropagation()}
            >
              开发者文档
              <ExternalLink className="size-2.5" />
            </a>
          )}
        </div>
      </div>

      {/* 描述 */}
      <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {provider.description}
      </p>

      {/* 已连接时显示账号标签 */}
      {isConnected && authorization?.account_label && (
        <div className="rounded-md bg-muted/40 px-2.5 py-1.5 text-[11px] text-muted-foreground">
          <span className="text-foreground/70">账号：</span>
          <span className="font-medium text-foreground">{authorization.account_label}</span>
        </div>
      )}

      {/* 底部：操作 */}
      <div className="mt-auto flex items-center justify-between gap-2 pt-1">
        {isConnected ? (
          <>
            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400">
              <Check className="size-3" />
              已连接
            </span>
            <div className="flex items-center gap-1">
              {onRefresh && authorization && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => onRefresh(provider, authorization)}
                  title="刷新令牌"
                >
                  <RefreshCw className="size-3" />
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                className="h-7 px-2 text-xs text-muted-foreground hover:text-red-600"
                onClick={() => authorization && onDisconnect(provider, authorization)}
              >
                <Unplug className="size-3" />
                断开
              </Button>
            </div>
          </>
        ) : (
          <Button
            variant="default"
            size="sm"
            className="ml-auto h-7 px-3 text-xs"
            onClick={() => onConnect(provider)}
          >
            <Plus className="size-3" />
            添加账户
          </Button>
        )}
      </div>
    </Card>
  )
}
