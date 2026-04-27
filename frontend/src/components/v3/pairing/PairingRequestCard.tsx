/**
 * PairingRequestCard — 待审核的配对请求卡片
 *
 * 卡片要素:渠道图标 + 用户名 + 渠道来源 + 创建时间 + 倒计时 + 批准/驳回。
 * 倒计时通过父组件下发的 `nowMs` 触发(避免每秒自身重渲)。
 */

import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

import type { ChannelType, PairingRequest } from '@/lib/api/imPairing'
import { useImPairingStore } from '@/lib/store/imPairingStore'

import { CountdownBadge } from './CountdownBadge'
import { RejectDialog } from './RejectDialog'

interface PairingRequestCardProps {
  request: PairingRequest
  /** 由父组件 tick 提供的"当前时间",驱动倒计时 */
  nowMs: number
}

const CHANNEL_META: Record<ChannelType, { emoji: string; label: string; bg: string }> = {
  feishu: { emoji: '飞', label: '飞书', bg: 'bg-blue-100 dark:bg-blue-500/15' },
  wechat: { emoji: '微', label: '企业微信', bg: 'bg-emerald-100 dark:bg-emerald-500/15' },
  dingtalk: { emoji: '钉', label: '钉钉', bg: 'bg-sky-100 dark:bg-sky-500/15' },
  telegram: { emoji: 'T', label: 'Telegram', bg: 'bg-cyan-100 dark:bg-cyan-500/15' },
  discord: { emoji: 'D', label: 'Discord', bg: 'bg-indigo-100 dark:bg-indigo-500/15' },
}

function relativeTime(iso: string, nowMs: number): string {
  const diff = nowMs - new Date(iso).getTime()
  if (diff < 60_000) return '刚刚发起'
  const min = Math.floor(diff / 60_000)
  if (min < 60) return `${min} 分钟前发起`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前发起`
  return `${new Date(iso).toLocaleDateString('zh-CN')} 发起`
}

export function PairingRequestCard({ request, nowMs }: PairingRequestCardProps) {
  const approve = useImPairingStore((s) => s.approve)
  const reject = useImPairingStore((s) => s.reject)

  const [submitting, setSubmitting] = useState(false)
  const [rejectOpen, setRejectOpen] = useState(false)

  const meta = CHANNEL_META[request.channel_type] ?? {
    emoji: '?',
    label: request.channel_type,
    bg: 'bg-muted',
  }

  const handleApprove = async () => {
    setSubmitting(true)
    try {
      await approve(request.id)
      toast.success(`已批准 ${request.external_user_name}`)
    } catch (e) {
      toast.error(`批准失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  const handleReject = async (reason: string) => {
    setSubmitting(true)
    try {
      await reject(request.id, reason)
      toast.success(`已驳回 ${request.external_user_name}`)
    } catch (e) {
      toast.error(`驳回失败: ${e instanceof Error ? e.message : '未知错误'}`)
      throw e // 让弹窗保持打开
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <Card className="p-4">
        <div className="flex items-start gap-3">
          <div
            className={`flex size-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-foreground ${meta.bg}`}
            aria-label={meta.label}
          >
            {meta.emoji}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-medium text-foreground">
                  {request.external_user_name}
                </h3>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                  <span className="truncate">
                    {meta.label} · {request.channel_name}
                  </span>
                  {request.external_group_name && (
                    <>
                      <span aria-hidden>·</span>
                      <span className="truncate">群「{request.external_group_name}」</span>
                    </>
                  )}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {relativeTime(request.created_at, nowMs)}
                </p>
              </div>
              <CountdownBadge expiresAt={request.expires_at} nowMs={nowMs} />
            </div>

            <div className="mt-3 flex gap-2">
              <Button size="sm" disabled={submitting} onClick={handleApprove}>
                批准
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={submitting}
                onClick={() => setRejectOpen(true)}
              >
                驳回
              </Button>
            </div>
          </div>
        </div>
      </Card>

      <RejectDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        targetName={request.external_user_name}
        onConfirm={handleReject}
      />
    </>
  )
}
