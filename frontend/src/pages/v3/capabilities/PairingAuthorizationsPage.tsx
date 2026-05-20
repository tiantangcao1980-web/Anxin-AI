/**
 * PairingAuthorizationsPage — V3 配对授权(P3-D 真业务化)
 *
 * 双段:
 *   - 待审核(24h 有效的 PairingRequest 列表)
 *   - 已授权(IMBinding 列表)
 *
 * 数据流:
 *   - mount 时并行 loadPending + loadAuthorized
 *   - 5s tick 一次"当前时间",仅触发倒计时显示更新(不重复请求接口);
 *     数据本身按 30s 拉一次最新 pending(防止过期请求残留)
 */

import { useEffect, useMemo, useState } from 'react'
import { icons } from '@/lib/icons'
import { Button } from '@/components/ui/button'

import { BindingRow } from '@/components/v3/pairing/BindingRow'
import { EmptyState } from '@/components/v3/pairing/EmptyState'
import { PairingRequestCard } from '@/components/v3/pairing/PairingRequestCard'

import { useImPairingStore } from '@/lib/store/imPairingStore'

const COUNTDOWN_TICK_MS = 5_000
const PENDING_REFRESH_MS = 30_000

export default function PairingAuthorizationsPage() {
  const pendingRequests = useImPairingStore((s) => s.pendingRequests)
  const bindings = useImPairingStore((s) => s.bindings)
  const pendingLoading = useImPairingStore((s) => s.pendingLoading)
  const authorizedLoading = useImPairingStore((s) => s.authorizedLoading)
  const pendingError = useImPairingStore((s) => s.pendingError)
  const authorizedError = useImPairingStore((s) => s.authorizedError)
  const loadPending = useImPairingStore((s) => s.loadPending)
  const loadAuthorized = useImPairingStore((s) => s.loadAuthorized)

  // 当前时间 tick:每 5s 更新一次,驱动倒计时显示
  // (page 级单一定时器,所有 RequestCard 共享同一 nowMs prop —— 避免每个卡片
  //  各自 setInterval 造成 N 个定时器 + 每秒重渲)
  const [nowMs, setNowMs] = useState(() => Date.now())

  // 初始加载
  useEffect(() => {
    loadPending()
    loadAuthorized()
  }, [loadPending, loadAuthorized])

  // 倒计时 tick(轻量,只 setState 一个 number)
  useEffect(() => {
    const t = window.setInterval(() => setNowMs(Date.now()), COUNTDOWN_TICK_MS)
    return () => window.clearInterval(t)
  }, [])

  // 周期性重载 pending(防止过期请求滞留 / 后端新增请求)
  useEffect(() => {
    const t = window.setInterval(() => {
      loadPending()
    }, PENDING_REFRESH_MS)
    return () => window.clearInterval(t)
  }, [loadPending])

  // 客户端再过滤一遍未过期(后端可能尚未清理)
  const visiblePending = useMemo(
    () =>
      pendingRequests.filter((p) => new Date(p.expires_at).getTime() > nowMs),
    [pendingRequests, nowMs],
  )

  const handleRefresh = () => {
    loadPending()
    loadAuthorized()
  }

  const isRefreshing = pendingLoading || authorizedLoading

  return (
    <div className="mx-auto flex h-full max-w-4xl flex-col gap-8 p-6">
      {/* 顶栏 */}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">配对授权</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            管理者可以通过 IM 渠道与你的智能体互动,指挥智能体工作。
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <icons.RefreshCcw className={isRefreshing ? 'animate-spin' : ''} />
          刷新
        </Button>
      </header>

      {/* ===== 待审核 ===== */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground">待审核</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            仅展示 24 小时内有效的配对请求
          </p>
        </div>

        {pendingError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
            加载待审请求失败: {pendingError}
          </div>
        )}

        {pendingLoading && pendingRequests.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border/60 px-6 py-8 text-center text-xs text-muted-foreground">
            正在加载...
          </div>
        ) : visiblePending.length === 0 ? (
          <EmptyState
            icon={icons.Inbox}
            title="暂无待审请求"
            description="当有人通过 IM 渠道请求与你的智能体配对时,请求将出现在这里。"
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {visiblePending.map((req) => (
              <PairingRequestCard key={req.id} request={req} nowMs={nowMs} />
            ))}
          </div>
        )}
      </section>

      {/* ===== 已授权 ===== */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground">已授权</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            已授权用户可通过 IM 渠道与智能体互动,并触发审核智能体的敏感操作
          </p>
        </div>

        {authorizedError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
            加载已授权列表失败: {authorizedError}
          </div>
        )}

        {authorizedLoading && bindings.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border/60 px-6 py-8 text-center text-xs text-muted-foreground">
            正在加载...
          </div>
        ) : bindings.length === 0 ? (
          <EmptyState
            icon={icons.Users}
            title="无已授权用户"
            description="你授权配对请求后,用户将显示在此处。"
          />
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <icons.ShieldCheck className="size-3" />
              共 {bindings.length} 位已授权用户
            </div>
            {bindings.map((b) => (
              <BindingRow key={b.id} binding={b} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
