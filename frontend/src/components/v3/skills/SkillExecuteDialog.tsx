/**
 * SkillExecuteDialog — 试运行弹窗
 *
 * 用户可在 Textarea 中编辑 JSON payload，提交后调用 executeSkill，
 * 把返回结果以 JSON pretty-print 展示。
 */

import { useEffect, useMemo, useState } from 'react'
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
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/components/ui/utils'

import type { Skill, SkillExecuteResult } from '@/lib/api/skills'
import { useSkillsStore } from '@/lib/store/skillsStore'

interface SkillExecuteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  skill: Skill | null
}

const DEFAULT_PAYLOAD = JSON.stringify({ input: '在此处填入测试输入' }, null, 2)

export function SkillExecuteDialog({
  open,
  onOpenChange,
  skill,
}: SkillExecuteDialogProps) {
  const executeSkill = useSkillsStore((s) => s.executeSkill)

  const [payloadText, setPayloadText] = useState<string>(DEFAULT_PAYLOAD)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<SkillExecuteResult | null>(null)

  // 重置状态当 skill 切换或弹窗关闭时
  useEffect(() => {
    if (!open) {
      setRunning(false)
      setResult(null)
    } else {
      setPayloadText(DEFAULT_PAYLOAD)
      setResult(null)
    }
  }, [open, skill?.name])

  const parseError = useMemo(() => {
    try {
      JSON.parse(payloadText)
      return null
    } catch (e) {
      return e instanceof Error ? e.message : 'JSON 格式错误'
    }
  }, [payloadText])

  const run = async () => {
    if (!skill) return
    if (parseError) return
    let payload: unknown
    try {
      payload = JSON.parse(payloadText)
    } catch {
      return
    }
    setRunning(true)
    setResult(null)
    try {
      const res = await executeSkill(skill.name, payload)
      setResult(res)
      if (res.ok) toast.success('试运行完成')
      else toast.error(`试运行失败：${res.error ?? '未知错误'}`)
    } catch (e) {
      toast.error(`调用失败：${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setRunning(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>试运行 · {skill?.display_name ?? '技能'}</DialogTitle>
          <DialogDescription>
            构造 JSON payload 并触发一次执行。结果将展示在下方（包含 trace_id /
            duration_ms）。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <label
              htmlFor="skill-payload"
              className="mb-1 block text-xs font-medium text-foreground"
            >
              Payload (JSON)
            </label>
            <Textarea
              id="skill-payload"
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              spellCheck={false}
              rows={8}
              className={cn(
                'font-mono text-xs',
                parseError && 'border-red-300 focus-visible:ring-red-200',
              )}
            />
            {parseError && (
              <p className="mt-1 flex items-center gap-1 text-[11px] text-red-600">
                <icons.XCircle className="size-3" />
                {parseError}
              </p>
            )}
          </div>

          {result && (
            <div
              className={cn(
                'space-y-1 rounded-md border p-3 text-xs',
                result.ok
                  ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-900/60 dark:bg-emerald-500/10'
                  : 'border-red-200 bg-red-50 dark:border-red-900/60 dark:bg-red-500/10',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={cn(
                    'inline-flex items-center gap-1 font-medium',
                    result.ok ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-700',
                  )}
                >
                  {result.ok ? (
                    <icons.CheckCircle2 className="size-3.5" />
                  ) : (
                    <icons.XCircle className="size-3.5" />
                  )}
                  {result.ok ? '成功' : '失败'}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {result.duration_ms} ms
                  {result.trace_id ? ` · ${result.trace_id}` : ''}
                </span>
              </div>
              <pre className="max-h-64 overflow-auto rounded bg-background/60 p-2 font-mono text-[11px]">
                {result.error
                  ? result.error
                  : JSON.stringify(result.output, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            关闭
          </Button>
          <Button onClick={run} disabled={!!parseError || running || !skill}>
            {running ? (
              <>
                <icons.Loader2 className="size-4 animate-spin" />
                运行中
              </>
            ) : (
              <>
                <icons.PlayCircle className="size-4" />
                运行
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
