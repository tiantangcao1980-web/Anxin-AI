/**
 * CreateConversationDialog - 创建新对话弹窗
 *
 * 从后端搜索真实用户，支持私聊和群聊两种模式。
 * 搜索使用防抖，避免频繁请求。
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { inputStyle, iconSize } from '@/lib/design-tokens'
import { icons } from '@/lib/icons'
import { imApi } from '@/lib/api'
import { useIMStore } from '@/lib/store'
import { toast } from 'sonner'

interface CreateConversationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated?: (conversationId: string) => void
}

interface UserOption {
  id: string
  name: string
  email?: string
  avatar_url?: string
  department?: string
  role?: string
}

export function CreateConversationDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateConversationDialogProps) {
  const [mode, setMode] = useState<'private' | 'group'>('private')
  const [search, setSearch] = useState('')
  const [title, setTitle] = useState('')
  const [selected, setSelected] = useState<UserOption[]>([])
  const [creating, setCreating] = useState(false)
  const [users, setUsers] = useState<UserOption[]>([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const addConversation = useIMStore((s) => s.addConversation)
  const setActiveConversation = useIMStore((s) => s.setActiveConversation)

  // 搜索用户（防抖）
  const fetchUsers = useCallback(async (query: string) => {
    setLoadingUsers(true)
    try {
      const res = await imApi.searchUsers(query)
      if (res?.data) {
        setUsers(res.data)
      }
    } catch {
      console.error('[IM] 搜索用户失败')
    } finally {
      setLoadingUsers(false)
    }
  }, [])

  useEffect(() => {
    if (!open) return
    fetchUsers('')
  }, [open, fetchUsers])

  useEffect(() => {
    if (!open) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      fetchUsers(search)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [search, open, fetchUsers])

  const toggleUser = (user: UserOption) => {
    if (mode === 'private') {
      setSelected((prev) =>
        prev.some((u) => u.id === user.id) ? [] : [user]
      )
    } else {
      setSelected((prev) =>
        prev.some((u) => u.id === user.id)
          ? prev.filter((u) => u.id !== user.id)
          : [...prev, user]
      )
    }
  }

  const handleCreate = async () => {
    if (selected.length === 0) {
      toast.warning('请选择至少一位成员')
      return
    }

    setCreating(true)
    try {
      const res = await imApi.createConversation({
        type: mode,
        participant_ids: selected.map((u) => u.id),
        title: mode === 'group' ? title || `群聊（${selected.length + 1}人）` : undefined,
      })

      if (res?.data) {
        addConversation(res.data)
        setActiveConversation(res.data.id)
        onCreated?.(res.data.id)
        toast.success('对话创建成功')
        onOpenChange(false)
        resetForm()
      } else {
        toast.error(res?.message || '创建对话失败')
      }
    } catch (err: any) {
      toast.error(err?.message || '创建对话失败，请重试')
    } finally {
      setCreating(false)
    }
  }

  const resetForm = () => {
    setMode('private')
    setSearch('')
    setTitle('')
    setSelected([])
    setUsers([])
  }

  useEffect(() => {
    if (!open) resetForm()
  }, [open])

  const getRoleLabel = (role?: string) => {
    const map: Record<string, string> = {
      admin: '管理员',
      member: '成员',
      lawyer: '律师',
      partner: '合伙人',
    }
    return role ? map[role] || role : ''
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>新建对话</DialogTitle>
        </DialogHeader>

        {/* 对话类型切换 */}
        <div className="flex gap-1 p-1 bg-muted/50 rounded-lg">
          <button
            className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-colors ${
              mode === 'private'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => {
              setMode('private')
              if (selected.length > 1) setSelected([])
            }}
          >
            <icons.User className={`${iconSize.sm} inline mr-1 -mt-0.5`} />
            私聊
          </button>
          <button
            className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-colors ${
              mode === 'group'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setMode('group')}
          >
            <icons.Users className={`${iconSize.sm} inline mr-1 -mt-0.5`} />
            群聊
          </button>
        </div>

        {/* 群聊名称 */}
        {mode === 'group' && (
          <input
            className={inputStyle.search}
            placeholder="群聊名称（可选）"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        )}

        {/* 搜索成员 */}
        <div className="relative">
          <icons.Search
            className={`absolute left-2.5 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`}
          />
          <input
            className={`${inputStyle.search} pl-8`}
            placeholder="搜索姓名或邮箱..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* 已选择标签 */}
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {selected.map((u) => (
              <Badge
                key={u.id}
                variant="secondary"
                className="gap-1 cursor-pointer hover:bg-destructive/10 hover:text-destructive transition-colors"
                onClick={() => toggleUser(u)}
              >
                {u.name}
                <icons.Close className="w-3 h-3" />
              </Badge>
            ))}
          </div>
        )}

        {/* 成员列表 */}
        <ScrollArea className="max-h-60">
          {loadingUsers ? (
            <div className="space-y-2 px-1">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-3 py-2">
                  <Skeleton className="w-8 h-8 rounded-full shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3.5 w-20" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
              ))}
            </div>
          ) : users.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <icons.Users className={`${iconSize.lg} mb-2 opacity-30`} />
              <p className="text-sm">{search ? '未找到匹配的用户' : '暂无可用成员'}</p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {users.map((user) => {
                const isSelected = selected.some((s) => s.id === user.id)
                return (
                  <div
                    key={user.id}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-primary/5 text-primary'
                        : 'hover:bg-muted text-foreground'
                    }`}
                    onClick={() => toggleUser(user)}
                  >
                    {/* 头像 */}
                    {user.avatar_url ? (
                      <img
                        src={user.avatar_url}
                        alt={user.name}
                        className="w-8 h-8 rounded-full shrink-0 object-cover"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium text-primary shrink-0">
                        {user.name.charAt(0)}
                      </div>
                    )}

                    {/* 信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-medium truncate">{user.name}</span>
                        {user.department && (
                          <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                            {user.department}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate">
                        {user.email}
                        {user.role && ` · ${getRoleLabel(user.role)}`}
                      </p>
                    </div>

                    {/* 选中标记 */}
                    {isSelected && <icons.Check className={`${iconSize.sm} text-primary shrink-0`} />}
                  </div>
                )
              })}
            </div>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button
            onClick={handleCreate}
            disabled={selected.length === 0 || creating}
          >
            {creating ? (
              <icons.Loader2 className={`${iconSize.sm} animate-spin mr-1.5`} />
            ) : (
              <icons.Add className={`${iconSize.sm} mr-1.5`} />
            )}
            {mode === 'private'
              ? '开始私聊'
              : `创建群聊${selected.length > 0 ? `（${selected.length}人）` : ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
