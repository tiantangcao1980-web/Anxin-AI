/**
 * 角色绑定面板 —— 后台 → 企业 → 权限绑定
 *
 * 表单：选择主体（user/department/group/position）+ 角色 + 作用域 → 创建绑定
 * 列表：本次会话临时缓存（暂不从后端拉，后端无 list-all 端点）
 * 撤回：按绑定 id 撤回
 *
 * 注：后端 list-all 端点未实装，本面板专注 **创建 / 撤回 / 即查即用**
 *     的最小有用形态，列表为本地"最近授权"缓存。
 */

import { useState } from 'react'
import { toast } from 'sonner'

import { icons } from '@/lib/icons'
import { heading, iconSize } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  enterpriseApi,
  type RoleBindingRow,
} from '@/lib/api/enterprise-directory'

const SUBJECT_TYPES = ['user', 'department', 'group', 'position'] as const
const SCOPE_TYPES = ['org', 'department'] as const

const ROLE_PRESETS = [
  'super_admin',
  'org_admin',
  'dept_admin',
  'partner',
  'lawyer',
  'paralegal',
  'enterprise_user',
  'individual_user',
  'platform_lawyer',
  'viewer',
] as const

interface Props {
  orgId: string | null | undefined
}

export function RoleBindingPanel({ orgId }: Props) {
  const [form, setForm] = useState({
    subject_type: 'user' as (typeof SUBJECT_TYPES)[number],
    subject_id: '',
    role: 'lawyer' as string,
    scope_type: 'org' as (typeof SCOPE_TYPES)[number],
    scope_id: '',
    reason: '',
    expires_at: '',
  })
  const [recent, setRecent] = useState<RoleBindingRow[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [permsLookup, setPermsLookup] = useState<{
    user_id: string
    scope_type: string
    scope_id: string
    permissions: string[]
  } | null>(null)
  const [lookupForm, setLookupForm] = useState({
    user_id: '',
    scope_type: 'org' as (typeof SCOPE_TYPES)[number],
    scope_id: '',
  })

  const onGrant = async () => {
    if (!form.subject_id.trim() || !form.role.trim() || !form.scope_id.trim()) {
      toast.error('主体 / 角色 / 作用域 都必须填写')
      return
    }
    setSubmitting(true)
    try {
      const rb = await enterpriseApi.grantRole({
        subject_type: form.subject_type,
        subject_id: form.subject_id.trim(),
        role: form.role.trim(),
        scope_type: form.scope_type,
        scope_id: form.scope_id.trim(),
        reason: form.reason || null,
        expires_at: form.expires_at || null,
      })
      setRecent((prev) => [rb, ...prev].slice(0, 20))
      toast.success('授权已生效')
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const onRevoke = async (id: string) => {
    if (!confirm('确认撤回此授权？')) return
    try {
      await enterpriseApi.revokeRole(id)
      setRecent((prev) => prev.filter((r) => r.id !== id))
      toast.success('已撤回')
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const onLookup = async () => {
    if (!lookupForm.user_id.trim() || !lookupForm.scope_id.trim()) {
      toast.error('user_id 与 scope_id 必填')
      return
    }
    try {
      const data = await enterpriseApi.effectivePermissions({
        uid: lookupForm.user_id.trim(),
        scopeType: lookupForm.scope_type,
        scopeId: lookupForm.scope_id.trim(),
      })
      setPermsLookup(data)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  if (!orgId) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
        当前账号未关联组织，无法管理权限绑定。
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className={heading.section}>权限绑定</h3>
        <p className="text-sm text-muted-foreground mt-1">
          按"主体 × 角色 × 作用域"授权。部门绑定向下继承，过期绑定自动失效。
        </p>
      </div>

      {/* 创建表单 */}
      <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="text-sm font-medium">创建新绑定</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>主体类型</Label>
            <Select
              value={form.subject_type}
              onValueChange={(v) =>
                setForm((p) => ({ ...p, subject_type: v as never }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SUBJECT_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>主体 ID</Label>
            <Input
              value={form.subject_id}
              onChange={(e) =>
                setForm((p) => ({ ...p, subject_id: e.target.value }))
              }
              placeholder="user_id / department_id / group_id"
            />
          </div>
          <div className="space-y-1.5">
            <Label>角色</Label>
            <Select
              value={form.role}
              onValueChange={(v) => setForm((p) => ({ ...p, role: v }))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLE_PRESETS.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>作用域类型</Label>
            <Select
              value={form.scope_type}
              onValueChange={(v) =>
                setForm((p) => ({ ...p, scope_type: v as never }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCOPE_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>作用域 ID</Label>
            <Input
              value={form.scope_id}
              onChange={(e) =>
                setForm((p) => ({ ...p, scope_id: e.target.value }))
              }
              placeholder="org_id 或 department_id"
            />
          </div>
          <div className="space-y-1.5">
            <Label>过期时间（可选 ISO8601）</Label>
            <Input
              value={form.expires_at}
              onChange={(e) =>
                setForm((p) => ({ ...p, expires_at: e.target.value }))
              }
              placeholder="2026-12-31T23:59:00Z"
            />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label>授权原因（可选，进 audit_log）</Label>
            <Input
              value={form.reason}
              onChange={(e) =>
                setForm((p) => ({ ...p, reason: e.target.value }))
              }
              placeholder="例如：代理 Q1 法务合规项目"
            />
          </div>
        </div>
        <div className="flex justify-end">
          <Button onClick={() => void onGrant()} disabled={submitting}>
            <icons.Check className={`${iconSize.sm} mr-1`} />
            {submitting ? '授权中…' : '授权'}
          </Button>
        </div>
      </div>

      {/* 最近授权 */}
      {recent.length > 0 && (
        <div className="rounded-2xl border border-border bg-card p-5">
          <div className="text-sm font-medium mb-3">
            本次会话授权（{recent.length}）
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="text-left py-2">主体</th>
                  <th className="text-left py-2">角色</th>
                  <th className="text-left py-2">作用域</th>
                  <th className="text-left py-2">过期</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {recent.map((rb) => (
                  <tr key={rb.id} className="border-b border-border last:border-0">
                    <td className="py-2 font-mono text-xs">
                      {rb.subject_type}:{rb.subject_id.slice(0, 8)}…
                    </td>
                    <td className="py-2">{rb.role}</td>
                    <td className="py-2 font-mono text-xs">
                      {rb.scope_type}:{rb.scope_id.slice(0, 8)}…
                    </td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {rb.expires_at || '永久'}
                    </td>
                    <td className="py-2 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive"
                        onClick={() => void onRevoke(rb.id)}
                      >
                        撤回
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 有效权限查询 */}
      <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="text-sm font-medium">有效权限查询</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label>user_id</Label>
            <Input
              value={lookupForm.user_id}
              onChange={(e) =>
                setLookupForm((p) => ({ ...p, user_id: e.target.value }))
              }
            />
          </div>
          <div className="space-y-1.5">
            <Label>作用域类型</Label>
            <Select
              value={lookupForm.scope_type}
              onValueChange={(v) =>
                setLookupForm((p) => ({ ...p, scope_type: v as never }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCOPE_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>作用域 ID</Label>
            <Input
              value={lookupForm.scope_id}
              onChange={(e) =>
                setLookupForm((p) => ({ ...p, scope_id: e.target.value }))
              }
            />
          </div>
        </div>
        <div className="flex justify-end">
          <Button variant="outline" onClick={() => void onLookup()}>
            <icons.Search className={`${iconSize.sm} mr-1`} />
            查询
          </Button>
        </div>
        {permsLookup && (
          <div className="rounded-xl bg-muted/50 p-3 text-sm">
            <div className="text-xs text-muted-foreground mb-2">
              共 {permsLookup.permissions.length} 项权限
            </div>
            <div className="flex flex-wrap gap-1.5">
              {permsLookup.permissions.length === 0 && (
                <span className="text-muted-foreground">（空集）</span>
              )}
              {permsLookup.permissions.map((p) => (
                <span
                  key={p}
                  className="px-2 py-0.5 rounded bg-background border border-border text-xs font-mono"
                >
                  {p}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default RoleBindingPanel
