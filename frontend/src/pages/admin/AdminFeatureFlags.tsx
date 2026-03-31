import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { adminApi } from '@/lib/api'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { heading, statusBadge, cardStyle } from '@/lib/design-tokens'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003/api/v1'

interface FeatureFlag {
  id: string
  key: string
  name: string
  description: string | null
  enabled: boolean
  rollout_percentage: number
  target_roles: string[] | null
  target_org_ids: string[] | null
  metadata: Record<string, unknown> | null
  expires_at: string | null
  created_at: string | null
  updated_at: string | null
}

interface FeatureFlagListResponse {
  items?: FeatureFlag[]
  meta?: {
    total: number
    skip: number
    limit: number
  }
}

const emptyForm = {
  key: '',
  name: '',
  description: '',
  enabled: false,
  rollout_percentage: 100,
  target_roles: '',
  expires_at: '',
}

async function flagRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const resp = await fetch(`${API_BASE_URL}${path}`, { ...headers, ...options, headers })
  const json = await resp.json()
  if (!resp.ok || (json.code && json.code >= 400)) {
    throw new Error(json.message || json.detail || '请求失败')
  }
  return (json.data ?? json) as T
}

export default function AdminFeatureFlags() {
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editKey, setEditKey] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const loadFlags = async () => {
    setLoading(true)
    try {
      const data = await flagRequest<FeatureFlagListResponse | FeatureFlag[]>('/admin/feature-flags')
      const items = Array.isArray(data) ? data : data?.items
      setFlags(Array.isArray(items) ? items : [])
    } catch (e: any) {
      toast.error(e.message || '加载失败')
      setFlags([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFlags()
  }, [])

  const openCreate = () => {
    setEditKey(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  const openEdit = (flag: FeatureFlag) => {
    setEditKey(flag.key)
    setForm({
      key: flag.key,
      name: flag.name,
      description: flag.description || '',
      enabled: flag.enabled,
      rollout_percentage: flag.rollout_percentage,
      target_roles: flag.target_roles ? flag.target_roles.join(', ') : '',
      expires_at: flag.expires_at ? flag.expires_at.slice(0, 16) : '',
    })
    setDialogOpen(true)
  }

  const handleToggle = async (flag: FeatureFlag) => {
    try {
      await flagRequest(`/admin/feature-flags/${flag.key}`, {
        method: 'PUT',
        body: JSON.stringify({ enabled: !flag.enabled }),
      })
      setFlags((prev) =>
        prev.map((f) => (f.key === flag.key ? { ...f, enabled: !f.enabled } : f))
      )
      toast.success(`已${!flag.enabled ? '启用' : '禁用'} ${flag.name}`)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleSave = async () => {
    if (!form.key || !form.name) {
      toast.error('Key 和名称为必填项')
      return
    }
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        key: form.key,
        name: form.name,
        description: form.description || null,
        enabled: form.enabled,
        rollout_percentage: form.rollout_percentage,
        target_roles: form.target_roles
          ? form.target_roles.split(',').map((s) => s.trim()).filter(Boolean)
          : null,
        expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      }
      if (editKey) {
        await flagRequest(`/admin/feature-flags/${editKey}`, {
          method: 'PUT',
          body: JSON.stringify(body),
        })
        toast.success('更新成功')
      } else {
        await flagRequest('/admin/feature-flags', {
          method: 'POST',
          body: JSON.stringify(body),
        })
        toast.success('创建成功')
      }
      setDialogOpen(false)
      await loadFlags()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    try {
      await flagRequest(`/admin/feature-flags/${deleteTarget}`, { method: 'DELETE' })
      toast.success('删除成功')
      setDeleteTarget(null)
      await loadFlags()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  // 搜索过滤
  const filteredFlags = searchQuery.trim()
    ? flags.filter(
        (f) =>
          f.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
          f.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : flags

  return (
    <PageContainer
      title="功能开关"
      description="管理系统功能的灰度发布与开关控制"
      actions={
        <Button onClick={openCreate} size="sm">
          <icons.Add className="w-4 h-4 mr-1.5" />
          新建开关
        </Button>
      }
    >
      {/* 搜索框 */}
      {!loading && flags.length > 0 && (
        <div className="mb-4">
          <Input
            placeholder="搜索 Key 或名称..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="max-w-xs"
          />
        </div>
      )}

      <div className={cardStyle.base}>
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : flags.length === 0 ? (
          <div className="text-center py-12">
            <icons.Settings className="w-10 h-10 mx-auto text-muted-foreground/40 mb-3" />
            <p className={heading.muted}>暂无功能开关</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>名称</TableHead>
                <TableHead className="text-center">状态</TableHead>
                <TableHead className="text-center">灰度百分比</TableHead>
                <TableHead>目标角色</TableHead>
                <TableHead>过期时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredFlags.map((flag) => (
                <TableRow key={flag.id}>
                  <TableCell className="font-mono text-xs">{flag.key}</TableCell>
                  <TableCell className={heading.card}>{flag.name}</TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={flag.enabled}
                      onCheckedChange={() => handleToggle(flag)}
                    />
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className={flag.rollout_percentage < 100 ? statusBadge.warning : statusBadge.neutral}>
                      {flag.rollout_percentage}%
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {flag.target_roles && flag.target_roles.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {flag.target_roles.map((r) => (
                          <Badge key={r} variant="secondary" className="text-xs">
                            {r}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <span className={heading.micro}>全部</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {flag.expires_at ? (
                      <span className="text-xs text-muted-foreground">
                        {new Date(flag.expires_at).toLocaleString('zh-CN')}
                      </span>
                    ) : (
                      <span className={heading.micro}>--</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(flag)}>
                        <icons.Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(flag.key)}>
                        <icons.Delete className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editKey ? '编辑功能开关' : '新建功能开关'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Key</Label>
              <Input
                value={form.key}
                onChange={(e) => setForm({ ...form, key: e.target.value })}
                placeholder="如 im_messaging"
                disabled={!!editKey}
              />
            </div>
            <div className="space-y-1.5">
              <Label>名称</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="如 即时通讯"
              />
            </div>
            <div className="space-y-1.5">
              <Label>描述</Label>
              <Input
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="功能描述（可选）"
              />
            </div>
            <div className="flex items-center gap-3">
              <Label>启用</Label>
              <Switch
                checked={form.enabled}
                onCheckedChange={(v) => setForm({ ...form, enabled: v })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>灰度百分比 (0-100)</Label>
              <Input
                type="number"
                min={0}
                max={100}
                value={form.rollout_percentage}
                onChange={(e) =>
                  setForm({ ...form, rollout_percentage: parseInt(e.target.value) || 0 })
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>目标角色（逗号分隔，留空表示不限）</Label>
              <Input
                value={form.target_roles}
                onChange={(e) => setForm({ ...form, target_roles: e.target.value })}
                placeholder="admin, lawyer, org_admin"
              />
            </div>
            <div className="space-y-1.5">
              <Label>过期时间</Label>
              <Input
                type="datetime-local"
                value={form.expires_at}
                onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="确认删除"
        description="删除后无法恢复，确定要删除此功能开关吗？"
        confirmText="确认删除"
        destructive
        onConfirm={handleDeleteConfirm}
      />
    </PageContainer>
  )
}
