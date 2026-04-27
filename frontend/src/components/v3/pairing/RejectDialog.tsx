/**
 * RejectDialog — 驳回配对请求时的理由输入弹窗
 */

import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'

interface RejectDialogProps {
  open: boolean
  /** 受控关闭 */
  onOpenChange: (open: boolean) => void
  /** 用于在弹窗标题上展示被驳回的对象 */
  targetName?: string
  /** 提交回调,父组件负责 toast / store 更新 */
  onConfirm: (reason: string) => Promise<void>
}

export function RejectDialog({
  open,
  onOpenChange,
  targetName,
  onConfirm,
}: RejectDialogProps) {
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // 每次重新打开时清理输入
  useEffect(() => {
    if (open) {
      setReason('')
      setSubmitting(false)
    }
  }, [open])

  const handleSubmit = async () => {
    const trimmed = reason.trim()
    if (!trimmed) return
    setSubmitting(true)
    try {
      await onConfirm(trimmed)
      onOpenChange(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>驳回配对请求</DialogTitle>
          <DialogDescription>
            {targetName
              ? `请填写驳回 "${targetName}" 的理由,理由会同步给申请人。`
              : '请填写驳回理由,理由会同步给申请人。'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground">驳回理由 *</label>
          <Textarea
            placeholder="例如:暂未通过身份核验 / 该 IM 渠道不在授权范围"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={4}
            disabled={submitting}
            maxLength={200}
          />
          <p className="text-right text-[10px] text-muted-foreground">
            {reason.length}/200
          </p>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            取消
          </Button>
          <Button
            variant="destructive"
            onClick={handleSubmit}
            disabled={submitting || !reason.trim()}
          >
            {submitting ? '提交中...' : '确认驳回'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
