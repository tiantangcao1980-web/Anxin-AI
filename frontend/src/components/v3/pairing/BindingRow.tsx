/**
 * BindingRow — 已授权 IM 绑定的列表行
 *
 * 行要素:头像 + 用户名 + 渠道 + 授权时间 + 最近活跃 + 撤销按钮。
 */

import { useState } from 'react'
import { toast } from 'sonner'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

import type { ChannelType, IMBinding } from '@/lib/api/imPairing'
import { useImPairingStore } from '@/lib/store/imPairingStore'

interface BindingRowProps {
  binding: IMBinding
}

const CHANNEL_LABEL: Record<ChannelType, string> = {
  feishu: '飞书',
  wechat: '企业微信',
  dingtalk: '钉钉',
  telegram: 'Telegram',
  discord: 'Discord',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

function relativeActive(iso: string | null): string {
  if (!iso) return '尚未活跃'
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 60_000) return '刚刚活跃'
  const min = Math.floor(diff / 60_000)
  if (min < 60) return `${min} 分钟前活跃`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前活跃`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} 天前活跃`
  return `${formatDate(iso)} 活跃`
}

function initials(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return '?'
  return trimmed.slice(0, 1)
}

export function BindingRow({ binding }: BindingRowProps) {
  const revokeBinding = useImPairingStore((s) => s.revokeBinding)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const handleRevoke = async () => {
    setSubmitting(true)
    try {
      await revokeBinding(binding.id)
      toast.success(`已撤销 ${binding.external_user_name} 的授权`)
      setConfirmOpen(false)
    } catch (e) {
      toast.error(`撤销失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  const channelLabel = CHANNEL_LABEL[binding.channel_type] ?? binding.channel_type

  return (
    <>
      <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-card p-3 transition-colors hover:bg-muted/40">
        <Avatar className="size-9 shrink-0">
          {binding.external_user_avatar && (
            <AvatarImage src={binding.external_user_avatar} alt={binding.external_user_name} />
          )}
          <AvatarFallback className="bg-muted text-xs font-medium">
            {initials(binding.external_user_name)}
          </AvatarFallback>
        </Avatar>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-foreground">
              {binding.external_user_name}
            </p>
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              {channelLabel}
            </span>
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {binding.channel_name} · 授权于 {formatDate(binding.bound_at)} ·{' '}
            {relativeActive(binding.last_active_at)}
          </p>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-destructive"
          onClick={() => setConfirmOpen(true)}
        >
          撤销
        </Button>
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>撤销授权</AlertDialogTitle>
            <AlertDialogDescription>
              撤销后,「{binding.external_user_name}」将无法再通过{channelLabel}调用你的智能体。
              如需恢复,需对方重新发起配对请求。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={submitting}>取消</AlertDialogCancel>
            <AlertDialogAction
              disabled={submitting}
              onClick={(e) => {
                e.preventDefault()
                handleRevoke()
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {submitting ? '撤销中...' : '确认撤销'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
