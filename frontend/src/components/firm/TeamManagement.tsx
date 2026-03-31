/**
 * TeamManagement - 团队管理组件
 *
 * - 团队列表（卡片网格）：名称、描述、负责人、成员数
 * - 点击团队卡展开成员列表
 * - 创建/编辑团队 Dialog
 * - 添加/移除成员
 * 全部 mock 数据
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
import { firmApi } from '@/lib/api'

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
  memberCount: number
  members: TeamMember[]
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
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [removeMemberTarget, setRemoveMemberTarget] = useState<{ teamId: string; memberId: string } | null>(null)

  useEffect(() => {
    let cancelled = false
    async function fetchTeams() {
      try {
        setLoading(true)
        setError(null)
        const data = await firmApi.listTeams()
        if (cancelled) return
        const items = Array.isArray(data) ? data : (data.items ?? data.teams ?? [])
        setTeams(
          items.map((t: any) => ({
            id: t.id,
            name: t.name ?? '',
            description: t.description ?? '',
            leader: t.leader ?? t.leader_name ?? '待指定',
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
        if (!cancelled) setError(err.message || '加载团队数据失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchTeams()
    return () => { cancelled = true }
  }, [])

  const handleToggleExpand = (teamId: string) => {
    setExpandedTeam(expandedTeam === teamId ? null : teamId)
  }

  const handleOpenCreate = () => {
    setEditingTeam(null)
    setFormName('')
    setFormDesc('')
    setDialogOpen(true)
  }

  const handleOpenEdit = (team: Team) => {
    setEditingTeam(team)
    setFormName(team.name)
    setFormDesc(team.description)
    setDialogOpen(true)
  }

  const handleSave = () => {
    if (!formName.trim()) return
    if (editingTeam) {
      setTeams(prev =>
        prev.map(t =>
          t.id === editingTeam.id ? { ...t, name: formName, description: formDesc } : t,
        ),
      )
    } else {
      const newTeam: Team = {
        id: `new-${Date.now()}`,
        name: formName,
        description: formDesc,
        leader: '待指定',
        memberCount: 0,
        members: [],
      }
      setTeams(prev => [newTeam, ...prev])
    }
    setDialogOpen(false)
  }

  const handleDeleteConfirm = () => {
    if (!deleteTarget) return
    setTeams(prev => prev.filter(t => t.id !== deleteTarget))
    if (expandedTeam === deleteTarget) setExpandedTeam(null)
    setDeleteTarget(null)
  }

  const handleRemoveMemberConfirm = () => {
    if (!removeMemberTarget) return
    const { teamId, memberId } = removeMemberTarget
    handleRemoveMember(teamId, memberId)
    setRemoveMemberTarget(null)
  }

  const handleRemoveMember = (teamId: string, memberId: string) => {
    setTeams(prev =>
      prev.map(t => {
        if (t.id !== teamId) return t
        const newMembers = t.members.filter(m => m.id !== memberId)
        return { ...t, members: newMembers, memberCount: newMembers.length }
      }),
    )
  }

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
        <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formName.trim()}>
              {editingTeam ? '保存' : '创建'}
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
