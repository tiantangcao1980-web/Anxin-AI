/**
 * TaskApprovalCard — needs_approval 状态下的审批面板
 */

import { useState } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

import type { AgentTask } from '@/lib/api/agentTasks'
import { useAgentTasksStore } from '@/lib/store/agentTasksStore'

interface TaskApprovalCardProps {
  task: AgentTask
}

export function TaskApprovalCard({ task }: TaskApprovalCardProps) {
  const approveTask = useAgentTasksStore((s) => s.approveTask)
  const rejectTask = useAgentTasksStore((s) => s.rejectTask)

  const [submitting, setSubmitting] = useState(false)
  const [showReject, setShowReject] = useState(false)
  const [reason, setReason] = useState('')

  if (task.status !== 'needs_approval') return null

  const description =
    (typeof task.payload?.approval_description === 'string'
      ? task.payload.approval_description
      : null) ??
    (typeof task.payload?.user_input === 'string' ? task.payload.user_input : null) ??
    '该任务在执行过程中需要您的审批后继续。'

  const handleApprove = async () => {
    setSubmitting(true)
    try {
      await approveTask(task.id)
      toast.success('已批准,任务继续执行')
    } catch (e) {
      toast.error(`批准失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!reason.trim()) {
      toast.error('请填写驳回理由')
      return
    }
    setSubmitting(true)
    try {
      await rejectTask(task.id, reason.trim())
      toast.success('已驳回')
      setShowReject(false)
      setReason('')
    } catch (e) {
      toast.error(`驳回失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-900/60 dark:bg-amber-500/10">
      <div className="flex items-start gap-3">
        <icons.AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-600 dark:text-amber-400" />
        <div className="flex-1 space-y-3">
          <div>
            <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-100">
              需要您的审批
            </h4>
            <p className="mt-1 text-sm leading-relaxed text-amber-900/80 dark:text-amber-100/80">
              {description}
            </p>
          </div>

          {!showReject ? (
            <div className="flex gap-2">
              <Button size="sm" disabled={submitting} onClick={handleApprove}>
                批准
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={submitting}
                onClick={() => setShowReject(true)}
              >
                驳回
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <Textarea
                placeholder="请输入驳回理由(必填)"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                disabled={submitting}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={submitting || !reason.trim()}
                  onClick={handleReject}
                >
                  确认驳回
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={submitting}
                  onClick={() => {
                    setShowReject(false)
                    setReason('')
                  }}
                >
                  取消
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
