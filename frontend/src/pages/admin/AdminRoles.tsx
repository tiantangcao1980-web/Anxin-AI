import { useState, useEffect } from'react'
import { motion } from'framer-motion'
import { icons } from'@/lib/icons'
import { adminApi } from'@/lib/api'
import { toast } from'sonner'
import { PageContainer } from'@/components/ui/PageContainer'
import { Button } from'@/components/ui/button'
import { Badge } from'@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from'@/components/ui/card'
import { Skeleton } from'@/components/ui/skeleton'
import { Separator } from'@/components/ui/separator'
import { Checkbox } from'@/components/ui/checkbox'

interface RoleInfo {
 key: string
 label: string
 description: string
 icon: any
 color: string
 userCount: number
 permissions: string[]
}

interface PermissionGroup {
 label: string
 permissions: { key: string; label: string }[]
}

const permissionGroups: PermissionGroup[] = [
 {
 label:'用户管理',
 permissions: [
 { key:'users.view', label:'查看用户' },
 { key:'users.create', label:'创建用户' },
 { key:'users.edit', label:'编辑用户' },
 { key:'users.delete', label:'删除用户' },
 ],
 },
 {
 label:'案件管理',
 permissions: [
 { key:'cases.view', label:'查看案件' },
 { key:'cases.create', label:'创建案件' },
 { key:'cases.edit', label:'编辑案件' },
 { key:'cases.delete', label:'删除案件' },
 ],
 },
 {
 label:'合同管理',
 permissions: [
 { key:'contracts.view', label:'查看合同' },
 { key:'contracts.create', label:'创建合同' },
 { key:'contracts.edit', label:'编辑合同' },
 { key:'contracts.review', label:'审查合同' },
 ],
 },
 {
 label:'文档管理',
 permissions: [
 { key:'documents.view', label:'查看文档' },
 { key:'documents.create', label:'创建文档' },
 { key:'documents.edit', label:'编辑文档' },
 { key:'documents.delete', label:'删除文档' },
 ],
 },
 {
 label:'知识库',
 permissions: [
 { key:'knowledge.view', label:'查看知识库' },
 { key:'knowledge.manage', label:'管理知识库' },
 { key:'knowledge.import', label:'导入知识' },
 ],
 },
 {
 label:'系统配置',
 permissions: [
 { key:'system.config', label:'系统设置' },
 { key:'system.audit', label:'审计日志' },
 { key:'system.health', label:'系统监控' },
 { key:'system.roles', label:'角色管理' },
 ],
 },
]

const defaultRoles: RoleInfo[] = [
 {
 key:'admin',
 label:'管理员',
 description:'拥有系统全部权限，可管理所有用户和配置',
 icon: icons.Shield,
 color:'text-warning',
 userCount: 0,
 permissions: permissionGroups.flatMap((g) => g.permissions.map((p) => p.key)),
 },
 {
 key:'member',
 label:'成员',
 description:'可使用核心业务功能，不可管理系统配置',
 icon: icons.Users,
 color:'text-info',
 userCount: 0,
 permissions: [
'cases.view','cases.create','cases.edit',
'contracts.view','contracts.create','contracts.edit','contracts.review',
'documents.view','documents.create','documents.edit',
'knowledge.view',
 ],
 },
 {
 key:'viewer',
 label:'观察者',
 description:'仅可查看数据，不可编辑或创建',
 icon: icons.Eye,
 color:'text-slate-500',
 userCount: 0,
 permissions: [
'users.view','cases.view','contracts.view','documents.view','knowledge.view',
 ],
 },
]

export default function AdminRoles() {
 const [loading, setLoading] = useState(true)
 const [roles, setRoles] = useState<RoleInfo[]>(defaultRoles)
 const [selectedRole, setSelectedRole] = useState<string>('admin')
 const [saving, setSaving] = useState(false)

 useEffect(() => {
 loadRoles()
 }, [])

 const loadRoles = async () => {
 setLoading(true)
 try {
 const data = await adminApi.listRoles()
 if (Array.isArray(data) && data.length > 0) {
 setRoles(
 defaultRoles.map((dr) => {
 const remote = data.find((r: any) => r.key === dr.key || r.name === dr.key)
 return remote
 ? {
 ...dr,
 userCount: remote.user_count || 0,
 permissions: remote.permissions || dr.permissions,
 }
 : dr
 })
 )
 }
 } catch {
 // Use defaults silently
 } finally {
 setLoading(false)
 }
 }

 const currentRole = roles.find((r) => r.key === selectedRole) || roles[0]

 const togglePermission = (permKey: string) => {
 setRoles((prev) =>
 prev.map((r) => {
 if (r.key !== selectedRole) return r
 const has = r.permissions.includes(permKey)
 return {
 ...r,
 permissions: has
 ? r.permissions.filter((p) => p !== permKey)
 : [...r.permissions, permKey],
 }
 })
 )
 }

 const handleSave = async () => {
 setSaving(true)
 try {
 await adminApi.updateRolePermissions(selectedRole, currentRole.permissions)
 toast.success('权限已保存')
 } catch (e: any) {
 toast.error(e.message ||'保存失败')
 } finally {
 setSaving(false)
 }
 }

 if (loading) {
 return (
 <PageContainer showHeader={false}>
 <Skeleton className="h-8 w-48" />
 <div className="grid grid-cols-3 gap-4">
 {Array.from({ length: 3 }).map((_, i) => (
 <Skeleton key={i} className="h-32 rounded-xl" />
 ))}
 </div>
 <Skeleton className="h-96 rounded-xl" />
 </PageContainer>
 )
 }

 return (
 <PageContainer
 title="角色管理"
 description="管理系统角色及其对应的功能权限"
 >
 {/* 角色卡片 */}
 <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
 {roles.map((role, index) => {
 const Icon = role.icon
 const isSelected = selectedRole === role.key
 return (
 <motion.div
 key={role.key}
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: index * 0.1 }}
 >
 <Card
 className={`cursor-pointer transition-all hover:shadow-md ${
 isSelected ?'ring-2 ring-primary shadow-md' :''
 }`}
 onClick={() => setSelectedRole(role.key)}
 >
 <CardHeader className="pb-3">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className={`p-2 rounded-lg bg-muted ${role.color}`}>
 <Icon className="w-5 h-5" />
 </div>
 <div>
 <CardTitle className="text-base">{role.label}</CardTitle>
 <CardDescription className="text-xs mt-0.5">
 {role.key}
 </CardDescription>
 </div>
 </div>
 {isSelected && (
 <Badge className="bg-primary text-primary-foreground text-xs">
 已选择
 </Badge>
 )}
 </div>
 </CardHeader>
 <CardContent className="pt-0">
 <p className="text-sm text-muted-foreground">{role.description}</p>
 <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
 <span className="flex items-center gap-1">
 <icons.Users className="w-3.5 h-3.5" />
 {role.userCount} 用户
 </span>
 <span className="flex items-center gap-1">
 <icons.Shield className="w-3.5 h-3.5" />
 {role.permissions.length} 权限
 </span>
 </div>
 </CardContent>
 </Card>
 </motion.div>
 )
 })}
 </div>

 {/* 权限矩阵 */}
 <Card>
 <CardHeader>
 <div className="flex items-center justify-between">
 <div>
 <CardTitle className="text-base">
 {currentRole.label} — 权限配置
 </CardTitle>
 <CardDescription className="mt-1">
 勾选或取消权限项来调整该角色的访问权限
 </CardDescription>
 </div>
 <Button onClick={handleSave} disabled={saving} className="gap-2">
 <icons.Check className="w-4 h-4" />
 {saving ?'保存中...' :'保存权限'}
 </Button>
 </div>
 </CardHeader>
 <CardContent>
 <div className="space-y-6">
 {permissionGroups.map((group) => (
 <div key={group.label}>
 <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
 <icons.FolderOpen className="w-4 h-4 text-muted-foreground" />
 {group.label}
 </h4>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
 {group.permissions.map((perm) => {
 const checked = currentRole.permissions.includes(perm.key)
 return (
 <label
 key={perm.key}
 className={`flex items-center gap-2.5 p-3 rounded-lg border cursor-pointer transition-colors ${
 checked
 ?'border-primary/50 bg-primary/5'
 :'border-border hover:bg-muted/50'
 }`}
 >
 <Checkbox
 checked={checked}
 onCheckedChange={() => togglePermission(perm.key)}
 />
 <span className="text-sm">{perm.label}</span>
 </label>
 )
 })}
 </div>
 <Separator className="mt-6" />
 </div>
 ))}
 </div>
 </CardContent>
 </Card>
 </PageContainer>
 )
}
