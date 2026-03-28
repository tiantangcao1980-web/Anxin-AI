/**
 * TeamManagement - 团队管理组件
 *
 * - 团队列表（卡片网格）：名称、描述、负责人、成员数
 * - 点击团队卡展开成员列表
 * - 创建/编辑团队 Dialog
 * - 添加/移除成员
 * 全部 mock 数据
 */

import { useState } from 'react'
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
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

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

// @mock-data FALLBACK: 后端就绪后从 /firm/teams API 获取
const MOCK_TEAMS: Team[] = [
  {
    id: '1',
    name: '公司法务部',
    description: '处理公司治理、股权架构、并购重组等事务',
    leader: '张明远',
    memberCount: 6,
    members: [
      { id: 'u1', name: '张明远', role: 'leader', title: '高级合伙人' },
      { id: 'u2', name: '李思晨', role: 'member', title: '律师' },
      { id: 'u3', name: '王浩然', role: 'member', title: '律师' },
      { id: 'u4', name: '赵雨萱', role: 'member', title: '实习律师' },
      { id: 'u5', name: '陈志强', role: 'member', title: '律师助理' },
      { id: 'u6', name: '周美琳', role: 'member', title: '律师助理' },
    ],
  },
  {
    id: '2',
    name: '知识产权组',
    description: '专利申请、商标注册、著作权保护、侵权诉讼',
    leader: '刘婉清',
    memberCount: 4,
    members: [
      { id: 'u7', name: '刘婉清', role: 'leader', title: '合伙人' },
      { id: 'u8', name: '孙晓峰', role: 'member', title: '律师' },
      { id: 'u9', name: '吴丽华', role: 'member', title: '律师' },
      { id: 'u10', name: '郑浩宇', role: 'member', title: '实习律师' },
    ],
  },
  {
    id: '3',
    name: '劳动法团队',
    description: '劳动争议仲裁、用工合规、员工关系管理',
    leader: '黄建国',
    memberCount: 3,
    members: [
      { id: 'u11', name: '黄建国', role: 'leader', title: '高级律师' },
      { id: 'u12', name: '林思远', role: 'member', title: '律师' },
      { id: 'u13', name: '许文博', role: 'member', title: '律师助理' },
    ],
  },
  {
    id: '4',
    name: '诉讼仲裁部',
    description: '民商事诉讼、仲裁案件代理、执行申请',
    leader: '陈伟达',
    memberCount: 5,
    members: [
      { id: 'u14', name: '陈伟达', role: 'leader', title: '合伙人' },
      { id: 'u15', name: '杨丽娜', role: 'member', title: '高级律师' },
      { id: 'u16', name: '韩思远', role: 'member', title: '律师' },
      { id: 'u17', name: '马小红', role: 'member', title: '律师' },
      { id: 'u18', name: '朱文杰', role: 'member', title: '实习律师' },
    ],
  },
]

// ========== 组件 ==========

export default function TeamManagement() {
  const [teams, setTeams] = useState<Team[]>(MOCK_TEAMS)
  const [expandedTeam, setExpandedTeam] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTeam, setEditingTeam] = useState<Team | null>(null)
  const [formName, setFormName] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [removeMemberTarget, setRemoveMemberTarget] = useState<{ teamId: string; memberId: string } | null>(null)

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
