import { useState, useEffect } from'react'
import { motion } from'framer-motion'
import { icons } from'@/lib/icons'
import { adminApi } from'@/lib/api'
import { toast } from'sonner'
import { PageContainer } from'@/components/ui/PageContainer'
import { Button } from'@/components/ui/button'
import { Input } from'@/components/ui/input'
import { Label } from'@/components/ui/label'
import { Badge } from'@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from'@/components/ui/card'
import { Skeleton } from'@/components/ui/skeleton'
import {
 Dialog,
 DialogContent,
 DialogDescription,
 DialogFooter,
 DialogHeader,
 DialogTitle,
} from'@/components/ui/dialog'
import {
 Table,
 TableBody,
 TableCell,
 TableHead,
 TableHeader,
 TableRow,
} from'@/components/ui/table'

interface Org {
 id: string
 name: string
 description?: string
 member_count?: number
 is_active?: boolean
 created_at?: string
 members?: any[]
}

export default function AdminOrgs() {
 const [loading, setLoading] = useState(true)
 const [orgs, setOrgs] = useState<Org[]>([])
 const [createOpen, setCreateOpen] = useState(false)
 const [editOrg, setEditOrg] = useState<Org | null>(null)
 const [viewOrg, setViewOrg] = useState<Org | null>(null)
 const [form, setForm] = useState({ name:'', description:'' })
 const [submitting, setSubmitting] = useState(false)

 useEffect(() => {
 loadOrgs()
 }, [])

 const loadOrgs = async () => {
 setLoading(true)
 try {
 const data = await adminApi.listOrgs()
 setOrgs(Array.isArray(data) ? data : [])
 } catch {
 toast.error('加载组织列表失败')
 } finally {
 setLoading(false)
 }
 }

 const handleCreate = async () => {
 if (!form.name) {
 toast.error('请输入组织名称')
 return
 }
 setSubmitting(true)
 try {
 await adminApi.createOrg(form)
 toast.success('组织创建成功')
 setCreateOpen(false)
 setForm({ name:'', description:'' })
 loadOrgs()
 } catch (e: any) {
 toast.error(e.message ||'创建失败')
 } finally {
 setSubmitting(false)
 }
 }

 const handleEdit = async () => {
 if (!editOrg) return
 setSubmitting(true)
 try {
 await adminApi.updateOrg(editOrg.id, form)
 toast.success('组织信息已更新')
 setEditOrg(null)
 setForm({ name:'', description:'' })
 loadOrgs()
 } catch (e: any) {
 toast.error(e.message ||'更新失败')
 } finally {
 setSubmitting(false)
 }
 }

 const openEdit = (org: Org) => {
 setEditOrg(org)
 setForm({ name: org.name, description: org.description ||'' })
 }

 if (loading) {
 return (
 <PageContainer showHeader={false}>
 <Skeleton className="h-8 w-48" />
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {Array.from({ length: 3 }).map((_, i) => (
 <Skeleton key={i} className="h-44 rounded-xl" />
 ))}
 </div>
 </PageContainer>
 )
 }

 return (
 <PageContainer
 title="组织管理"
 description="管理系统中的组织和团队"
 actions={
 <Button onClick={() => setCreateOpen(true)} className="gap-2">
 <icons.Plus className="w-4 h-4" />
 创建组织
 </Button>
 }
 >
 {/* 组织卡片列表 */}
 {orgs.length > 0 ? (
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {orgs.map((org, index) => (
 <motion.div
 key={org.id}
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: index * 0.08 }}
 >
 <Card className="hover:shadow-md transition-shadow">
 <CardHeader className="pb-3">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="p-2.5 rounded-lg bg-info/10">
 <icons.Building className="w-5 h-5 text-info" />
 </div>
 <div>
 <CardTitle className="text-base">{org.name}</CardTitle>
 {org.description && (
 <CardDescription className="text-xs mt-0.5 line-clamp-1">
 {org.description}
 </CardDescription>
 )}
 </div>
 </div>
 <Badge
 variant={org.is_active !== false ?'default' :'destructive'}
 className="text-xs"
 >
 {org.is_active !== false ?'活跃' :'停用'}
 </Badge>
 </div>
 </CardHeader>
 <CardContent className="pt-0">
 <div className="flex items-center gap-4 text-xs text-muted-foreground mb-4">
 <span className="flex items-center gap-1">
 <icons.Users className="w-3.5 h-3.5" />
 {org.member_count || 0} 成员
 </span>
 {org.created_at && (
 <span className="flex items-center gap-1">
 <icons.Calendar className="w-3.5 h-3.5" />
 {new Date(org.created_at).toLocaleDateString('zh-CN')}
 </span>
 )}
 </div>
 <div className="flex gap-2">
 <Button
 variant="outline"
 size="sm"
 className="flex-1 gap-1"
 onClick={() => setViewOrg(org)}
 >
 <icons.Eye className="w-3.5 h-3.5" />
 成员
 </Button>
 <Button
 variant="outline"
 size="sm"
 className="flex-1 gap-1"
 onClick={() => openEdit(org)}
 >
 <icons.Edit className="w-3.5 h-3.5" />
 编辑
 </Button>
 </div>
 </CardContent>
 </Card>
 </motion.div>
 ))}
 </div>
 ) : (
 <Card>
 <CardContent className="py-16 text-center">
 <icons.Building className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
 <p className="text-muted-foreground">暂无组织，请点击上方按钮创建</p>
 </CardContent>
 </Card>
 )}

 {/* 创建组织对话框 */}
 <Dialog open={createOpen} onOpenChange={setCreateOpen}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>创建组织</DialogTitle>
 <DialogDescription>添加一个新的组织或团队</DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="space-y-2">
 <Label>组织名称</Label>
 <Input
 placeholder="请输入组织名称"
 value={form.name}
 onChange={(e) => setForm({ ...form, name: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>描述（可选）</Label>
 <Input
 placeholder="请输入组织描述"
 value={form.description}
 onChange={(e) => setForm({ ...form, description: e.target.value })}
 />
 </div>
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setCreateOpen(false)}>
 取消
 </Button>
 <Button onClick={handleCreate} disabled={submitting}>
 {submitting ?'创建中...' :'创建'}
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>

 {/* 编辑组织对话框 */}
 <Dialog open={!!editOrg} onOpenChange={() => setEditOrg(null)}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>编辑组织</DialogTitle>
 <DialogDescription>修改组织基本信息</DialogDescription>
 </DialogHeader>
 <div className="space-y-4">
 <div className="space-y-2">
 <Label>组织名称</Label>
 <Input
 value={form.name}
 onChange={(e) => setForm({ ...form, name: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>描述</Label>
 <Input
 value={form.description}
 onChange={(e) => setForm({ ...form, description: e.target.value })}
 />
 </div>
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => setEditOrg(null)}>
 取消
 </Button>
 <Button onClick={handleEdit} disabled={submitting}>
 {submitting ?'保存中...' :'保存'}
 </Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>

 {/* 查看成员对话框 */}
 <Dialog open={!!viewOrg} onOpenChange={() => setViewOrg(null)}>
 <DialogContent className="max-w-lg">
 <DialogHeader>
 <DialogTitle>{viewOrg?.name} — 成员列表</DialogTitle>
 <DialogDescription>
 该组织共有 {viewOrg?.member_count || viewOrg?.members?.length || 0} 名成员
 </DialogDescription>
 </DialogHeader>
 <div className="max-h-[400px] overflow-auto">
 {viewOrg?.members && viewOrg.members.length > 0 ? (
 <Table>
 <TableHeader>
 <TableRow>
 <TableHead>姓名</TableHead>
 <TableHead>邮箱</TableHead>
 <TableHead>角色</TableHead>
 </TableRow>
 </TableHeader>
 <TableBody>
 {viewOrg.members.map((m: any) => (
 <TableRow key={m.id}>
 <TableCell className="font-medium">{m.name}</TableCell>
 <TableCell className="text-muted-foreground">{m.email}</TableCell>
 <TableCell>
 <Badge variant="outline" className="text-xs">
 {m.role ||'成员'}
 </Badge>
 </TableCell>
 </TableRow>
 ))}
 </TableBody>
 </Table>
 ) : (
 <div className="py-8 text-center text-muted-foreground text-sm">
 暂无成员数据
 </div>
 )}
 </div>
 </DialogContent>
 </Dialog>
 </PageContainer>
 )
}
