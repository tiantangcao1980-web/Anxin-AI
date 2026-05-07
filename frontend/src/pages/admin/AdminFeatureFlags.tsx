import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { API_BASE_URL, buildApiHeaders } from '@/lib/api'
import { getTokenStorage } from '@/lib/platform/storage'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

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

// ===== 前端功能模块 → 功能开关映射 =====
// 与 App.tsx 路由中的 feature 属性和 usePermission.ts 中的 FEATURE_FLAGS 对应

interface ModuleDef {
  key: string
  name: string
  description: string
}

interface ModuleGroup {
  label: string
  icon: keyof typeof icons
  modules: ModuleDef[]
}

const MODULE_GROUPS: ModuleGroup[] = [
  {
    label: 'AI 法务',
    icon: 'Sparkles',
    modules: [
      { key: 'ai_chat', name: '智能对话', description: 'AI 法律助手对话系统，支持合同审查、文书起草、法律咨询等' },
      { key: 'ai_assistant', name: 'AI 助手增强', description: '智能推荐、自动生成摘要等增强功能' },
    ],
  },
  {
    label: '智能协作',
    icon: 'Briefcase',
    modules: [
      { key: 'case_management', name: '案件管理', description: '案件全生命周期管理、线索跟进、任务分配' },
      { key: 'contract_management', name: '合同管理', description: '合同审查、模板管理、签约流程' },
      { key: 'document_management', name: '智能文档', description: '文档协作工作台、在线编辑、版本管理' },
      { key: 'lawyer_matching', name: '找律师', description: '律师智能匹配、推荐与预约' },
      { key: 'approval_workflow', name: '审批流程', description: '多级审批、模板配置' },
    ],
  },
  {
    label: '智能调查',
    icon: 'Search',
    modules: [
      { key: 'due_diligence', name: '尽职调查', description: '企业背景调查、工商信息、诉讼记录、信用报告' },
    ],
  },
  {
    label: '法律智库',
    icon: 'BookOpen',
    modules: [
      { key: 'knowledge_graph', name: '知识图谱', description: '法律知识图谱可视化与查询' },
      { key: 'knowledge_base', name: '法律智库', description: '法律法规数据库、案例库、智能检索' },
    ],
  },
  {
    label: '通讯与协作',
    icon: 'MessageCircle',
    modules: [
      { key: 'im_messaging', name: '即时通讯', description: '团队内部即时消息、文件分享' },
      { key: 'collaboration', name: '在线协作', description: '多人实时文档协作' },
    ],
  },
  {
    label: '律师生态',
    icon: 'Users',
    modules: [
      { key: 'lawyer_onboarding', name: '律师入驻', description: '律师认证入驻、资质审核流程' },
      { key: 'lawyer_dashboard', name: '律师工作台', description: '律师专属工作台、客户管理、收入统计' },
      { key: 'customer_acquisition', name: '获客管理', description: '客户获取渠道分析与管理' },
    ],
  },
  {
    label: '商业化',
    icon: 'DollarSign',
    modules: [
      { key: 'pricing', name: '定价页', description: '产品定价展示与套餐选择' },
      { key: 'my_subscription', name: '我的订阅', description: '用户订阅管理、账单查看' },
      { key: 'billing', name: '计费管理', description: '计费规则、订单管理' },
    ],
  },
  {
    label: '系统功能',
    icon: 'Settings',
    modules: [
      { key: 'private_llm', name: '私有大模型', description: '私有化大模型部署与配置' },
      { key: 'settings', name: '系统设置', description: '个人偏好、通知、隐私设置' },
      { key: 'private_deployment', name: '私有化部署', description: '企业私有化部署支持' },
      { key: 'firm_management', name: '律所管理', description: '律所信息、成员、部门管理' },
      { key: 'enterprise_management', name: '企业管理', description: '企业信息、合规配置' },
    ],
  },
]

// 所有预置 key 集合
const PRESET_KEYS = new Set(MODULE_GROUPS.flatMap(g => g.modules.map(m => m.key)))

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
  const token = await getTokenStorage().getAccessToken()
  const headers = buildApiHeaders(options.headers, { token })
  const resp = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
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
  const [showCustomOnly, setShowCustomOnly] = useState(false)

  const loadFlags = async () => {
    setLoading(true)
    try {
      const data = await flagRequest<{ items?: FeatureFlag[] } | FeatureFlag[]>('/admin/feature-flags')
      const items = Array.isArray(data) ? data : data?.items
      setFlags(Array.isArray(items) ? items : [])
    } catch (e: any) {
      toast.error(e.message || '加载失败')
      setFlags([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadFlags() }, [])

  // 构建 key → flag 映射
  const flagMap = new Map(flags.map(f => [f.key, f]))

  // 自定义 flags（不在预置列表中的）
  const customFlags = flags.filter(f => !PRESET_KEYS.has(f.key))

  const handleToggle = async (key: string, currentEnabled: boolean) => {
    try {
      const flag = flagMap.get(key)
      if (flag) {
        // 已有 flag，更新
        await flagRequest(`/admin/feature-flags/${key}`, {
          method: 'PUT',
          body: JSON.stringify({ enabled: !currentEnabled }),
        })
      } else {
        // 预置模块没有对应 flag，创建并启用/禁用
        const moduleDef = MODULE_GROUPS.flatMap(g => g.modules).find(m => m.key === key)
        await flagRequest('/admin/feature-flags', {
          method: 'POST',
          body: JSON.stringify({
            key,
            name: moduleDef?.name || key,
            description: moduleDef?.description || '',
            enabled: !currentEnabled,
            rollout_percentage: 10000,
          }),
        })
      }
      setFlags(prev =>
        prev.some(f => f.key === key)
          ? prev.map(f => f.key === key ? { ...f, enabled: !currentEnabled } : f)
          : [...prev, { id: key, key, name: key, description: null, enabled: !currentEnabled, rollout_percentage: 10000, target_roles: null, target_org_ids: null, metadata: null, expires_at: null, created_at: null, updated_at: null }]
      )
      toast.success(`已${!currentEnabled ? '启用' : '禁用'}`)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

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
        rollout_percentage: Math.round(form.rollout_percentage * 100), // 转为万分比
        target_roles: form.target_roles
          ? form.target_roles.split(',').map(s => s.trim()).filter(Boolean)
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
  const matchSearch = (text: string) =>
    !searchQuery.trim() || text.toLowerCase().includes(searchQuery.toLowerCase())

  if (loading) {
    return (
      <PageContainer title="功能开关">
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer
      title="功能开关"
      description="管理前端功能模块的可见性和灰度发布"
      actions={
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowCustomOnly(!showCustomOnly)}>
            {showCustomOnly ? '显示全部' : '仅自定义'}
          </Button>
          <Button onClick={openCreate} size="sm">
            <icons.Add className="w-4 h-4 mr-1.5" />
            自定义开关
          </Button>
        </div>
      }
    >
      {/* 搜索 */}
      <div className="mb-6">
        <Input
          placeholder="搜索功能模块..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {/* 预置模块分组 */}
      {!showCustomOnly && (
        <div className="space-y-6 mb-8">
          {MODULE_GROUPS.map((group) => {
            const visibleModules = group.modules.filter(
              m => matchSearch(m.key) || matchSearch(m.name) || matchSearch(m.description)
            )
            if (visibleModules.length === 0) return null

            const IconComp = icons[group.icon] || icons.Settings

            return (
              <Card key={group.label}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <IconComp className="w-4.5 h-4.5 text-primary" />
                    {group.label}
                    <Badge variant="secondary" className="ml-auto text-xs font-normal">
                      {visibleModules.filter(m => {
                        const flag = flagMap.get(m.key)
                        return !flag || flag.enabled
                      }).length}/{visibleModules.length} 已启用
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="divide-y divide-border">
                    {visibleModules.map((mod) => {
                      const flag = flagMap.get(mod.key)
                      const isEnabled = !flag || flag.enabled // 没有 flag 记录默认启用
                      const hasCustomConfig = flag && (
                        (flag.target_roles && flag.target_roles.length > 0) ||
                        flag.rollout_percentage < 10000 ||
                        flag.expires_at
                      )

                      return (
                        <div
                          key={mod.key}
                          className="flex items-center justify-between py-3 gap-4"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-foreground">{mod.name}</span>
                              <code className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-mono">
                                {mod.key}
                              </code>
                              {hasCustomConfig && (
                                <Badge variant="outline" className="text-[10px] text-warning border-warning/30">
                                  自定义规则
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5 truncate">
                              {mod.description}
                            </p>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            {flag && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => openEdit(flag)}
                              >
                                <icons.Settings className="w-3.5 h-3.5" />
                              </Button>
                            )}
                            <Switch
                              checked={isEnabled}
                              onCheckedChange={() => handleToggle(mod.key, isEnabled)}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* 自定义开关 */}
      {customFlags.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <icons.Target className="w-4.5 h-4.5 text-muted-foreground" />
              自定义开关
              <Badge variant="secondary" className="ml-auto text-xs font-normal">
                {customFlags.filter(f => f.enabled).length}/{customFlags.length} 已启用
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="divide-y divide-border">
              {customFlags
                .filter(f => matchSearch(f.key) || matchSearch(f.name))
                .map((flag) => (
                  <div key={flag.id} className="flex items-center justify-between py-3 gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">{flag.name}</span>
                        <code className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-mono">
                          {flag.key}
                        </code>
                        {flag.rollout_percentage < 10000 && (
                          <Badge variant="outline" className="text-[10px]">
                            灰度 {Math.round(flag.rollout_percentage / 100)}%
                          </Badge>
                        )}
                      </div>
                      {flag.description && (
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">{flag.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(flag)}>
                        <icons.Edit className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setDeleteTarget(flag.key)}>
                        <icons.Delete className="w-3.5 h-3.5 text-destructive" />
                      </Button>
                      <Switch
                        checked={flag.enabled}
                        onCheckedChange={() => handleToggle(flag.key, flag.enabled)}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 编辑/创建对话框 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editKey ? '编辑功能开关' : '新建自定义开关'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Key</Label>
              <Input
                value={form.key}
                onChange={(e) => setForm({ ...form, key: e.target.value })}
                placeholder="如 custom_feature"
                disabled={!!editKey}
              />
            </div>
            <div className="space-y-1.5">
              <Label>名称</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="功能名称"
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
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
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
