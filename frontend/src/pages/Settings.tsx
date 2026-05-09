import { useState, useEffect } from'react'
import { useNavigate, useSearchParams } from'react-router-dom'
import { icons } from'@/lib/icons'
import { toast } from'sonner'
import { cardStyle, buttonStyle, heading, statusBadge, iconSize, inputStyle } from'@/lib/design-tokens'
import { PageContainer } from'@/components/ui/PageContainer'

import { Button } from'@/components/ui/button'
import { Input } from'@/components/ui/input'
import { Label } from'@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from'@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from'@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from'@/components/ui/select'
import { Switch } from'@/components/ui/switch'
import { Badge } from'@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from'@/components/ui/dialog'
import { ScrollArea } from'@/components/ui/scroll-area'
import { Separator } from'@/components/ui/separator'

import { llmApi, mcpApi, authApi, notificationsApi, LLMConfig, LLMProvider, McpServerConfig, McpServerCreate, NotificationPreference } from'@/lib/api'
import { useAuthStore, useUIStore } from'@/lib/store'
import { ErrorState, LoadingState } from'@/components/common'
import { usePermission } from'@/hooks/usePermission'
import { DesktopWorkstationPanel } from'@/components/desktop/DesktopWorkstationPanel'
import { buildLlmConfigSavePayload, getLlmCredentialSummary } from './llmSettingsModel'
import { buildMcpSavePayload, getPersistedEnvKeys, maskMcpEnvValue } from './mcpSettingsModel'
import { normalizeSettingsTab } from'./settingsTabs'

export default function Settings() {
 const [searchParams, setSearchParams] = useSearchParams()
 const [activeTab, setActiveTab] = useState(() => normalizeSettingsTab(searchParams.get('tab')))

 useEffect(() => {
 const rawTab = searchParams.get('tab')
 const normalizedTab = normalizeSettingsTab(rawTab)
 setActiveTab(normalizedTab)
 if (rawTab && rawTab !== normalizedTab) {
 setSearchParams(normalizedTab ==='profile' ? {} : { tab: normalizedTab }, { replace: true })
 }
 }, [searchParams, setSearchParams])

 const handleTabChange = (value: string) => {
 const nextTab = normalizeSettingsTab(value)
 setActiveTab(nextTab)
 setSearchParams(nextTab ==='profile' ? {} : { tab: nextTab }, { replace: true })
 }

 return (
 <PageContainer
 title="我的设置"
 description="管理个人账号、本机运行和通知偏好；组织级模型、工具和系统集成统一进入治理后台"
 className="box-border w-[100dvw] min-w-0 max-w-[100dvw] overflow-hidden lg:w-full lg:max-w-full"
 >
 <Tabs value={activeTab} onValueChange={handleTabChange} className="min-w-0 space-y-4 overflow-hidden">
 <TabsList className="min-w-0 max-w-full w-full justify-start overflow-x-auto scrollbar-hide sm:w-auto">
 <TabsTrigger value="profile" className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
 <icons.User className={`${iconSize.sm} shrink-0`} />
 <span className="whitespace-nowrap">个人中心</span>
 </TabsTrigger>
 <TabsTrigger value="workstation" className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
 <icons.LayoutDashboard className={`${iconSize.sm} shrink-0`} />
 <span className="whitespace-nowrap">本机运行</span>
 </TabsTrigger>
 <TabsTrigger value="notifications" className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
 <icons.Notification className={`${iconSize.sm} shrink-0`} />
 <span className="whitespace-nowrap">通知偏好</span>
 </TabsTrigger>
 </TabsList>

 <TabsContent value="profile" className="min-w-0 space-y-4">
 <ProfilePanel />
 </TabsContent>

 <TabsContent value="workstation" className="min-w-0 space-y-4">
 <DesktopWorkstationPanel />
 </TabsContent>

 <TabsContent value="notifications" className="min-w-0 space-y-4">
 <NotificationPreferencesPanel />
 </TabsContent>
 </Tabs>
 </PageContainer>
 )
}

// ============ 个人中心面板 ============

function ProfilePanel() {
 const navigate = useNavigate()
 const { user, setUser } = useAuthStore()
 const { isAdmin } = usePermission()
 const { theme, setTheme } = useUIStore()
 const [form, setForm] = useState({
 name: user?.name ||'',
 email: user?.email ||'',
 role: user?.role ||'',
 })
 const [saving, setSaving] = useState(false)
 const [changingPassword, setChangingPassword] = useState(false)
 const [showTwoFactorInfo, setShowTwoFactorInfo] = useState(false)
 const [passwordForm, setPasswordForm] = useState({ current:'', newPassword:'', confirm:'' })

 const handleSaveProfile = async () => {
 if (!form.name.trim()) return toast.error('姓名不能为空')
 setSaving(true)
 try {
 const updated = await authApi.updateProfile({ name: form.name })
 setUser(updated)
 toast.success('个人信息已更新')
 } catch (e: any) {
 toast.error(e.message ||'个人信息更新失败')
 } finally {
 setSaving(false)
 }
 }

 const handleChangePassword = async () => {
 if (!passwordForm.current || !passwordForm.newPassword) return toast.error('请填写完整密码信息')
 if (passwordForm.newPassword !== passwordForm.confirm) return toast.error('两次输入的新密码不一致')
 if (passwordForm.newPassword.length < 8) return toast.error('密码长度不能少于8位')
 try {
 await authApi.changePassword(passwordForm.current, passwordForm.newPassword)
 toast.success('密码修改成功')
 setChangingPassword(false)
 setPasswordForm({ current:'', newPassword:'', confirm:'' })
 } catch (err: any) {
 toast.error(err.message ||'密码修改失败')
 }
 }

 const handleResendVerification = async () => {
 if (!user?.email) {
 toast.error('当前账号没有可用邮箱')
 return
 }
 try {
 await authApi.resendVerification(user.email)
 toast.success('验证邮件已重新发送，请前往登录页完成验证')
 } catch (err: any) {
 toast.error(err.message ||'重发验证邮件失败')
 }
 }

 // 主题由 ThemeProvider 统一管理，此处无需重复

 return (
 <div className="space-y-6 max-w-2xl">
 {/* 基本信息 */}
 <Card className="border-border rounded-xl">
 <CardHeader>
 <CardTitle className={heading.section}>基本信息</CardTitle>
 <CardDescription className={heading.muted}>管理你的个人资料和账户信息</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="flex items-center gap-4 mb-4">
 <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
 <icons.User className="w-8 h-8 text-primary" />
 </div>
 <div>
 <p className="font-medium text-foreground">{user?.name ||'未设置'}</p>
 <p className="text-sm text-muted-foreground">{user?.email ||'未设置'}</p>
 </div>
 </div>

 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>姓名</Label>
 <Input
 value={form.name}
 onChange={e => setForm({ ...form, name: e.target.value })}
 placeholder="请输入姓名"
 />
 </div>
 <div className="space-y-2">
 <Label>邮箱</Label>
 <Input value={form.email} disabled className="bg-muted/50" />
 <p className="text-xs text-muted-foreground">邮箱不可修改</p>
 </div>
 </div>

 <div className="space-y-2">
 <Label>角色</Label>
 <Input value={form.role ||'律师'} disabled className="bg-muted/50" />
 </div>
 </CardContent>
 <CardFooter>
 <Button onClick={handleSaveProfile} disabled={saving}>
 {saving ?'保存中...' :'保存修改'}
 </Button>
 </CardFooter>
 </Card>

 {/* 安全设置 */}
 <Card className="border-border rounded-xl">
 <CardHeader>
 <CardTitle className={heading.section}>安全设置</CardTitle>
 <CardDescription className={heading.muted}>管理密码和安全选项</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className={`${cardStyle.flat} space-y-3`}>
 <div className="flex items-center justify-between">
 <div>
 <p className="text-sm font-medium text-foreground">安全状态</p>
 <p className="text-xs text-muted-foreground">显示当前账号已启用的基础保护能力</p>
 </div>
 <Badge variant={user?.email_verified === false ?'secondary' :'default'}>
 {user?.email_verified === false ?'需补充验证' :'基础保护已启用'}
 </Badge>
 </div>
 <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
 <div className="rounded-lg bg-background border border-border px-3 py-2">
 <p className="text-xs text-muted-foreground">邮箱验证</p>
 <p className="text-sm font-medium text-foreground mt-1">
 {user?.email_verified === false ?'未完成' :'已完成'}
 </p>
 </div>
 <div className="rounded-lg bg-background border border-border px-3 py-2">
 <p className="text-xs text-muted-foreground">两步验证</p>
 <p className="text-sm font-medium text-foreground mt-1">暂未开放</p>
 </div>
 </div>
 </div>

 <div className="flex items-center justify-between">
 <div>
 <p className="text-sm font-medium text-foreground">登录密码</p>
 <p className="text-xs text-muted-foreground">定期修改密码可以提升账户安全性</p>
 </div>
 <Button variant="outline" size="sm" onClick={() => setChangingPassword(true)}>
 修改密码
 </Button>
 </div>
 <Separator />
 <div className="flex items-center justify-between">
 <div>
 <p className="text-sm font-medium text-foreground">两步验证</p>
 <p className="text-xs text-muted-foreground">该能力已进入规划阶段，后续会接入短信或身份验证器</p>
 </div>
 <Button variant="outline" size="sm" onClick={() => setShowTwoFactorInfo(true)}>
 查看说明
 </Button>
 </div>
 </CardContent>
 </Card>

 {isAdmin && (
 <Card className="border-border rounded-xl">
 <CardHeader>
 <CardTitle className={heading.section}>治理入口</CardTitle>
 <CardDescription className={heading.muted}>组织级用户、权限、模型、工具、审计、安全和系统配置统一在治理后台处理</CardDescription>
 </CardHeader>
 <CardContent className="flex items-center justify-between gap-3">
 <div>
 <p className="text-sm font-medium text-foreground">治理后台</p>
 <p className="text-xs text-muted-foreground">跨用户、跨组织和平台级配置不再放在个人设置里</p>
 </div>
 <Button onClick={() => navigate('/admin')}>进入治理后台</Button>
 </CardContent>
 </Card>
 )}

 {/* 外观设置 */}
 <Card className="border-border rounded-xl">
 <CardHeader>
 <CardTitle className={heading.section}>外观设置</CardTitle>
 <CardDescription className={heading.muted}>自定义界面主题和显示偏好</CardDescription>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="flex items-center justify-between">
 <div>
 <p className="text-sm font-medium text-foreground">主题模式</p>
 <p className="text-xs text-muted-foreground">选择浅色、深色或跟随系统</p>
 </div>
 <Select value={theme} onValueChange={(v:'light' |'dark' |'system') => setTheme(v)}>
 <SelectTrigger className="w-32">
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="light">浅色模式</SelectItem>
 <SelectItem value="dark">深色模式</SelectItem>
 <SelectItem value="system">跟随系统</SelectItem>
 </SelectContent>
 </Select>
 </div>
 <Separator />
 <div className="flex items-center justify-between">
 <div>
 <p className="text-sm font-medium text-foreground">语言设置</p>
 <p className="text-xs text-muted-foreground">选择系统界面语言</p>
 </div>
 <Select value="zh-CN" onValueChange={() => toast.info('目前仅支持简体中文')}>
 <SelectTrigger className="w-32">
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="zh-CN">简体中文</SelectItem>
 <SelectItem value="en" disabled>English (即将支持)</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </CardContent>
 </Card>

 {/* 修改密码对话框 */}
 <Dialog open={changingPassword} onOpenChange={setChangingPassword}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>修改密码</DialogTitle>
 <DialogDescription>请输入当前密码和新密码</DialogDescription>
 </DialogHeader>
 <div className="space-y-4 py-4">
 <div className="space-y-2">
 <Label>当前密码</Label>
 <Input
 type="password"
 value={passwordForm.current}
 onChange={e => setPasswordForm({ ...passwordForm, current: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>新密码</Label>
 <Input
 type="password"
 value={passwordForm.newPassword}
 onChange={e => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
 />
 </div>
 <div className="space-y-2">
 <Label>确认新密码</Label>
 <Input
 type="password"
 value={passwordForm.confirm}
 onChange={e => setPasswordForm({ ...passwordForm, confirm: e.target.value })}
 />
 </div>
 </div>
 <DialogFooter>
 <Button variant="ghost" onClick={() => setChangingPassword(false)}>取消</Button>
 <Button onClick={handleChangePassword}>确认修改</Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>

 <Dialog open={showTwoFactorInfo} onOpenChange={setShowTwoFactorInfo}>
 <DialogContent>
 <DialogHeader>
 <DialogTitle>两步验证说明</DialogTitle>
 <DialogDescription>当前账号安全能力状态</DialogDescription>
 </DialogHeader>
 <div className="space-y-4 py-4">
 <div className={cardStyle.flat}>
 <div className="flex items-center gap-2 mb-2">
 <Badge variant="secondary">规划中</Badge>
 <span className="text-sm font-medium text-foreground">尚未开放短信或验证器绑定</span>
 </div>
 <p className="text-sm text-muted-foreground">
 当前版本还未接入短信 OTP 或 TOTP 身份验证器，因此这里不会展示伪开关，避免误导您认为账号已受双重保护。
 </p>
 </div>
 <div className="space-y-2 text-sm text-muted-foreground">
 <p>当前建议：</p>
 <p>1. 定期修改登录密码，并避免与其他系统重复使用。</p>
 <p>2. 确保邮箱已验证，便于后续找回和风险提醒。</p>
 <p>3. 如需更高强度的账户保护，可优先使用私有化部署与本地私有助手模式。</p>
 </div>
 {user?.email_verified === false && (
 <div className="rounded-xl border border-warning/20 bg-warning/10 px-4 py-3 space-y-3">
 <div className="flex items-center gap-2 text-warning">
 <icons.AlertTriangle className="w-4 h-4" />
 <p className="text-sm font-medium">当前邮箱尚未完成验证</p>
 </div>
 <p className="text-sm text-warning/90">
 建议先完成邮箱验证，再等待两步验证能力开放。这样至少能保证找回密码和安全通知链路可用。
 </p>
 <div className="flex flex-wrap gap-2">
 <Button variant="outline" onClick={handleResendVerification}>
 重新发送验证邮件
 </Button>
 <Button onClick={() => navigate('/login')}>
 前往登录页验证
 </Button>
 </div>
 </div>
 )}
 </div>
 <DialogFooter>
 <Button onClick={() => setShowTwoFactorInfo(false)}>我知道了</Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>
 </div>
 )
}

// ============ LLM设置面板组件 ============

type ConnectionPanelScope = 'account' | 'governance'

export function LlmSettingsPanel({ scope = 'governance' }: { scope?: ConnectionPanelScope } = {}) {
 const [configs, setConfigs] = useState<LLMConfig[]>([])
 const [providers, setProviders] = useState<Record<string, LLMProvider>>({})
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)
 const [showDialog, setShowDialog] = useState(false)
 const [editingConfig, setEditingConfig] = useState<LLMConfig | null>(null)
 const isGovernance = scope === 'governance'

 useEffect(() => {
 loadData()
 }, [])

 const loadData = async () => {
 setLoading(true)
 setError(null)
 try {
 const [configsData, providersData] = await Promise.all([
 llmApi.listConfigs(),
 llmApi.getProviders()
 ])
 setConfigs(configsData.items || [])
 setProviders(providersData || {})
 } catch (e: any) {
 setConfigs([])
 setProviders({})
 setError(e.message ||'无法加载模型配置')
 } finally {
 setLoading(false)
 }
 }

 const handleDelete = async (id: string) => {
 if (!confirm('确定要删除这个模型配置吗？')) return
 try {
 await llmApi.deleteConfig(id)
 toast.success('配置已删除')
 loadData()
 } catch (e: any) {
 toast.error(e.message ||'删除失败')
 }
 }

 const handleToggleActive = async (id: string) => {
 try {
 await llmApi.toggleActive(id)
 toast.success('配置状态已更新')
 loadData()
 } catch (e: any) {
 toast.error(e.message ||'更新状态失败')
 }
 }

 const handleSetDefault = async (id: string) => {
 try {
 await llmApi.setDefault(id)
 toast.success('已设置为默认模型')
 loadData()
 } catch (e: any) {
 toast.error(e.message ||'设置默认模型失败')
 }
 }

 if (loading) {
 return (
 <div className={cardStyle.base}>
 <LoadingState />
 </div>
 )
 }

 if (error) {
 return (
 <ErrorState title="模型配置加载失败" message={error} onRetry={loadData} />
 )
 }

 return (
 <div className="space-y-6">
 <div className="flex items-center justify-between">
 <div>
 <h2 className={heading.section}>{isGovernance ? '模型连接' : 'AI 连接'}</h2>
 <p className={heading.muted}>
 {isGovernance
 ? '管理组织级模型供应商、默认配置、密钥遮罩和联调状态'
 : '管理当前账号可使用的模型连接；组织默认、密钥审计和启停治理在治理后台的模型治理中统一处理'}
 </p>
 </div>
 <button
 data-testid="llm-config-add"
 onClick={() => {
 setEditingConfig(null)
 setShowDialog(true)
 }}
 className={buttonStyle.primary}
 >
 <icons.Plus className={`${iconSize.sm} inline-block mr-1.5 -mt-0.5`} />
 添加模型
 </button>
 </div>

 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {configs.map(config => (
 <div key={config.id} data-testid={`llm-config-${config.id}`} className={`${cardStyle.interactive} ${config.is_active ?'' :'opacity-60'}`}>
 <div className="flex items-start justify-between mb-2">
 <div className="flex items-center gap-2 flex-wrap">
 <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded-md ${config.is_active ? statusBadge.info : statusBadge.neutral}`}>
 {providers[config.provider]?.name || config.provider}
 </span>
 {config.is_default && (
 <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded-md ${statusBadge.success}`}>默认</span>
 )}
 </div>
 <div className="flex gap-1">
 <button className={buttonStyle.icon} onClick={() => handleToggleActive(config.id)} title={config.is_active ?"禁用" :"启用"}>
 {config.is_active ? <icons.Activity className={`${iconSize.sm} text-success`} /> : <icons.Activity className={`${iconSize.sm} text-muted-foreground`} />}
 </button>
 <button data-testid={`llm-config-edit-${config.id}`} className={buttonStyle.icon} onClick={() => {
 setEditingConfig(config)
 setShowDialog(true)
 }}>
 <icons.Edit className={iconSize.sm} />
 </button>
 <button className={`${buttonStyle.icon} text-destructive`} onClick={() => handleDelete(config.id)}>
 <icons.Trash2 className={iconSize.sm} />
 </button>
 </div>
 </div>
 <h3 className={heading.card}>{config.name}</h3>
 <p className={`${heading.micro} mt-0.5`}>{config.model_name}</p>
 <div className="mt-3 pt-3 border-t border-border text-sm space-y-1.5">
 <div className="flex justify-between">
 <span className={heading.micro}>类型:</span>
 <span className="text-xs capitalize text-foreground">{config.config_type}</span>
 </div>
 <div className="flex justify-between">
 <span className={heading.micro}>API Base:</span>
 <span className="text-xs text-foreground truncate max-w-[180px]" title={config.api_base_url}>{config.api_base_url ||'默认'}</span>
 </div>
 <div className="flex justify-between gap-3">
 <span className={heading.micro}>API Key:</span>
 <span className="text-xs text-foreground truncate max-w-[180px]" data-testid={`llm-config-key-${config.id}`}>
 {getLlmCredentialSummary(config)}
 </span>
 </div>
 {config.total_calls !== undefined && (
 <div className="flex justify-between">
 <span className={heading.micro}>调用次数:</span>
 <span className="text-xs text-foreground">{config.total_calls}</span>
 </div>
 )}
 </div>
 {!config.is_default && config.is_active && (
 <button className={`${buttonStyle.ghost} w-full mt-3 text-xs`} onClick={() => handleSetDefault(config.id)}>
 设为默认
 </button>
 )}
 </div>
 ))}
 </div>

 {configs.length === 0 && (
 <div className={`${cardStyle.base} text-center py-16`}>
 <icons.Cpu className="w-12 h-12 text-muted-foreground/40 mx-auto mb-3" />
 <p className={heading.muted}>暂无模型配置，请点击右上角添加</p>
 </div>
 )}

 {showDialog && (
 <LlmConfigDialog
 editingConfig={editingConfig}
 providers={providers}
 onClose={() => setShowDialog(false)}
 onSave={() => {
 setShowDialog(false)
 loadData()
 }}
 />
 )}
 </div>
 )
}

function LlmConfigDialog({
 editingConfig,
 providers,
 onClose,
 onSave
}: {
 editingConfig: LLMConfig | null
 providers: Record<string, LLMProvider>
 onClose: () => void
 onSave: () => void
}) {
 const [form, setForm] = useState({
 name: editingConfig?.name ||'',
 provider: editingConfig?.provider ||'openai',
 model_name: editingConfig?.model_name ||'',
 api_key:'',
 api_base_url: editingConfig?.api_base_url ||'',
 config_type: editingConfig?.config_type ||'llm',
 max_tokens: editingConfig?.max_tokens || 4096,
 temperature: editingConfig?.temperature || 0.7,
 is_default: editingConfig?.is_default || false
 })

 const [testing, setTesting] = useState(false)
 const [saving, setSaving] = useState(false)

 const handleProviderChange = (provider: string) => {
 const providerConfig = providers[provider]
 setForm(prev => ({
 ...prev,
 provider,
 api_base_url: providerConfig?.base_url ||'',
 model_name: providerConfig?.models?.llm?.[0] ||''
 }))
 }

 const handleTestConnection = async () => {
 setTesting(true)
 try {
 if (editingConfig && !form.api_key) {
 const res = await llmApi.testConfigConnection(editingConfig.id)
 if (res.success) {
 toast.success(`连接成功! 延迟: ${res.response_time_ms?.toFixed(0)}ms`)
 } else {
 toast.error(`连接失败: ${res.error}`)
 }
 } else {
 const res = await llmApi.testConnection({
 provider: form.provider,
 api_key: form.api_key,
 api_base_url: form.api_base_url,
 model_name: form.model_name
 })
 if (res.success) {
 toast.success(`连接成功! 延迟: ${res.response_time_ms?.toFixed(0)}ms`)
 } else {
 toast.error(`连接失败: ${res.error}`)
 }
 }
 } catch (e: any) {
 toast.error('测试出错:' + (e.message ||'无法连接到后端服务'))
 } finally {
 setTesting(false)
 }
 }

 const handleSave = async () => {
 if (!form.name || !form.provider || !form.model_name) {
 return toast.error('请填写必要信息')
 }

 setSaving(true)
 try {
 const data = buildLlmConfigSavePayload(form, { editing: Boolean(editingConfig) })

 if (editingConfig) {
 await llmApi.updateConfig(editingConfig.id, data)
 } else {
 await llmApi.createConfig(data)
 }
 toast.success('保存成功')
 onSave()
 } catch (e: any) {
 toast.error('保存失败:' + (e.message ||'无法连接到后端服务'))
 } finally {
 setSaving(false)
 }
 }

 const currentProvider = providers[form.provider]

 return (
 <Dialog open={true} onOpenChange={onClose}>
 <DialogContent data-testid="llm-config-dialog" className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
 <DialogHeader>
 <DialogTitle>{editingConfig ?'编辑模型配置' :'添加模型配置'}</DialogTitle>
 <DialogDescription>
 配置大语言模型的连接参数，支持 OpenAI 兼容接口
 </DialogDescription>
 </DialogHeader>

 <ScrollArea className="flex-1 pr-4 -mr-4">
 <div className="grid gap-4 py-4">
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>配置名称</Label>
 <Input
 value={form.name}
 onChange={e => setForm({...form, name: e.target.value})}
 placeholder="给这个配置起个名字"
 />
 </div>
 <div className="space-y-2">
 <Label>提供商</Label>
 <Select value={form.provider} onValueChange={handleProviderChange}>
 <SelectTrigger>
 <SelectValue placeholder="选择提供商" />
 </SelectTrigger>
 <SelectContent>
 {Object.entries(providers).map(([key, p]) => (
 <SelectItem key={key} value={key}>
 {p.name}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 </div>

 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>模型名称</Label>
 <div className="relative">
 <Input
 value={form.model_name}
 onChange={e => setForm({...form, model_name: e.target.value})}
 placeholder="输入或选择模型"
 list="model-options"
 />
 <datalist id="model-options">
 {currentProvider?.models?.llm?.map(m => (
 <option key={m} value={m} />
 ))}
 </datalist>
 </div>
 <p className="text-xs text-muted-foreground">
 {currentProvider?.models?.llm ? `推荐: ${currentProvider.models.llm.slice(0, 3).join(',')}...` :'请输入模型ID'}
 </p>
 </div>
 <div className="space-y-2">
 <Label>配置类型</Label>
 <Select value={form.config_type} onValueChange={v => setForm({...form, config_type: v})}>
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="llm">对话模型 (LLM)</SelectItem>
 <SelectItem value="embedding">向量模型 (Embedding)</SelectItem>
 <SelectItem value="reranker">重排序模型 (Reranker)</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </div>

 <div className="space-y-2">
 <Label>API Base URL</Label>
 <Input
 value={form.api_base_url}
 onChange={e => setForm({...form, api_base_url: e.target.value})}
 placeholder="https://api.openai.com/v1"
 />
 {currentProvider?.note && (
 <p className="text-xs text-warning">{currentProvider.note}</p>
 )}
 </div>

 <div className="space-y-2">
 <Label>API Key {editingConfig &&'(留空保持不变)'}</Label>
 {editingConfig && (
 <p className="text-xs text-muted-foreground" data-testid="llm-config-saved-key">
 {getLlmCredentialSummary(editingConfig)}
 </p>
 )}
 <Input
 data-testid="llm-config-api-key"
 type="password"
 value={form.api_key}
 onChange={e => setForm({...form, api_key: e.target.value})}
 placeholder="sk-..."
 />
 </div>

 <Separator />

 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <Label>最大Token数</Label>
 <Input
 type="number"
 value={form.max_tokens}
 onChange={e => setForm({...form, max_tokens: parseInt(e.target.value)})}
 />
 </div>
 <div className="space-y-2">
 <Label>温度 (Temperature)</Label>
 <Input
 type="number"
 step="0.1"
 min="0"
 max="2"
 value={form.temperature}
 onChange={e => setForm({...form, temperature: parseFloat(e.target.value)})}
 />
 </div>
 </div>

 <div className="flex items-center space-x-2">
 <Switch
 id="is-default"
 checked={form.is_default}
 onCheckedChange={c => setForm({...form, is_default: c})}
 />
 <Label htmlFor="is-default">设为默认模型</Label>
 </div>
 </div>
 </ScrollArea>

 <DialogFooter className="pt-4">
 <Button variant="outline" onClick={handleTestConnection} disabled={testing}>
 {testing ? <icons.Loader2 className="h-4 w-4 animate-spin mr-2" /> : <icons.Zap className="h-4 w-4 mr-2" />}
 测试连接
 </Button>
 <div className="flex gap-2">
 <Button variant="ghost" onClick={onClose}>取消</Button>
 <Button onClick={handleSave} disabled={saving}>
 {saving ?'保存中...' :'保存配置'}
 </Button>
 </div>
 </DialogFooter>
 </DialogContent>
 </Dialog>
 )
}

// ============ MCP设置面板组件 ============

const MCP_TEMPLATES = [
 {
 name:'brave-search',
 description:'Brave Search web search capability',
 type:'stdio',
 command:'npx',
 args: ['-y','@modelcontextprotocol/server-brave-search'],
 env: { BRAVE_API_KEY:'' }
 },
 {
 name:'google-maps',
 description:'Google Maps location services',
 type:'stdio',
 command:'npx',
 args: ['-y','@modelcontextprotocol/server-google-maps'],
 env: { GOOGLE_MAPS_API_KEY:'' }
 },
 {
 name:'amap-maps',
 description:'高德地图 (Amap) - 路线规划与POI搜索',
 type:'stdio',
 command:'npx',
 args: ['-y','@amap/amap-maps-mcp-server'],
 env: { AMAP_MAPS_API_KEY:'' }
 },
 {
 name:'github',
 description:'GitHub repository management',
 type:'stdio',
 command:'npx',
 args: ['-y','@modelcontextprotocol/server-github'],
 env: { GITHUB_PERSONAL_ACCESS_TOKEN:'' }
 },
 {
 name:'postgres',
 description:'PostgreSQL database access',
 type:'stdio',
 command:'npx',
 args: ['-y','@modelcontextprotocol/server-postgres','postgresql://user:password@localhost/db']
 }
]

export function McpSettingsPanel({ scope = 'governance' }: { scope?: ConnectionPanelScope } = {}) {
 const [servers, setServers] = useState<McpServerConfig[]>([])
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)
 const [showAddDialog, setShowAddDialog] = useState(false)
 const [editingServer, setEditingServer] = useState<McpServerConfig | null>(null)
 const [connecting, setConnecting] = useState<string | null>(null)
 const isGovernance = scope === 'governance'

 useEffect(() => {
 loadData()
 }, [])

 const loadData = async () => {
 setLoading(true)
 setError(null)
 try {
 const data = await mcpApi.listServers()
 setServers(Array.isArray(data) ? data : [])
 } catch (e: any) {
 setServers([])
 setError(e.message ||'无法加载服务集成配置')
 } finally {
 setLoading(false)
 }
 }

 const handleConnect = async (id: string) => {
 setConnecting(id)
 try {
 const result = await mcpApi.connect(id)
 toast.success(`连接成功! 发现 ${result.tools_count} 个工具`)
 loadData()
 } catch (e: any) {
 toast.error('连接失败:' + (e.message ||'无法连接到后端服务'))
 } finally {
 setConnecting(null)
 }
 }

 const handleDelete = async (id: string) => {
 if (!confirm('确定要删除这个服务配置吗？')) return
 try {
 await mcpApi.delete(id)
 toast.success('服务已删除')
 loadData()
 } catch (e: any) {
 toast.error(e.message ||'删除失败')
 }
 }

 if (loading) {
 return (
 <div className={cardStyle.base}>
 <LoadingState />
 </div>
 )
 }

 if (error) {
 return (
 <ErrorState title="服务集成加载失败" message={error} onRetry={loadData} />
 )
 }

 return (
 <div className="space-y-6">
 <div className={cardStyle.base}>
 <div className="flex items-center justify-between">
 <div>
 <h2 className={heading.section}>{isGovernance ? 'MCP / 工具连接' : '工具连接 (MCP)'}</h2>
 <p className={`${heading.muted} mt-0.5`}>
 {isGovernance
 ? '管理组织级 MCP 工具服务、allowlist、连接刷新和凭据遮罩'
 : '管理当前工作流可调用的 MCP 工具连接；跨组织启用、凭据审计和系统级接入统一在治理后台处理'}
 </p>
 </div>
 <button
 onClick={() => {
 setEditingServer(null)
 setShowAddDialog(true)
 }}
 className={buttonStyle.primary}
 >
 <icons.Plus className={`${iconSize.sm} inline-block mr-1.5 -mt-0.5`} />
 添加服务
 </button>
 </div>
 </div>

 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {servers.map(server => (
 <div key={server.id} className={cardStyle.interactive}>
 <div className="flex items-start justify-between mb-3">
 <div className="flex items-center gap-3">
 <div className="p-2 rounded-lg bg-primary/10 text-primary">
 <icons.Briefcase className={iconSize.lg} />
 </div>
 <div>
 <h3 className={heading.card}>{server.name}</h3>
 <div className="flex items-center gap-2 mt-1">
 <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded-md ${statusBadge.neutral} uppercase`}>
 {server.type}
 </span>
 {server.is_enabled ? (
 <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded-md ${statusBadge.success}`}>已启用</span>
 ) : (
 <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded-md ${statusBadge.error}`}>已禁用</span>
 )}
 </div>
 </div>
 </div>
 <div className="flex gap-1">
 <button
 onClick={() => handleConnect(server.id)}
 disabled={!!connecting}
 className={buttonStyle.icon}
 title="重新连接/刷新工具"
 >
 {connecting === server.id ? <icons.Loader2 className={`${iconSize.sm} animate-spin`} /> : <icons.Zap className={iconSize.sm} />}
 </button>
 <button
 onClick={() => {
 setEditingServer(server)
 setShowAddDialog(true)
 }}
 className={buttonStyle.icon}
 title="编辑"
 >
 <icons.Settings className={iconSize.sm} />
 </button>
 <button
 onClick={() => handleDelete(server.id)}
 className={`${buttonStyle.icon} text-destructive`}
 title="删除"
 >
 <icons.Trash2 className={iconSize.sm} />
 </button>
 </div>
 </div>

 {server.description && (
 <p className={`${heading.muted} mb-3`}>{server.description}</p>
 )}

 <div className="text-xs bg-muted/50 p-2 rounded-lg border border-border font-mono truncate mb-3">
 {server.type ==='stdio' ? server.command : server.url}
 </div>

 <div className="border-t border-border pt-2">
 <p className={`${heading.micro} mb-1`}>可用工具:</p>
 <div className="flex flex-wrap gap-1">
 {server.cached_tools && server.cached_tools.length > 0 ? (
 server.cached_tools.map((t: any) => (
 <span key={t.name} className={`inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded-md ${statusBadge.info}`}>
 {t.name}
 </span>
 ))
 ) : (
 <span className={`${heading.micro} italic`}>暂无缓存工具 (请点击闪电图标连接)</span>
 )}
 </div>
 </div>
 </div>
 ))}
 </div>

 {servers.length === 0 && (
 <div className={`${cardStyle.base} text-center py-16`}>
 <icons.Server className="w-12 h-12 text-muted-foreground/40 mx-auto mb-3" />
 <p className={heading.muted}>暂无集成的第三方服务</p>
 </div>
 )}

 {showAddDialog && (
 <McpConfigDialog
 editingServer={editingServer}
 onClose={() => setShowAddDialog(false)}
 onSave={() => {
 setShowAddDialog(false)
 loadData()
 }}
 />
 )}
 </div>
 )
}

function McpConfigDialog({ editingServer, onClose, onSave }: { editingServer: McpServerConfig | null, onClose: () => void, onSave: () => void }) {
 const persistedEnvKeys = getPersistedEnvKeys(editingServer)
 const [form, setForm] = useState<McpServerCreate>({
 name: editingServer?.name ||'',
 description: editingServer?.description ||'',
 type: editingServer?.type ||'stdio',
 command: editingServer?.command ||'',
 args: editingServer?.args || [],
 env: editingServer ? {} : {},
 url: editingServer?.url ||'',
 is_enabled: editingServer?.is_enabled ?? true
 })

 const [argInput, setArgInput] = useState('')
 const [envKey, setEnvKey] = useState('')
 const [envVal, setEnvVal] = useState('')
 const [replaceEnv, setReplaceEnv] = useState(false)
 const [saving, setSaving] = useState(false)

 const applyTemplate = (templateName: string) => {
 const template = MCP_TEMPLATES.find(t => t.name === templateName)
 if (template) {
 setForm({
 ...form,
 name: template.name,
 description: template.description,
 type: template.type,
 command: template.command ||'',
 args: [...(template.args || [])],
 env: { ...(template.env || {}) } as Record<string, string>,
 url:''
 })
 setReplaceEnv(false)
 }
 }

 const handleSave = async () => {
 if (!form.name) return toast.error('请输入服务名称')
 if (form.type ==='stdio' && !form.command) return toast.error('请输入执行命令')
 if (form.type ==='sse' && !form.url) return toast.error('请输入SSE URL')

 setSaving(true)
 try {
 const payload = buildMcpSavePayload(form, { editing: Boolean(editingServer), replaceEnv })
 if (editingServer) {
 await mcpApi.update(editingServer.id, payload)
 } else {
 await mcpApi.create(payload as McpServerCreate)
 }
 toast.success('保存成功')
 onSave()
 } catch (e: any) {
 toast.error(e.message ||'保存失败，无法连接到后端服务')
 } finally {
 setSaving(false)
 }
 }

 return (
 <div className="fixed inset-0 bg-foreground/40 flex items-center justify-center z-50">
 <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col mx-4">
 <div className="flex items-center justify-between px-6 py-4 border-b border-border">
 <h2 className={heading.section}>{editingServer ?'编辑服务' :'添加服务'}</h2>
 <button onClick={onClose} className={buttonStyle.icon}><icons.X className={iconSize.md} /></button>
 </div>

 <div className="p-6 overflow-y-auto space-y-4 flex-1">
 {!editingServer && (
 <div>
 <label className={`block ${heading.card} mb-2`}>快速模板</label>
 <div className="flex flex-wrap gap-2">
 {MCP_TEMPLATES.map(t => (
 <button
 key={t.name}
 onClick={() => applyTemplate(t.name)}
 className="px-3 py-1.5 text-xs bg-muted hover:bg-primary/10 hover:text-primary rounded-full border transition-colors"
 >
 + {t.name}
 </button>
 ))}
 </div>
 </div>
 )}

 <div className="grid grid-cols-2 gap-4">
 <div>
 <label className={`block ${heading.card} mb-1`}>名称</label>
 <input
 className={inputStyle.search}
 value={form.name}
 onChange={e => setForm({...form, name: e.target.value})}
 placeholder="例如: brave-search"
 />
 </div>
 <div>
 <label className={`block ${heading.card} mb-1`}>类型</label>
 <select
 className={inputStyle.search}
 value={form.type}
 onChange={e => setForm({...form, type: e.target.value})}
 >
 <option value="stdio">Local Process (stdio)</option>
 <option value="sse">Remote Server (SSE)</option>
 </select>
 </div>
 </div>

 <div>
 <label className={`block ${heading.card} mb-1`}>描述</label>
 <input
 className={inputStyle.search}
 value={form.description}
 onChange={e => setForm({...form, description: e.target.value})}
 placeholder="简要描述该服务的功能"
 />
 </div>

 {form.type ==='stdio' ? (
 <>
 <div>
 <label className={`block ${heading.card} mb-1`}>命令 (Command)</label>
 <input
 className={`${inputStyle.search} font-mono`}
 value={form.command}
 onChange={e => setForm({...form, command: e.target.value})}
 placeholder="e.g. npx, python, uv"
 />
 </div>

 <div>
 <label className={`block ${heading.card} mb-1`}>参数 (Args)</label>
 <div className="flex gap-2 mb-2">
 <input
 className={`flex-1 ${inputStyle.search} font-mono`}
 value={argInput}
 onChange={e => setArgInput(e.target.value)}
 placeholder="-y @modelcontextprotocol/server-brave-search"
 onKeyDown={e => {
 if (e.key ==='Enter') {
 e.preventDefault()
 if (argInput) {
 setForm({...form, args: [...(form.args || []), argInput]})
 setArgInput('')
 }
 }
 }}
 />
 <button
 className={buttonStyle.secondary}
 onClick={() => {
 if (argInput) {
 setForm({...form, args: [...(form.args || []), argInput]})
 setArgInput('')
 }
 }}
 >
 添加
 </button>
 </div>
 <div className="flex flex-wrap gap-2">
 {form.args?.map((arg, i) => (
 <span key={i} className="px-2 py-1 bg-muted rounded text-sm flex items-center gap-1 font-mono">
 {arg}
 <button onClick={() => setForm({...form, args: form.args?.filter((_, idx) => idx !== i)})}><icons.X className="h-3 w-3" /></button>
 </span>
 ))}
 </div>
 </div>

 <div>
 <div className="mb-2 flex items-center justify-between gap-3">
 <label className={`block ${heading.card}`}>环境变量 (Environment Variables)</label>
 {editingServer && (
 <button
 type="button"
 className={buttonStyle.secondary}
 onClick={() => {
 setReplaceEnv(true)
 setForm({...form, env: {}})
 }}
 >
 替换环境变量
 </button>
 )}
 </div>
 {editingServer && persistedEnvKeys.length > 0 && !replaceEnv && (
 <div className="mb-3 rounded-lg border border-border bg-muted/50 p-3">
 <p className="mb-2 text-xs text-muted-foreground">已保存的凭据只显示键名，编辑其他字段不会清空密钥。</p>
 <div className="flex flex-wrap gap-2">
 {persistedEnvKeys.map((key) => (
 <span key={key} className="rounded bg-background px-2 py-1 text-xs font-medium text-foreground">
 {key}=已保存
 </span>
 ))}
 </div>
 </div>
 )}
 {(!editingServer || replaceEnv) && (
 <>
 {editingServer && (
 <p className="mb-2 text-xs leading-5 text-warning">
 保存后将用下方列表替换当前环境变量；留空会清空该服务的 env 配置。
 </p>
 )}
 <div className="flex gap-2 mb-2">
 <input
 className={`flex-1 ${inputStyle.search} font-mono`}
 placeholder="KEY"
 value={envKey}
 onChange={e => setEnvKey(e.target.value)}
 />
 <input
 type="password"
 autoComplete="off"
 className={`flex-1 ${inputStyle.search} font-mono`}
 placeholder="VALUE"
 value={envVal}
 onChange={e => setEnvVal(e.target.value)}
 />
 <button
 className={buttonStyle.secondary}
 onClick={() => {
 if (envKey && envVal) {
 setForm({...form, env: {...form.env, [envKey]: envVal}})
 setEnvKey('')
 setEnvVal('')
 }
 }}
 >
 添加
 </button>
 </div>
 <div className="space-y-1">
 {Object.entries(form.env || {}).map(([k, v]) => (
 <div key={k} className="flex justify-between px-3 py-1 bg-muted rounded text-sm font-mono">
 <span>{k}={maskMcpEnvValue(v)}</span>
 <button onClick={() => {
 const newEnv = {...form.env}
 delete newEnv[k]
 setForm({...form, env: newEnv})
 }}><icons.X className="h-3 w-3" /></button>
 </div>
 ))}
 </div>
 </>
 )}
 </div>
 </>
 ) : (
 <div>
 <label className={`block ${heading.card} mb-1`}>SSE URL</label>
 <input
 className={`${inputStyle.search} font-mono`}
 value={form.url}
 onChange={e => setForm({...form, url: e.target.value})}
 placeholder="http://localhost:3001/sse"
 />
 </div>
 )}

 <div className="flex items-center gap-2">
 <input
 type="checkbox"
 checked={form.is_enabled}
 onChange={e => setForm({...form, is_enabled: e.target.checked})}
 className="rounded border-border"
 />
 <label className="text-sm">启用此服务</label>
 </div>
 </div>

 <div className="flex justify-end gap-2 px-6 py-4 border-t border-border bg-muted/30">
 <button onClick={onClose} className={buttonStyle.secondary}>取消</button>
 <button
 onClick={handleSave}
 disabled={saving}
 className={`${buttonStyle.primary} disabled:opacity-50`}
 >
 {saving ?'保存中...' :'保存配置'}
 </button>
 </div>
 </div>
 </div>
 )
}

// ============ 通知偏好面板 ============

const EVENT_TYPES = [
 { key:'approval', label:'审批通知' },
 { key:'chat', label:'对话消息' },
 { key:'case', label:'案件更新' },
 { key:'system', label:'系统公告' },
 { key:'contract', label:'合同提醒' },
 { key:'lawyer', label:'找律师匹配' },
] as const

const CHANNELS = [
 { key:'site', label:'站内信', icon: icons.Bell },
 { key:'email', label:'邮件', icon: icons.Mail },
 { key:'wechat', label:'微信', icon: icons.MessageSquare },
 { key:'sms', label:'短信', icon: icons.Phone },
] as const

function NotificationPreferencesPanel() {
 const [preferences, setPreferences] = useState<Record<string, Record<string, boolean>>>({})
 const [loading, setLoading] = useState(true)
 const [updating, setUpdating] = useState<string | null>(null)

 useEffect(() => {
 loadPreferences()
 }, [])

 const loadPreferences = async () => {
 setLoading(true)
 try {
 const data = await notificationsApi.getPreferences()
 const map: Record<string, Record<string, boolean>> = {}
 // Initialize all to true by default
 for (const evt of EVENT_TYPES) {
 map[evt.key] = {}
 for (const ch of CHANNELS) {
 map[evt.key][ch.key] = true
 }
 }
 // Override with API data
 for (const pref of data) {
 if (!map[pref.event_type]) map[pref.event_type] = {}
 map[pref.event_type][pref.channel] = pref.enabled
 }
 setPreferences(map)
 } catch {
 // Fallback: all enabled
 const map: Record<string, Record<string, boolean>> = {}
 for (const evt of EVENT_TYPES) {
 map[evt.key] = {}
 for (const ch of CHANNELS) {
 map[evt.key][ch.key] = true
 }
 }
 setPreferences(map)
 toast.error('加载通知偏好失败，使用默认设置')
 } finally {
 setLoading(false)
 }
 }

 const handleToggle = async (eventType: string, channel: string, enabled: boolean) => {
 const cellKey = `${eventType}-${channel}`
 setUpdating(cellKey)

 // Optimistic update
 setPreferences(prev => ({
 ...prev,
 [eventType]: { ...prev[eventType], [channel]: enabled },
 }))

 try {
 // Build full preference list from current state
 const list: NotificationPreference[] = []
 for (const evt of EVENT_TYPES) {
 for (const ch of CHANNELS) {
 const isEnabled =
 evt.key === eventType && ch.key === channel
 ? enabled
 : preferences[evt.key]?.[ch.key] ?? true
 list.push({ event_type: evt.key, channel: ch.key, enabled: isEnabled })
 }
 }
 await notificationsApi.updatePreferences(list)
 } catch {
 // Revert on failure
 setPreferences(prev => ({
 ...prev,
 [eventType]: { ...prev[eventType], [channel]: !enabled },
 }))
 toast.error('更新通知偏好失败')
 } finally {
 setUpdating(null)
 }
 }

 if (loading) {
 return (
 <Card className="border-border rounded-xl">
 <CardContent>
 <LoadingState text="加载通知偏好..." />
 </CardContent>
 </Card>
 )
 }

 return (
 <div className="space-y-6 max-w-3xl">
 <Card className="border-border rounded-xl">
 <CardHeader>
 <CardTitle className={heading.section}>通知偏好</CardTitle>
 <CardDescription className={heading.muted}>
 选择各类通知的接收渠道，开关即时生效
 </CardDescription>
 </CardHeader>
 <CardContent>
 <div className="overflow-x-auto">
 <table className="w-full text-sm">
 <thead>
 <tr className="border-b border-border">
 <th className="text-left py-3 pr-4 font-medium text-muted-foreground whitespace-nowrap">
 事件类型
 </th>
 {CHANNELS.map(ch => (
 <th key={ch.key} className="text-center py-3 px-4 font-medium text-muted-foreground whitespace-nowrap">
 <div className="flex flex-col items-center gap-1">
 <ch.icon className={iconSize.sm} />
 <span>{ch.label}</span>
 </div>
 </th>
 ))}
 </tr>
 </thead>
 <tbody>
 {EVENT_TYPES.map(evt => (
 <tr key={evt.key} className="border-b border-border/50 last:border-b-0">
 <td className="py-3 pr-4 font-medium text-foreground whitespace-nowrap">
 {evt.label}
 </td>
 {CHANNELS.map(ch => {
 const cellKey = `${evt.key}-${ch.key}`
 const isEnabled = preferences[evt.key]?.[ch.key] ?? true
 return (
 <td key={ch.key} className="text-center py-3 px-4">
 <div className="flex justify-center">
 <Switch
 checked={isEnabled}
 onCheckedChange={(checked) => handleToggle(evt.key, ch.key, checked)}
 disabled={updating === cellKey}
 />
 </div>
 </td>
 )
 })}
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </CardContent>
 </Card>
 </div>
 )
}
