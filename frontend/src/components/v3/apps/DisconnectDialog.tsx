/**
 * DisconnectDialog — 断开授权二次确认
 */

import { useState } from 'react'
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

import type { AppAuthorization, AppProvider } from '@/lib/api/appAuthorizations'
import { useAppAuthorizationsStore } from '@/lib/store/appAuthorizationsStore'

interface DisconnectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  provider: AppProvider | null
  authorization: AppAuthorization | null
}

export function DisconnectDialog({
  open,
  onOpenChange,
  provider,
  authorization,
}: DisconnectDialogProps) {
  const disconnect = useAppAuthorizationsStore((s) => s.disconnect)
  const [submitting, setSubmitting] = useState(false)

  if (!provider || !authorization) return null

  const handleConfirm = async () => {
    setSubmitting(true)
    try {
      await disconnect(authorization.id)
      toast.success(`已断开 ${provider.display_name} 授权`)
      onOpenChange(false)
    } catch (e) {
      toast.error(`断开失败：${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <icons.AlertTriangle className="size-4 text-amber-500" />
            断开 {provider.display_name} 授权
          </DialogTitle>
          <DialogDescription>
            断开后，安心智能助手将立即失去对该应用的访问权限。
            {authorization.account_label && (
              <>
                {' '}
                当前账号：
                <span className="font-medium text-foreground">
                  {authorization.account_label}
                </span>
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border border-amber-200/70 bg-amber-50/60 p-3 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-500/10 dark:text-amber-300">
          <p className="font-medium">将影响以下能力：</p>
          <ul className="mt-1.5 list-disc space-y-0.5 pl-4">
            {authorization.scopes.length === 0 ? (
              <li>该应用所授予的全部权限</li>
            ) : (
              authorization.scopes.slice(0, 4).map((s) => (
                <li key={s}>
                  <code className="font-mono">{s}</code>
                </li>
              ))
            )}
            {authorization.scopes.length > 4 && (
              <li className="opacity-70">等共 {authorization.scopes.length} 项权限</li>
            )}
          </ul>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={submitting}
          >
            {submitting ? '断开中...' : '确认断开'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
