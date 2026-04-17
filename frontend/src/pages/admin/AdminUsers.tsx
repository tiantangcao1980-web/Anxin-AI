import { useState, useEffect, useCallback } from'react'
import { motion } from'framer-motion'
import { icons } from'@/lib/icons'
import { adminApi } from'@/lib/api'
import { toast } from'sonner'
import { PageContainer } from'@/components/ui/PageContainer'
import { Button } from'@/components/ui/button'
import { Input } from'@/components/ui/input'
import { Label } from'@/components/ui/label'
import { Badge } from'@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from'@/components/ui/card'
import { Skeleton } from'@/components/ui/skeleton'
import {
 Table,
 TableBody,
 TableCell,
 TableHead,
 TableHeader,
 TableRow,
} from'@/components/ui/table'
import {
 Dialog,
 DialogContent,
 DialogDescription,
 DialogFooter,
 DialogHeader,
 DialogTitle,
} from'@/components/ui/dialog'
import {
 AlertDialog,
 AlertDialogAction,
 AlertDialogCancel,
 AlertDialogContent,
 AlertDialogDescription,
 AlertDialogFooter,
 AlertDialogHeader,
 AlertDialogTitle,
} from'@/components/ui/alert-dialog'
import {
 DropdownMenu,
 DropdownMenuContent,
 DropdownMenuItem,
 DropdownMenuSeparator,
 DropdownMenuTrigger,
} from'@/components/ui/dropdown-menu'
import {
 Select,
 SelectContent,
 SelectItem,
 SelectTrigger,
 SelectValue,
} from'@/components/ui/select'

const PAGE_SIZE = 10

const roleMap: Record<string, { label: string; color: string }> = {
 admin: { label:'管理员', color:'bg-warning text-warning-foreground' },
 member: { label:'成员', color:'bg-info text-info-foreground' },
 viewer: { label:'观察者', color:'bg-slate-500 text-white' },
}

export default function AdminUsers() {
 const [loading, setLoading] = useState(true)
 const [users, setUsers] = useState<any[]>([])
 const [total, setTotal] = useState(0)
 const [page, setPage] = useState(0)
 const [search, setSearch] = useState('')
 const [roleFilter, setRoleFilter] = useState<string>('all')
 const [statusFilter, setStatusFilter] = useState<string>('all')

 // Dialogs
 const [createOpen, setCreateOpen] = useState(false)
 const [editOpen, setEditOpen] = useState(false)
 const [editUser, setEditUser] = useState<any>(null)
 const [toggleUser, setToggleUser] = useState<any>(null)
 const [resetPwUser, setResetPwUser] = useState<any>(null)

 // Form state
 const [form, setForm] = useState({
 email:'',
 name:'',
 password:'',
 role:'member',
 })
 const [editForm, setEditForm] = useState({
 name:'',
 email:'',
 role:'member',
 })
 const [newPassword, setNewPassword] = useState('')
 const [submitting, setSubmitting] = useState(false)

 const loadUsers = useCallback(async () => {
 setLoading(true)
 try {
 const params: any = {
 skip: page * PAGE_SIZE,
 limit: PAGE_SIZE,
 }
 if (search) params.search = search
 if (roleFilter !=='all') params.role = roleFilter
 if (statusFilter !=='all') params.is_active = statusFilter ==='active'

 const res = await adminApi.listUsers(params)
 setUsers(res.users || [])
 setTotal(res.total || 0)
 } catch {
 toast.error('加载用户列表失败')
 } finally {
 setLoading(false)
 }
 }, [page, search, roleFilter, statusFilter])

 useEffect(() => {
 loadUsers()
 }, [loadUsers])

 const handleCreate = async () => {
 if (!form.email || !form.name || !form.password) {
 toast.error('请填写完整信息')
 return
 }
 setSubmitting(true)
 try {
 await adminApi.createUser(form)
 toast.success('用户创建成功')
 setCreateOpen(false)
 setForm({ email:'', name:'', password:'', role:'member' })
 loadUsers()
 } catch (e: any) {
 toast.error(e.message ||'创建失败')
 } finally {
 setSubmitting(false)
 }
 }

 const handleEdit = async () => {
 if (!editUser) return
 setSubmitting(true)
 try {
 await adminApi.updateUser(editUser.id, editForm)
 toast.success('用户信息已更新')
 setEditOpen(false)
 setEditUser(null)
 loadUsers()
 } catch (e: any) {
 toast.error(e.message ||'更新失败')
 } finally {
 setSubmitting(false)
 }
 }

 const handleToggleStatus = async () => {
 if (!toggleUser) return
 try {
 await adminApi.toggleUserStatus(toggleUser.id)
 toast.success(toggleUser.is_active ?'用户已禁用' :'用户已启用')
 setToggleUser(null)
 loadUsers()
 } catch (e: any) {
 toast.error(e.message ||'操作失败')
 }
 }

 const handleResetPassword = async () => {
 if (!resetPwUser || !newPassword) {
 toast.error('请输入新密码')
 return
 }
 try {
 await adminApi.resetPassword(resetPwUser.id, { new_password: newPassword })
 toast.success('密码已重置')
 setResetPwUser(null)
 setNewPassword('')
 } catch (e: any) {
 toast.error(e.message ||'重置失败')
 }
 }

 const openEditDialog = (user: any) => {
 setEditUser(user)
 setEditForm({ name: user.name, email: user.email, role: user.role })
 setEditOpen(true)
 }

 const totalPages = Math.ceil(total / PAGE_SIZE)

 return (
 <PageContainer
 title="用户管理"
 description="管理系统用户账号、角色和状态"
 actions={
 <Button onClick={() => setCreateOpen(true)} className="gap-2">
 <icons.Plus className="w-4 h-4" />
 新建用户
 </Button>
 }
 >
 {/* 筛选栏 */}
 <Card>
 <CardContent className="pt-4 pb-4">
 <div className="flex flex-wrap items-center gap-4">
 <div className="flex-1 min-w-[200px]">
 <div className="relative">
 <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
 <Input
 placeholder="搜索用户名或邮箱..."
 value={search}
 onChange={(e) => {
 setSearch(e.target.value)
 setPage(0)
 }}
 className="pl-9"
 />
 </div>
 </div>
 <Select
 value={roleFilter}
 onValueChange={(v) => {
 setRoleFilter(v)
 setPage(0)
 }}
 >
 <SelectTrigger className="w-[140px]">
 <SelectValue placeholder="角色筛选" />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="all">全部角色</SelectItem>
 <SelectItem value="admin">管理员</SelectItem>
 <SelectItem value="member">成员</SelectItem>
 <SelectItem value="viewer">观察者</SelectItem>
 </SelectContent>
 </Select>
 <Select
 value={statusFilter}
 onValueChange={(v) => {
 setStatusFilter(v)
 setPage(0)
 }}
 >
 <SelectTrigger className="w-[140px]">
 <SelectValue placeholder="状态筛选" />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="all">全部状态</SelectItem>
 <SelectItem value="active">已启用</SelectItem>
 <SelectItem value="inactive">已禁用</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </CardContent>
 </Card>

 {/* 用户表格 */}
 <Card>
 <CardContent className="p-0">
 {loading ? (
 <div className="p-6 space-y-4">
 {Array.from({ length: 5 }).map((_, i) => (
 <Skeleton key={i} className="h-12 w-full" />
 ))}
 </div>
 ) : (
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>用户</TableHead>
 <TableHead>邮箱</TableHead>
 <TableHead>角色</TableHead>
 <TableHead>状态</TableHead>
 <TableHead>登录方式</TableHead>
 <TableHead>创建时间</TableHead>
 <TableHead className="text-right">操作</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {users.length > 0 ? (
 users.map((user: any) => (
 <TableRow key={user.id}>
 <TableCell>
 <div className="flex items-center gap-3">
 <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium text-primary">
 {user.avatar_url ? (
 <img
 src={user.avatar_url}
 alt=""
 className="w-8 h-8 rounded-full object-cover"
 />
 ) : (
 user.name?.charAt(0) ||'?'
 )}
 </div>
 <span className="font-medium">{user.name}</span>
 </div>
 </TableCell>
 <TableCell className="text-muted-foreground">{user.email}</TableCell>
 <TableCell>
 <Badge className={`text-xs ${roleMap[user.role]?.color ||'bg-slate-400 text-white'}`}>
 {roleMap[user.role]?.label || user.role}
 </Badge>
 </TableCell>
 <TableCell>
 <Badge
 variant={user.is_active !== false ?'default' :'destructive'}
 className="text-xs"
 >
 {user.is_active !== false ?'已启用' :'已禁用'}
 </Badge>
 </TableCell>
 <TableCell className="text-muted-foreground text-sm">
 {user.login_type ||'密码'}
 </TableCell>
 <TableCell className="text-muted-foreground text-sm">
 {user.created_at
 ? new Date(user.created_at).toLocaleDateString('zh-CN')
 :'--'}
 </TableCell>
 <TableCell className="text-right">
 <DropdownMenu>
 <DropdownMenuTrigger asChild>
 <Button variant="ghost" size="sm">
 <icons.MoreHorizontal className="w-4 h-4" />
 </Button>
 </DropdownMenuTrigger>
 <DropdownMenuContent align="end">
 <DropdownMenuItem onClick={() => openEditDialog(user)}>
 <icons.Edit className="w-4 h-4 mr-2" />
 编辑用户
 </DropdownMenuItem>
 <DropdownMenuItem onClick={() => setToggleUser(user)}>
 <icons.Shield className="w-4 h-4 mr-2" />
 {user.is_active !== false ?'禁用用户' :'启用用户'}
 </DropdownMenuItem>
 <DropdownMenuSeparator />
 <DropdownMenuItem onClick={() => setResetPwUser(user)}>
 <icons.Lock className="w-4 h-4 mr-2" />
 重置密码
 </DropdownMenuItem>
 </DropdownMenuContent>
 </DropdownMenu>
 </TableCell>
 </TableRow>
 ))
 ) : (
 <TableRow>
 <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
 暂无用户数据
 </TableCell>
 </TableRow>
 )}
 </TableBody>
 </Table>
 )}
 </CardContent>
 </Card>

 {/* 分页 */}
 {totalPages > 1 && (
 <div className="flex items-center justify-between">
 <p className="text-sm text-muted-foreground">
 共 {total} 条，第 {page + 1}/{totalPages} 页
 </p>
 <div className="flex gap-2">
 <Button
 variant="outline"
 size="sm"
 disabled={page === 0}
 onClick={() => setPage((p) => p - 1)}
 >
 上一页
 </Button>
 <Button
 variant="outline"
 size="sm"
 disabled={page >= totalPages - 1}
 onClick={() => setPage((p) => p + 1)}
 >
 下一页
 </Button>
 </div>
 </div>
 )}

 {/* 新建用户对话框 */}
 <Dialog open={createOpen} onOpenChange={setCreateOpen}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>新建用户</DialogTitle>
 <DialogDescription>创建一个新的系统用户账号</DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="space-y-2">
 <Label>邮箱</Label>
 <Input
 type="email"
 placeholder="user@example.com"
 value={form.email}
 onChange={(e) => setForm({ ...form, email: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>姓名</Label>
 <Input
 placeholder="请输入姓名"
 value={form.name}
 onChange={(e) => setForm({ ...form, name: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>密码</Label>
 <Input
 type="password"
 placeholder="请输入密码"
 value={form.password}
 onChange={(e) => setForm({ ...form, password: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>角色</Label>
 <Select
 value={form.role}
 onValueChange={(v) => setForm({ ...form, role: v })}
 >
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="admin">管理员</SelectItem>
 <SelectItem value="member">成员</SelectItem>
 <SelectItem value="viewer">观察者</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setCreateOpen(false)}>
 取消
 </Button>
 <Button onClick={handleCreate} disabled={submitting}>
 {submitting ?'创建中...' :'创建用户'}
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>

 {/* 编辑用户对话框 */}
 <Dialog open={editOpen} onOpenChange={setEditOpen}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>编辑用户</DialogTitle>
 <DialogDescription>修改用户基本信息</DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="space-y-2">
 <Label>邮箱</Label>
 <Input
 type="email"
 value={editForm.email}
 onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>姓名</Label>
 <Input
 value={editForm.name}
 onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>角色</Label>
 <Select
 value={editForm.role}
 onValueChange={(v) => setEditForm({ ...editForm, role: v })}
 >
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="admin">管理员</SelectItem>
 <SelectItem value="member">成员</SelectItem>
 <SelectItem value="viewer">观察者</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setEditOpen(false)}>
 取消
 </Button>
 <Button onClick={handleEdit} disabled={submitting}>
 {submitting ?'保存中...' :'保存修改'}
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>

 {/* 切换状态确认 */}
 <AlertDialog open={!!toggleUser} onOpenChange={() => setToggleUser(null)}>
 <AlertDialogContent>
 <AlertDialogHeader>
 <AlertDialogTitle>
 确认{toggleUser?.is_active !== false ?'禁用' :'启用'}用户？
 </AlertDialogTitle>
 <AlertDialogDescription>
 {toggleUser?.is_active !== false
 ? `禁用后，用户 ${toggleUser?.name} 将无法登录系统。`
 : `启用后，用户 ${toggleUser?.name} 将可以正常登录系统。`}
 </AlertDialogDescription>
 </AlertDialogHeader>
 <AlertDialogFooter>
 <AlertDialogCancel>取消</AlertDialogCancel>
 <AlertDialogAction onClick={handleToggleStatus}>确认</AlertDialogAction>
 </AlertDialogFooter>
 </AlertDialogContent>
 </AlertDialog>

 {/* 重置密码对话框 */}
 <Dialog open={!!resetPwUser} onOpenChange={() => setResetPwUser(null)}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>重置密码</DialogTitle>
 <DialogDescription>
 为用户 {resetPwUser?.name} 设置新密码
 </DialogDescription>
 </DialogHeader>
 <div className="space-y-2">
 <Label>新密码</Label>
 <Input
 type="password"
 placeholder="请输入新密码"
 value={newPassword}
 onChange={(e) => setNewPassword(e.target.value)}
 />
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setResetPwUser(null)}>
 取消
 </Button>
 <Button onClick={handleResetPassword}>确认重置</Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>
 </PageContainer>
 )
}
