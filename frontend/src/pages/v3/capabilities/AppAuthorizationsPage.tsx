/**
 * AppAuthorizationsPage — V3 应用授权（P4-F 真业务化）
 *
 * 参考 Accio Work "应用授权" 页布局：
 *   - 顶部标题 + 副标题 + 已连接计数
 *   - 搜索框 + 分类 Tab（全部 / 8 大分类）
 *   - 卡片网格（响应式 1/2/3/4 列）
 *   - 已连接 provider 在所属分类内置顶
 *   - 空状态提示
 *   - "添加账户" → ConnectDialog；"断开" → DisconnectDialog
 */

import { useEffect, useMemo, useState } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'

import { AppCard } from '@/components/v3/apps/AppCard'
import { AppCategoryTabs } from '@/components/v3/apps/AppCategoryTabs'
import { AppSearchBox } from '@/components/v3/apps/AppSearchBox'
import { ConnectDialog } from '@/components/v3/apps/ConnectDialog'
import { DisconnectDialog } from '@/components/v3/apps/DisconnectDialog'

import type { AppAuthorization, AppProvider } from '@/lib/api/appAuthorizations'
import { useAppAuthorizationsStore } from '@/lib/store/appAuthorizationsStore'

export default function AppAuthorizationsPage() {
  const providers = useAppAuthorizationsStore((s) => s.providers)
  const authorizations = useAppAuthorizationsStore((s) => s.authorizations)
  const searchQuery = useAppAuthorizationsStore((s) => s.searchQuery)
  const selectedCategory = useAppAuthorizationsStore((s) => s.selectedCategory)
  const providersLoading = useAppAuthorizationsStore((s) => s.providersLoading)
  const authorizationsLoading = useAppAuthorizationsStore((s) => s.authorizationsLoading)
  const loadError = useAppAuthorizationsStore((s) => s.loadError)

  const loadProviders = useAppAuthorizationsStore((s) => s.loadProviders)
  const loadAuthorizations = useAppAuthorizationsStore((s) => s.loadAuthorizations)
  const setSearch = useAppAuthorizationsStore((s) => s.setSearch)
  const setCategory = useAppAuthorizationsStore((s) => s.setCategory)
  const refresh = useAppAuthorizationsStore((s) => s.refresh)
  const getFilteredProviders = useAppAuthorizationsStore((s) => s.getFilteredProviders)
  const getAuthorizationFor = useAppAuthorizationsStore((s) => s.getAuthorizationFor)

  const [connectTarget, setConnectTarget] = useState<AppProvider | null>(null)
  const [disconnectTarget, setDisconnectTarget] = useState<{
    provider: AppProvider
    authorization: AppAuthorization
  } | null>(null)

  // mount 时并发加载 providers + authorizations
  useEffect(() => {
    Promise.all([loadProviders(), loadAuthorizations()]).catch(() => {
      // store 内已记录 loadError
    })
  }, [loadProviders, loadAuthorizations])

  // 已连接置顶的过滤+排序结果
  // 注：依赖 providers/authorizations/searchQuery/selectedCategory 触发重算
  const sortedProviders = useMemo(() => {
    const list = getFilteredProviders()
    const connectedIds = new Set(
      authorizations.filter((a) => a.status === 'connected').map((a) => a.provider_id),
    )
    return [...list].sort((a, b) => {
      const ac = connectedIds.has(a.provider_id) ? 0 : 1
      const bc = connectedIds.has(b.provider_id) ? 0 : 1
      if (ac !== bc) return ac - bc
      return a.display_name.localeCompare(b.display_name, 'zh-Hans-CN')
    })
  }, [
    providers,
    authorizations,
    searchQuery,
    selectedCategory,
    getFilteredProviders,
  ])

  const connectedCount = authorizations.filter((a) => a.status === 'connected').length

  const handleRefresh = async (
    _provider: AppProvider,
    auth: AppAuthorization,
  ) => {
    try {
      await refresh(auth.id)
      toast.success('令牌已刷新')
    } catch (e) {
      toast.error(`刷新失败：${e instanceof Error ? e.message : '未知错误'}`)
    }
  }

  const reload = () => {
    Promise.all([loadProviders(), loadAuthorizations()])
  }

  const loading = providersLoading || authorizationsLoading
  const isEmptyResult = !loading && sortedProviders.length === 0 && providers.length > 0

  return (
    <div className="mx-auto flex h-full max-w-7xl flex-col gap-5 p-6">
      {/* 顶栏 */}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <icons.KeyRound className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              应用授权
            </h1>
            <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
              授权第三方平台，让安心智能助手代替你访问数据。授权可随时断开撤销。
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={reload}
          disabled={loading}
        >
          <icons.RefreshCcw className={loading ? 'animate-spin' : ''} />
          刷新
        </Button>
      </header>

      {/* 计数 */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 font-medium text-foreground">
          {providers.length} 个应用
        </span>
        <span>· 当前已授权 {connectedCount} 个</span>
      </div>

      {/* 错误提示 */}
      {loadError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
          加载失败: {loadError}
        </div>
      )}

      {/* 搜索 + 分类 */}
      <div className="flex flex-col gap-3">
        <AppSearchBox value={searchQuery} onChange={setSearch} />
        <AppCategoryTabs
          providers={providers}
          value={selectedCategory}
          onChange={setCategory}
        />
      </div>

      {/* 网格 / 空状态 */}
      {loading && providers.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border/60 p-10 text-center text-sm text-muted-foreground">
          正在加载应用列表...
        </div>
      ) : isEmptyResult ? (
        <div className="rounded-lg border border-dashed border-border/60 p-10 text-center text-sm text-muted-foreground">
          没有匹配的应用 — 尝试切换分类或修改搜索词
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {sortedProviders.map((p) => (
            <AppCard
              key={p.provider_id}
              provider={p}
              authorization={getAuthorizationFor(p.provider_id)}
              onConnect={(provider) => setConnectTarget(provider)}
              onDisconnect={(provider, authorization) =>
                setDisconnectTarget({ provider, authorization })
              }
              onRefresh={handleRefresh}
            />
          ))}
        </div>
      )}

      {/* 弹窗：添加账户 */}
      <ConnectDialog
        open={!!connectTarget}
        onOpenChange={(open) => {
          if (!open) setConnectTarget(null)
        }}
        provider={connectTarget}
      />

      {/* 弹窗：断开授权 */}
      <DisconnectDialog
        open={!!disconnectTarget}
        onOpenChange={(open) => {
          if (!open) setDisconnectTarget(null)
        }}
        provider={disconnectTarget?.provider ?? null}
        authorization={disconnectTarget?.authorization ?? null}
      />
    </div>
  )
}
