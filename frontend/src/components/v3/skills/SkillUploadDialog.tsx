/**
 * SkillUploadDialog — 上传 SKILL.md 弹窗
 *
 * 1. 选择 .md 文件
 * 2. 本地解析 frontmatter（mock 同款轻量解析）做预览
 * 3. 用户确认 → uploadSkill → toast
 */

import { useState } from 'react'
import { CheckCircle2, FileText, Loader2, Upload, XCircle } from 'lucide-react'
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
import { cn } from '@/components/ui/utils'

import { useSkillsStore } from '@/lib/store/skillsStore'

interface SkillUploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface ParsedPreview {
  name: string
  display_name: string
  description: string
  category?: string
  type?: string
  triggers: string[]
  body_lines: number
  body_chars: number
}

function parsePreview(text: string, fallbackName: string): ParsedPreview {
  const fmMatch = text.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
  const meta: Record<string, string> = {}
  let body = text
  if (fmMatch) {
    body = fmMatch[2]
    fmMatch[1].split('\n').forEach((line) => {
      const m = line.match(/^([a-zA-Z_]+):\s*(.+)$/)
      if (m) meta[m[1]] = m[2].trim().replace(/^['"]|['"]$/g, '')
    })
  }
  return {
    name: meta.name || fallbackName,
    display_name: meta.display_name || meta.name || fallbackName,
    description: meta.description || '（未在 frontmatter 中提供 description）',
    category: meta.category,
    type: meta.type,
    triggers: (meta.triggers || '').split(',').map((s) => s.trim()).filter(Boolean),
    body_lines: body.split('\n').length,
    body_chars: body.length,
  }
}

export function SkillUploadDialog({ open, onOpenChange }: SkillUploadDialogProps) {
  const uploadSkill = useSkillsStore((s) => s.uploadSkill)

  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ParsedPreview | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const reset = () => {
    setFile(null)
    setPreview(null)
    setParseError(null)
    setSubmitting(false)
  }

  const handleFile = async (f: File) => {
    setFile(f)
    setParseError(null)
    if (!f.name.endsWith('.md') && !f.name.endsWith('.markdown')) {
      setParseError('仅支持 .md / .markdown 文件')
      setPreview(null)
      return
    }
    try {
      const text = await f.text()
      const fallback = `uploaded/${f.name.replace(/\.md$/, '')}`
      setPreview(parsePreview(text, fallback))
    } catch (e) {
      setParseError(e instanceof Error ? e.message : '读取文件失败')
    }
  }

  const handleSubmit = async () => {
    if (!file) return
    setSubmitting(true)
    try {
      const result = await uploadSkill(file)
      toast.success(`已上传：${result.skill.display_name}`, {
        description: result.warnings.length
          ? `提示：${result.warnings.join('；')}`
          : undefined,
      })
      reset()
      onOpenChange(false)
    } catch (e) {
      toast.error(`上传失败：${e instanceof Error ? e.message : '未知错误'}`)
      setSubmitting(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset()
        onOpenChange(o)
      }}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>上传 SKILL.md</DialogTitle>
          <DialogDescription>
            上传一个 Anthropic 风格的 SKILL.md 文件作为新技能。frontmatter 字段：name /
            display_name / description / category / type / triggers / personas /
            requires_apps / dependencies / keywords。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <label
            className={cn(
              'flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center text-sm transition-colors',
              file ? 'border-primary/40 bg-primary/5' : 'border-border hover:bg-muted/40',
            )}
          >
            <Upload className="size-6 text-muted-foreground" />
            <span className="text-foreground">
              {file ? file.name : '点击选择 .md 文件'}
            </span>
            <input
              type="file"
              accept=".md,.markdown,text/markdown"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) handleFile(f)
              }}
            />
          </label>

          {parseError && (
            <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-2.5 text-xs text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
              <XCircle className="size-4" />
              {parseError}
            </div>
          )}

          {preview && !parseError && (
            <div className="space-y-2 rounded-md border border-border/60 bg-muted/30 p-3 text-xs">
              <div className="flex items-center gap-2 font-medium text-foreground">
                <FileText className="size-3.5" />
                解析预览
              </div>
              <dl className="grid grid-cols-3 gap-x-3 gap-y-1">
                <dt className="text-muted-foreground">name</dt>
                <dd className="col-span-2 truncate font-mono">{preview.name}</dd>
                <dt className="text-muted-foreground">display_name</dt>
                <dd className="col-span-2 truncate">{preview.display_name}</dd>
                <dt className="text-muted-foreground">category</dt>
                <dd className="col-span-2">{preview.category ?? '（缺失）'}</dd>
                <dt className="text-muted-foreground">type</dt>
                <dd className="col-span-2">{preview.type ?? '（缺失，默认 tool）'}</dd>
                <dt className="text-muted-foreground">triggers</dt>
                <dd className="col-span-2">
                  {preview.triggers.length > 0
                    ? preview.triggers.join(' · ')
                    : '（缺失，可能无法被自动触发）'}
                </dd>
                <dt className="text-muted-foreground">body</dt>
                <dd className="col-span-2 text-muted-foreground">
                  {preview.body_lines} 行 / {preview.body_chars} 字符
                </dd>
              </dl>
              <p className="line-clamp-3 text-muted-foreground">{preview.description}</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={!file || !!parseError || submitting}>
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                上传中
              </>
            ) : (
              <>
                <CheckCircle2 className="size-4" />
                确认上传
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
