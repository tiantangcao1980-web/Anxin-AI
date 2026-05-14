/**
 * Skill 安装授权弹窗
 *
 * 用户视角（设计文档 docs/v3/skills-sandbox-design.md §9）：
 *   1. 上传或选择一个 SKILL.md
 *   2. 弹窗展示 manifest：tier / 资源 / 网络 / 文件系统 / 权限 / 签名信息
 *   3. 用户勾选"我已知悉以上风险" + 点击"授权安装"
 *   4. 后端落库 + 写 audit_log
 *
 * 这是**纯展示 + 同意**组件，不直接调上传 API；调用方可在 onConfirm 回调里走 /skills/upload。
 */

import { useState } from 'react'

import { icons } from '@/lib/icons'
import { iconSize } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

// ============ Manifest 形状 ============

export interface SandboxManifestSummary {
  tier: 'T0' | 'T1' | 'T2' | 'T3' | 'T4'
  entrypoint?: string | null
  runtime?: string | null
  resource_limits?: {
    cpu_millicores?: number
    memory_mb?: number
    disk_mb?: number
    timeout_sec?: number
  } | null
  network?: {
    mode: 'none' | 'allowlist' | 'full'
    allowed_hosts?: string[]
  } | null
  filesystem?: {
    read?: string[]
    write?: string[]
  } | null
  permissions?: string[] | null
  signature?: {
    algo?: string
    publisher?: string
  } | null
  fingerprint?: string | null
}

export interface SkillInstallSummary {
  name: string
  description: string
  version: string
  author?: string | null
  manifest: SandboxManifestSummary
}

const TIER_DESC: Record<SandboxManifestSummary['tier'], { label: string; tone: string }> = {
  T0: { label: 'Prompt-only（无代码执行）', tone: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
  T1: { label: 'In-process 受信进程', tone: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' },
  T2: { label: 'Subprocess 子进程沙箱', tone: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' },
  T3: { label: 'Container 容器沙箱', tone: 'bg-orange-500/10 text-orange-600 dark:text-orange-400' },
  T4: { label: 'Remote 远程沙箱', tone: 'bg-red-500/10 text-red-600 dark:text-red-400' },
}

// ============ 组件 ============

interface Props {
  open: boolean
  onOpenChange: (v: boolean) => void
  skill: SkillInstallSummary | null
  /** 用户授权安装后调用；返回 promise，组件不在 try/catch */
  onConfirm: (skill: SkillInstallSummary) => Promise<void> | void
}

export function SkillInstallDialog({ open, onOpenChange, skill, onConfirm }: Props) {
  const [agreed, setAgreed] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  if (!skill) return null

  const m = skill.manifest
  const tier = TIER_DESC[m.tier]

  const handleConfirm = async () => {
    setSubmitting(true)
    try {
      await onConfirm(skill)
      onOpenChange(false)
      setAgreed(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <icons.Sparkles className={`${iconSize.md} text-primary`} />
            安装 Skill
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* 标题区 */}
          <div className="rounded-2xl border border-border bg-card p-4">
            <div className="text-lg font-medium">{skill.name}</div>
            <div className="text-sm text-muted-foreground mt-1">{skill.description}</div>
            <div className="mt-2 flex items-center gap-2 text-xs">
              <span className="font-mono text-muted-foreground">v{skill.version}</span>
              {skill.author && (
                <>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-muted-foreground">作者：{skill.author}</span>
                </>
              )}
            </div>
          </div>

          {/* 信任分级 */}
          <Section title="信任分级" icon="ShieldCheck">
            <div className="flex items-center gap-3">
              <span
                className={`px-2.5 py-1 rounded text-xs font-mono font-semibold ${tier.tone}`}
              >
                {m.tier}
              </span>
              <span className="text-sm text-muted-foreground">{tier.label}</span>
            </div>
            {m.signature && (
              <div className="mt-3 flex items-center gap-2 text-xs">
                <icons.Check className={`${iconSize.sm} text-emerald-600`} />
                <span>
                  签名发布方：
                  <span className="font-mono ml-1">{m.signature.publisher}</span>
                  <span className="text-muted-foreground ml-1">
                    ({m.signature.algo || 'ed25519'})
                  </span>
                </span>
              </div>
            )}
            {!m.signature && m.tier !== 'T0' && (
              <div className="mt-3 flex items-start gap-2 text-xs text-amber-600 dark:text-amber-400">
                <icons.AlertTriangle className={`${iconSize.sm} mt-0.5`} />
                <span>未签名 —— 若 tier=T1 将被后端拒绝；其他 tier 仍可执行但建议审慎评估来源。</span>
              </div>
            )}
          </Section>

          {/* 资源限额 */}
          {m.resource_limits && (
            <Section title="资源限额" icon="Cpu">
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <Pair label="CPU" value={m.resource_limits.cpu_millicores ? `${m.resource_limits.cpu_millicores} mCPU` : '—'} />
                <Pair label="内存" value={m.resource_limits.memory_mb ? `${m.resource_limits.memory_mb} MB` : '—'} />
                <Pair label="磁盘" value={m.resource_limits.disk_mb ? `${m.resource_limits.disk_mb} MB` : '—'} />
                <Pair label="超时" value={m.resource_limits.timeout_sec ? `${m.resource_limits.timeout_sec} 秒` : '—'} />
              </dl>
            </Section>
          )}

          {/* 网络 */}
          {m.network && (
            <Section title="网络策略" icon="Globe">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-mono px-2 py-0.5 rounded bg-muted text-xs">
                  {m.network.mode}
                </span>
                {m.network.mode === 'none' && <span className="text-muted-foreground">完全断网（最安全）</span>}
                {m.network.mode === 'allowlist' && <span className="text-muted-foreground">仅放行白名单主机</span>}
                {m.network.mode === 'full' && (
                  <span className="text-amber-600">完全放开（仅 dev 环境允许）</span>
                )}
              </div>
              {m.network.allowed_hosts && m.network.allowed_hosts.length > 0 && (
                <ul className="mt-2 text-xs text-muted-foreground font-mono list-disc list-inside">
                  {m.network.allowed_hosts.map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                </ul>
              )}
            </Section>
          )}

          {/* 文件系统 */}
          {m.filesystem && (m.filesystem.read?.length || m.filesystem.write?.length) ? (
            <Section title="文件系统" icon="FolderOpen">
              {m.filesystem.read && m.filesystem.read.length > 0 && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">读：</div>
                  <ul className="text-xs font-mono space-y-0.5">
                    {m.filesystem.read.map((p) => <li key={p}>{p}</li>)}
                  </ul>
                </div>
              )}
              {m.filesystem.write && m.filesystem.write.length > 0 && (
                <div className="mt-2">
                  <div className="text-xs text-muted-foreground mb-1">写：</div>
                  <ul className="text-xs font-mono space-y-0.5">
                    {m.filesystem.write.map((p) => <li key={p}>{p}</li>)}
                  </ul>
                </div>
              )}
            </Section>
          ) : null}

          {/* 权限 */}
          {m.permissions && m.permissions.length > 0 && (
            <Section title="所需权限" icon="Lock">
              <div className="flex flex-wrap gap-1.5">
                {m.permissions.map((p) => (
                  <span
                    key={p}
                    className="px-2 py-0.5 rounded bg-muted text-xs font-mono"
                  >
                    {p}
                  </span>
                ))}
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                安装即授权 —— 你当前角色必须拥有这些权限才能执行此 Skill。
              </div>
            </Section>
          )}

          {/* fingerprint */}
          {m.fingerprint && (
            <div className="text-xs text-muted-foreground font-mono break-all border border-border rounded-xl p-2 bg-muted/30">
              {m.fingerprint}
            </div>
          )}

          {/* 同意 */}
          <div className="flex items-start gap-2 pt-2 border-t border-border">
            <Checkbox
              id="install-agreement"
              checked={agreed}
              onCheckedChange={(v) => setAgreed(v === true)}
            />
            <label htmlFor="install-agreement" className="text-sm cursor-pointer">
              我已知悉以上权限和风险，授权安装并允许后续执行
            </label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button
            onClick={() => void handleConfirm()}
            disabled={!agreed || submitting}
          >
            {submitting ? '安装中…' : '授权安装'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Section({
  title,
  icon,
  children,
}: {
  title: string
  icon: keyof typeof icons
  children: React.ReactNode
}) {
  const Icon = icons[icon]
  return (
    <div>
      <div className="flex items-center gap-2 text-sm font-medium mb-2">
        <Icon className={`${iconSize.sm} text-primary`} />
        {title}
      </div>
      <div className="pl-6">{children}</div>
    </div>
  )
}

function Pair({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="font-mono text-sm">{value}</dd>
    </>
  )
}

export default SkillInstallDialog
