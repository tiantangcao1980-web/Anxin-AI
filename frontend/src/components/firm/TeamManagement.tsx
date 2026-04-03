/**
 * TeamManagement - 团队管理组件
 *
 * - 团队列表（卡片网格）：名称、描述、负责人、成员数
 * - 点击团队卡展开成员列表
 * - 创建/编辑团队 Dialog
 * - 添加/移除成员
 * - 团队负责人可从真实用户列表中指定
 */

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { icons } from '@/lib/icons'
import { cardStyle, iconSize, heading, statusBadge } from '@/lib/design-tokens'
import { Skeleton } from '@/components/ui/skeleton'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { adminApi, firmApi } from '@/lib/api'
import { toast } from 'sonner'

// ========== Mock 数据 ==========

interface TeamMember {
  id: string
  name: string
  role: 'leader' | 'member'
  avatar?: string
  title: string
}

interface Team {
  id: string
  name: string
  description: string
  leader: string
  leaderId?: string
  memberCount: number
  members: TeamMember[]
}

interface UserOption {
  id: string
  name: string
  email: string
}

// 数据从 API 加载

// ========== 组件 ==========

export default function TeamManagement() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [teams, setTeams] = useState<Team[]>([])
  const [expandedTeam, setExpandedTeam] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTeam, setEditingTeam] = useState<Team | null>(null)
  const [formName, setFormName] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [selectedLeaderId, setSelectedLeaderId] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [removeMemberTarget, setRemoveMemberTarget] = useState<{ teamId: string; memberId: string } | null>(null)
  const [memberDialogOpen, setMemberDialogOpen] = useState(false)
  const [memberTeamId, setMemberTeamId] = useState<string | null>(null)
  const [userOptions, setUserOptions] = useState<UserOption[]>([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [memberSearch, setMemberSearch] = useState('')
  const [saving, setSaving] = useState(false)

  const fetchTeams = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await firmApi.listTeams()
      const items = Array.isArray(data) ? data : (data.items ?? data.teams ?? [])
      setTeams(
        items.map((t: any) => ({
          id: t.id,
          name: t.name ?? '',
          description: t.description ?? '',
          leader: t.leader ?? t.leader_name ?? '待指定',
          leaderId: t.leader_id ?? undefined,
          memberCount: t.member_count ?? t.memberCount ?? (t.members?.length ?? 0),
          members: (t.members ?? []).map((m: any) => ({
            id: m.id ?? m.user_id ?? '',
            name: m.name ?? m.user_name ?? '',
            role: m.role ?? 'member',
            avatar: m.avatar ?? m.avatar_url,
            title: m.title ?? m.position ?? '',
          })),
        }))
      )
    } catch (err: any) {
      setError(err.message || '加载团队数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTeams().catch(() => undefined)
  }, [])

  const loadActiveUsers = async () => {
    const res = await adminApi.listUsers({ limit: 100, is_active: true })
    const payload: any = res
    const items = payload?.users ?? payload?.items ?? []
    return items.map((item: any) => ({
      id: item.id,
      name: item.name || '未命名用户',
      email: item.email || '',
    }))
  }

  const handleToggleExpand = (teamId: string) => {
    setExpandedTeam(expandedTeam === teamId ? null : teamId)
  }

  const handleOpenCreate = async () => {
    setEditingTeam(null)
    setFormName('')
    setFormDesc('')
    setSelectedLeaderId('')
    setDialogOpen(true)
    try {
      setUserOptions(await loadActiveUsers())
    } catch (e: any) {
      toast.error(e.message || '加载用户列表失败')
    }
  }

  const handleOpenEdit = async (team: Team) => {
    setEditingTeam(team)
    setFormName(team.name)
    setFormDesc(team.description)
    setSelectedLeaderId(team.leaderId || '')
    setDialogOpen(true)
    try {
      setUserOptions(await loadActiveUsers())
    } catch (e: any) {
      toast.error(e.message || '加载用户列表失败')
    }
  }

  const handleOpenAddMember = async (teamId: string) => {
    setMemberTeamId(teamId)
    setSelectedUserId('')
    setMemberSearch('')
    setMemberDialogOpen(true)
    try {
      const res = await adminApi.listUsers({ limit: 100, is_active: true })
      const payload: any = res
      const items = payload?.users ?? payload?.items ?? []
      const currentTeam = teams.find((team) => team.id === teamId)
      const existingMemberIds = new Set((currentTeam?.members ?? []).map((member) => member.id))
      setUserOptions(
        items
          .filter((item: any) => !existingMemberIds.has(item.id))
          .map((item: any) => ({
            id: item.id,
            name: item.name || '未命名用户',
            email: item.email || '',
          }))
      )
    } catch (e: any) {
      toast.error(e.message || '加载用户列表失败')
    }
  }

  const handleSave = async () => {
    if (!formName.trim()) return
    setSaving(true)
    try {
      if (editingTeam) {
        await firmApi.updateTeam(editingTeam.id, {
          name: formName.trim(),
          description: formDesc.trim() || undefined,
          leader_id: selectedLeaderId || undefined,
        })
        toast.success('团队已更新')
      } else {
        await firmApi.createTeam({
          name: formName.trim(),
          description: formDesc.trim() || undefined,
          leader_id: selectedLeaderId || undefined,
        })
        toast.success('团队已创建')
      }
      await fetchTeams()
      setDialogOpen(false)
    } catch (e: any) {
      toast.error(e.message || (editingTeam ? '更新团队失败' : '创建团队失败'))
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    try {
      await firmApi.deleteTeam(deleteTarget)
      toast.success('团队已删除')
      if (expandedTeam === deleteTarget) setExpandedTeam(null)
      setDeleteTarget(null)
      await fetchTeams()
    } catch (e: any) {
      toast.error(e.message || '删除团队失败')
    }
  }

  const handleRemoveMemberConfirm = async () => {
    if (!removeMemberTarget) return
    const { teamId, memberId } = removeMemberTarget
    try {
      await firmApi.removeTeamMember(teamId, memberId)
      toast.success('成员已移除')
      setRemoveMemberTarget(null)
      await fetchTeams()
    } catch (e: any) {
      toast.error(e.message || '移除成员失败')
    }
  }

  const handleAddMember = async () => {
    if (!memberTeamId || !selectedUserId) return
    setSaving(true)
    try {
      await firmApi.addTeamMember(memberTeamId, { user_id: selectedUserId, role: 'member' })
      toast.success('成员已添加')
      setMemberDialogOpen(false)
      setMemberTeamId(null)
      setSelectedUserId('')
      await fetchTeams()
    } catch (e: any) {
      toast.error(e.message || '添加成员失败')
    } finally {
      setSaving(false)
    }
  }

  const filteredUserOptions = userOptions.filter((user) => {
    const keyword = memberSearch.trim().toLowerCase()
    if (!keyword) return true
    return (
      user.name.toLowerCase().includes(keyword) ||
      user.email.toLowerCase().includes(keyword)
    )
  })

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-9 w-24" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`${cardStyle.base} flex flex-col items-center justify-center py-12`}>
        <icons.AlertTriangle className={`${iconSize.xl} text-destructive/60 mb-3`} />
        <p className="text-sm text-muted-foreground mb-3">{error}</p>
        <Button variant="outline" size="sm" onClick={() => fetchTeams()}>
          重试
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 操作栏 */}
      <div className="flex items-center justify-between">
        <p className={heading.muted}>共 {teams.length} 个团队</p>
        <Button size="sm" onClick={handleOpenCreate}>
          <icons.Plus className={iconSize.sm} />
          新建团队
        </Button>
      </div>

      {/* 团队卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {teams.map(team => (
          <div key={team.id} className="space-y-0">
            {/* 团队卡片 */}
            <div
              className={`${cardStyle.interactive} ${expandedTeam === team.id ? 'border-primary/30 shadow-md' : ''}`}
              onClick={() => handleToggleExpand(team.id)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                    <icons.Users className={`${iconSize.md} text-primary`} />
                  </div>
                  <div>
                    <h3 className={heading.card}>{team.name}</h3>
                    <p className="text-xs text-muted-foreground">{team.leader} 负责</p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
                    onClick={e => { e.stopPropagation(); handleOpenEdit(team) }}
                  >
                    <icons.Edit className={iconSize.sm} />
                  </button>
                  <button
                    className="p-1 text-muted-foreground hover:text-destructive rounded transition-colors"
                    onClick={e => { e.stopPropagation(); setDeleteTarget(team.id) }}
                  >
                    <icons.Delete className={iconSize.sm} />
                  </button>
                </div>
              </div>

              <p className="text-sm text-muted-foreground line-clamp-2 mb-3">{team.description}</p>

              <div className="flex items-center justify-between">
                <Badge variant="secondary" className="text-xs">
                  <icons.Users className="w-3 h-3 mr-1" />
                  {team.memberCount} 人
                </Badge>
                <icons.ChevronDown
                  className={`${iconSize.sm} text-muted-foreground transition-transform ${
                    expandedTeam === team.id ? 'rotate-180' : ''
                  }`}
                />
              </div>
            </div>

            {/* 展开的成员列表 */}
            {expandedTeam === team.id && (
              <div className="border border-t-0 border-border rounded-b-xl bg-muted/30 p-4 space-y-2">
                <div className="flex justify-end pb-2">
                  <Button size="sm" variant="outline" onClick={() => handleOpenAddMember(team.id)}>
                    <icons.Plus className={iconSize.sm} />
                    添加成员
                  </Button>
                </div>
                {team.members.map(member => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-background transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium text-primary">
                        {member.name.slice(0, 1)}
                      </div>
                      <div>
                        <span className="text-sm font-medium text-foreground">{member.name}</span>
                        <span className="text-xs text-muted-foreground ml-2">{member.title}</span>
                      </div>
                      {member.role === 'leader' && (
                        <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${statusBadge.info}`}>
                          负责人
                        </Badge>
                      )}
                    </div>
                    {member.role !== 'leader' && (
                      <button
                        className="p-1 text-muted-foreground hover:text-destructive rounded transition-colors"
                        onClick={() => setRemoveMemberTarget({ teamId: team.id, memberId: member.id })}
                      >
                        <icons.X className={iconSize.xs} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 创建/编辑 Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingTeam ? '编辑团队' : '新建团队'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="team-name">团队名称</Label>
              <Input
                id="team-name"
                value={formName}
                onChange={e => setFormName(e.target.value)}
                placeholder="请输入团队名称"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="team-desc">团队描述</Label>
              <Input
                id="team-desc"
                value={formDesc}
                onChange={e => setFormDesc(e.target.value)}
                placeholder="请输入团队描述"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="team-leader">团队负责人</Label>
              <select
                id="team-leader"
                value={selectedLeaderId}
                onChange={(e) => setSelectedLeaderId(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
              >
                <option value="">暂不指定</option>
                {userOptions.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.email})
                  </option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formName.trim() || saving}>
              {saving ? '提交中...' : editingTeam ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={memberDialogOpen} onOpenChange={setMemberDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加团队成员</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="team-member-search">搜索用户</Label>
              <Input
                id="team-member-search"
                value={memberSearch}
                onChange={(e) => setMemberSearch(e.target.value)}
                placeholder="输入姓名或邮箱筛选"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="team-member-user">选择用户</Label>
              <select
                id="team-member-user"
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
              >
                <option value="">
                  {filteredUserOptions.length > 0 ? '请选择用户' : '没有匹配的可添加成员'}
                </option>
                {filteredUserOptions.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.email})
                  </option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMemberDialogOpen(false)} disabled={saving}>
              取消
            </Button>
            <Button onClick={handleAddMember} disabled={!selectedUserId || saving}>
              {saving ? '添加中...' : '添加成员'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="确认删除团队"
        description="删除后团队信息将无法恢复，确定要删除吗？"
        confirmText="确认删除"
        destructive
        onConfirm={handleDeleteConfirm}
      />

      <ConfirmDialog
        open={!!removeMemberTarget}
        onOpenChange={(open) => !open && setRemoveMemberTarget(null)}
        title="确认移除成员"
        description="确定要将此成员从团队中移除吗？"
        confirmText="确认移除"
        destructive
        onConfirm={handleRemoveMemberConfirm}
      />
    </div>
  )
}
