/**
 * SecureSkillInstallButton —— 带 manifest 预览 + 授权同意的安装入口
 *
 * 区别于现有 SkillUploadDialog（直接上传 + 注册）：
 *   1. 用户选文件
 *   2. POST /skills/preview 解析 manifest（不注册）
 *   3. 弹 SkillInstallDialog 展示 tier / 资源 / 网络 / 文件系统 / 权限 / 签名
 *   4. 用户勾选"我已知悉" + 点"授权安装"后才 POST /skills/upload
 *   5. 成功后调 onInstalled() 让列表刷新
 *
 * 设计意图：给 T1/T2/T3/T4 这种"会真执行代码"的 skill 一个强同意路径，
 *           避免误装陌生 SKILL.md 直接拿到敏感权限。
 */

import { useRef, useState } from 'react'
import { toast } from 'sonner'

import { icons } from '@/lib/icons'
import { iconSize } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import {
  SkillInstallDialog,
  type SkillInstallSummary,
} from '@/components/admin/enterprise/SkillInstallDialog'

interface Props {
  onInstalled?: () => void
  size?: 'default' | 'sm' | 'lg'
  variant?: 'default' | 'outline' | 'ghost'
}

export function SecureSkillInstallButton({
  onInstalled,
  size = 'default',
  variant = 'outline',
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [summary, setSummary] = useState<SkillInstallSummary | null>(null)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [open, setOpen] = useState(false)
  const [previewing, setPreviewing] = useState(false)

  const onPick = () => {
    fileInputRef.current?.click()
  }

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    // 允许重复选同一个文件
    e.target.value = ''
    setPreviewing(true)
    try {
      const fd = new FormData()
      fd.append('file', f)
      const token = localStorage.getItem('access_token') || ''
      const resp = await fetch('/api/v1/skills/preview', {
        method: 'POST',
        body: fd,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      const data = await resp.json()
      if (!resp.ok) {
        const detail =
          typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail || data)
        throw new Error(detail)
      }
      setSummary(data as SkillInstallSummary)
      setPendingFile(f)
      setOpen(true)
    } catch (err) {
      toast.error(`预览失败：${(err as Error).message}`)
    } finally {
      setPreviewing(false)
    }
  }

  const onConfirmInstall = async (s: SkillInstallSummary) => {
    if (!pendingFile) {
      toast.error('文件丢失，请重新选择')
      return
    }
    const fd = new FormData()
    fd.append('file', pendingFile)
    const token = localStorage.getItem('access_token') || ''
    const resp = await fetch('/api/v1/skills/upload', {
      method: 'POST',
      body: fd,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) {
      const detail =
        typeof data.detail === 'string'
          ? data.detail
          : JSON.stringify(data.detail || data)
      throw new Error(detail)
    }
    toast.success(`已安装 ${s.name}`)
    setSummary(null)
    setPendingFile(null)
    onInstalled?.()
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".md"
        className="hidden"
        onChange={onFile}
      />
      <Button
        size={size}
        variant={variant}
        onClick={onPick}
        disabled={previewing}
        data-testid="secure-skill-install-btn"
      >
        <icons.ShieldCheck className={`${iconSize.sm} mr-1.5`} />
        {previewing ? '解析中…' : '授权安装 Skill'}
      </Button>
      <SkillInstallDialog
        open={open}
        onOpenChange={setOpen}
        skill={summary}
        onConfirm={onConfirmInstall}
      />
    </>
  )
}

export default SecureSkillInstallButton
