/**
 * ConnectDialog — "添加账户"弹窗（模拟 OAuth 授权流）
 *
 * 真实生产：点击"去授权"应跳转 startConnect 返回的 authorize_url。
 * Mock 模式 (VITE_APP_AUTH_MOCK=true)：不跳转，倒计时 2 秒后调用
 * `useAppAuthorizationsStore.completeMockConnect(providerId)` 模拟 callback 回写，
 * 让前端授权流程在无后端时也能整体跑通。
 */

import { useEffect, useState } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import type { AppProvider } from '@/lib/api/appAuthorizations'
import { useAppAuthorizationsStore } from '@/lib/store/appAuthorizationsStore'

const USE_MOCK = import.meta.env.VITE_APP_AUTH_MOCK === 'true'

type Phase = 'idle' | 'starting' | 'redirecting' | 'success' | 'error'

interface ConnectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  provider: AppProvider | null
}

export function ConnectDialog({ open, onOpenChange, provider }: ConnectDialogProps) {
  const startConnect = useAppAuthorizationsStore((s) => s.startConnect)
  const completeMockConnect = useAppAuthorizationsStore((s) => s.completeMockConnect)

  const [phase, setPhase] = useState<Phase>('idle')
  const [countdown, setCountdown] = useState(2)
  const [errMsg, setErrMsg] = useState<string | null>(null)

  // 弹窗每次打开重置状态
  useEffect(() => {
    if (open) {
      setPhase('idle')
      setCountdown(2)
      setErrMsg(null)
    }
  }, [open])

  // mock 模式倒计时
  useEffect(() => {
    if (phase !== 'redirecting' || !USE_MOCK || !provider) return
    if (countdown <= 0) {
      // 倒计时结束，模拟 callback 回写
      completeMockConnect(provider.provider_id)
        .then(() => {
          setPhase('success')
          toast.success(`已连接 ${provider.display_name}`)
        })
        .catch((e: unknown) => {
          setPhase('error')
          setErrMsg(e instanceof Error ? e.message : '未知错误')
        })
      return
    }
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [phase, countdown, provider, completeMockConnect])

  if (!provider) return null

  const handleAuthorize = async () => {
    setPhase('starting')
    setErrMsg(null)
    try {
      const { authorize_url } = await startConnect(provider.provider_id)
      if (USE_MOCK) {
        // 不跳转，进入倒计时
        setPhase('redirecting')
        setCountdown(2)
      } else {
        // 真实环境：跳转到授权 URL
        setPhase('redirecting')
        window.location.assign(authorize_url)
      }
    } catch (e) {
      setPhase('error')
      setErrMsg(e instanceof Error ? e.message : '授权启动失败')
    }
  }

  const handleClose = () => onOpenChange(false)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            添加账户 · {provider.display_name}
          </DialogTitle>
          <DialogDescription>{provider.description}</DialogDescription>
        </DialogHeader>

        {/* 权限范围 */}
        <div className="space-y-3">
          <div>
            <p className="mb-1.5 text-xs font-medium text-foreground">将申请以下权限：</p>
            <ul className="space-y-1 rounded-md border border-border/60 bg-muted/30 p-2.5">
              {provider.default_scopes.length === 0 ? (
                <li className="text-[11px] text-muted-foreground">（默认权限集）</li>
              ) : (
                provider.default_scopes.map((s) => (
                  <li
                    key={s}
                    className="flex items-center gap-1.5 text-[11px] text-foreground/80"
                  >
                    <span className="size-1 rounded-full bg-primary/60" />
                    <code className="font-mono">{s}</code>
                  </li>
                ))
              )}
            </ul>
          </div>

          {/* 风险提示 */}
          <div className="flex gap-2 rounded-md border border-amber-200/70 bg-amber-50/60 p-2.5 text-[11px] text-amber-800 dark:border-amber-900/50 dark:bg-amber-500/10 dark:text-amber-300">
            <icons.ShieldAlert className="mt-0.5 size-3.5 shrink-0" />
            <p>
              授权后，安心智能助手将以你的身份代访问 {provider.display_name} 数据。可随时在本页面断开授权撤销访问。
            </p>
          </div>

          {/* 阶段反馈 */}
          {phase === 'redirecting' && USE_MOCK && (
            <div className="flex items-center gap-2 rounded-md border border-blue-200/70 bg-blue-50/60 p-2.5 text-[11px] text-blue-800 dark:border-blue-900/50 dark:bg-blue-500/10 dark:text-blue-300">
              <icons.Loader2 className="size-3.5 animate-spin" />
              <span>
                模拟 OAuth 跳转中... {countdown > 0 ? `${countdown}s 后回写授权` : '处理中'}
              </span>
            </div>
          )}
          {phase === 'redirecting' && !USE_MOCK && (
            <div className="flex items-center gap-2 rounded-md border border-blue-200/70 bg-blue-50/60 p-2.5 text-[11px] text-blue-800 dark:border-blue-900/50 dark:bg-blue-500/10 dark:text-blue-300">
              <icons.ExternalLink className="size-3.5" />
              <span>正在跳转到授权页面...</span>
            </div>
          )}
          {phase === 'success' && (
            <div className="flex items-center gap-2 rounded-md border border-emerald-200/70 bg-emerald-50/60 p-2.5 text-[11px] text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-500/10 dark:text-emerald-300">
              <icons.CheckCircle2 className="size-3.5" />
              <span>已成功连接 {provider.display_name}</span>
            </div>
          )}
          {phase === 'error' && errMsg && (
            <div className="rounded-md border border-red-200/70 bg-red-50/60 p-2.5 text-[11px] text-red-800 dark:border-red-900/50 dark:bg-red-500/10 dark:text-red-300">
              错误：{errMsg}
            </div>
          )}
        </div>

        <DialogFooter>
          {phase === 'success' ? (
            <Button onClick={handleClose}>完成</Button>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={phase === 'starting' || phase === 'redirecting'}
              >
                取消
              </Button>
              <Button
                onClick={handleAuthorize}
                disabled={phase === 'starting' || phase === 'redirecting'}
              >
                {phase === 'starting' && <icons.Loader2 className="size-3.5 animate-spin" />}
                {phase === 'idle' && '去授权'}
                {phase === 'starting' && '准备中...'}
                {phase === 'redirecting' && '处理中...'}
                {phase === 'error' && '重试'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
