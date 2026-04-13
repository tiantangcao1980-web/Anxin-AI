import { icons } from '@/lib/icons'
import { heading, buttonStyle, iconSize } from '@/lib/design-tokens'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi, User as ApiUser } from '../lib/api'
import { getTokenStorage } from '../lib/platform/storage'
import { useAuthStore, useUIStore } from '../lib/store'
import { clearAuth as clearDesktopAuth } from '../lib/tauri-bridge'
import { usePrivacy, PrivacyMode, HardwareStatus as HWStatus } from '../context/PrivacyContext'
import { toast } from 'sonner'

const OPENCLAW_SETUP_GUIDE = [
  '1. 确认本机满足最低硬件要求（建议 8GB 内存、20GB 可用磁盘）。',
  '2. 拉取 OpenClaw 运行时与法律模型包。',
  '3. 配置本地推理服务地址、模型目录和隐私策略。',
  '4. 完成本地联调后，再回到平台点击“我已完成部署”。',
].join('\n')

// ==================== 角色和认证辅助函数 ====================

const ROLE_DISPLAY_MAP: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '系统管理员',
  org_admin: '机构管理员',
  dept_admin: '部门管理员',
  partner: '合伙人',
  lawyer: '执业律师',
  paralegal: '律师助理',
  platform_lawyer: '平台律师',
  enterprise_user: '企业用户',
  individual_user: '个人用户',
  member: '普通用户',
  client: '委托人',
  viewer: '访客',
}

const USER_TYPE_DISPLAY_MAP: Record<string, string> = {
  individual: '个人版',
  enterprise: '企业版',
  lawyer: '律师版',
  law_firm: '律所版',
  internal: '',
  admin: '管理平台',
  super_admin: '管理平台',
}

function getRoleDisplayName(role: string): string {
  return ROLE_DISPLAY_MAP[role] || role
}

function getUserTypeDisplayName(userType: string): string {
  return USER_TYPE_DISPLAY_MAP[userType] || userType
}

/** 角色图标映射 — 使用设计系统中的 lucide-react SVG 图标 */
function RoleIcon({ role, className = 'w-3.5 h-3.5' }: { role: string; className?: string }) {
  const iconMap: Record<string, typeof icons[keyof typeof icons]> = {
    super_admin: icons.Shield,
    admin: icons.Settings,
    org_admin: icons.Building,
    dept_admin: icons.ClipboardCheck,
    partner: icons.Star,
    lawyer: icons.Scale,
    paralegal: icons.Edit,
    platform_lawyer: icons.Scale,
    enterprise_user: icons.Building2,
    individual_user: icons.User,
    member: icons.User,
    client: icons.Users,
    viewer: icons.Eye,
  }
  const IconComponent = iconMap[role] || icons.User
  return <IconComponent className={className} />
}

// 兼容旧的字符串签名（返回空字符串，实际使用 RoleIcon 组件）
function getRoleIcon(_role: string): string {
  return ''
}

/** 需要认证的角色 */
const ROLES_NEED_VERIFICATION = ['lawyer', 'platform_lawyer', 'enterprise_user', 'org_admin']

/** 生成认证状态横幅 */
function getVerificationBanner(
  user: { role?: string; user_type?: string; email_verified?: boolean },
  navigate: (path: string) => void,
) {
  const role = user.role || 'member'
  const userType = user.user_type || 'individual'

  // 管理员角色不显示认证/升级提示
  if (['super_admin', 'admin', 'org_admin', 'dept_admin'].includes(role)) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-success/10 text-success text-xs">
        <icons.Shield className="w-3.5 h-3.5 shrink-0" />
        <span>{getRoleDisplayName(role)} · 全部功能已开通</span>
      </div>
    )
  }

  // 邮箱未验证
  if (user.email_verified === false) {
    return (
      <button
        onClick={() => navigate('/settings?tab=profile')}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-warning/10 text-warning text-xs hover:bg-warning/20 transition-colors"
      >
        <icons.AlertTriangle className="w-3.5 h-3.5 shrink-0" />
        <span className="text-left">邮箱未验证，部分功能受限。点击前往验证</span>
        <icons.ChevronRight className="w-3.5 h-3.5 ml-auto shrink-0" />
      </button>
    )
  }

  // 律师/律所 — 检查是否已认证
  if (userType === 'lawyer' || userType === 'law_firm' || role === 'lawyer' || role === 'platform_lawyer') {
    // 如果角色仍是 viewer/member，说明未通过认证
    if (role === 'viewer' || role === 'member' || role === 'individual_user') {
      return (
        <button
          onClick={() => navigate('/lawyer-onboarding')}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-warning/10 text-warning text-xs hover:bg-warning/20 transition-colors"
        >
          <icons.FileSignature className="w-3.5 h-3.5 shrink-0" />
          <span className="text-left">律师资质待认证，完成认证后解锁全部功能</span>
          <icons.ChevronRight className="w-3.5 h-3.5 ml-auto shrink-0" />
        </button>
      )
    }
    // 已认证
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-success/10 text-success text-xs">
        <icons.CheckCircle className="w-3.5 h-3.5 shrink-0" />
        <span>已认证律师 · 全部功能已开通</span>
      </div>
    )
  }

  // 企业用户 — 检查是否已认证
  if (userType === 'enterprise') {
    if (role === 'viewer' || role === 'member' || role === 'individual_user') {
      return (
        <button
          onClick={() => navigate('/settings?tab=profile')}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-info/10 text-info text-xs hover:bg-info/20 transition-colors"
        >
          <icons.Building className="w-3.5 h-3.5 shrink-0" />
          <span className="text-left">企业认证待完成，认证后开通团队协作功能</span>
          <icons.ChevronRight className="w-3.5 h-3.5 ml-auto shrink-0" />
        </button>
      )
    }
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-success/10 text-success text-xs">
        <icons.CheckCircle className="w-3.5 h-3.5 shrink-0" />
        <span>企业已认证 · 团队功能已开通</span>
      </div>
    )
  }

  // 个人用户 — 提示升级
  if (userType === 'individual' || role === 'individual_user' || role === 'member') {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/10 text-white/80 text-xs">
        <icons.Lightbulb className="w-3.5 h-3.5 shrink-0" />
        <span>个人用户 · </span>
        <button
          onClick={() => navigate('/subscription')}
          className="underline hover:text-white transition-colors"
        >
          升级套餐解锁更多功能
        </button>
      </div>
    )
  }

  return null
}

// ==================== Component ====================

interface UserProfileProps {
  onClose: () => void
  headerActionLabels?: boolean
  onToggleHeaderActionLabels?: () => void
}

export function UserProfile({ onClose, headerActionLabels = true, onToggleHeaderActionLabels }: UserProfileProps) {
  const navigate = useNavigate()
  const { theme, setTheme } = useUIStore()
  const { user: storeUser, logout: storeLogout } = useAuthStore()
  const {
    mode: privacyMode,
    setMode: setPrivacyMode,
    hardwareStatus,
    hardwareName,
    secureComputeUsage,
    openClawInstalled,
    toggleHardwareConnection,
    setOpenClawInstalled,
  } = usePrivacy()
  const [showHardwareSetup, setShowHardwareSetup] = useState(false)
  const [notifications, setNotifications] = useState(() => {
    return localStorage.getItem('notifications_enabled') !== 'false'
  })
  const [user, setUser] = useState<ApiUser | null>(storeUser)

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      const currentUser = await authApi.getCurrentUser()
      setUser(currentUser)
    } catch {
      if (storeUser) {
        setUser(storeUser)
      } else {
        const stored = localStorage.getItem('user_info')
        if (stored) {
          try { setUser(JSON.parse(stored)) } catch { /* ignore */ }
        }
      }
    }
  }

  const isDark = theme === 'dark' || (theme === 'system' && typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  const isAdmin = user?.role === 'admin'

  const toggleDarkMode = () => {
    const newTheme = isDark ? 'light' : 'dark'
    setTheme(newTheme)
    toast.success(newTheme === 'dark' ? '已切换到深色模式' : '已切换到浅色模式')
  }

  const toggleNotifications = () => {
    const next = !notifications
    setNotifications(next)
    localStorage.setItem('notifications_enabled', String(next))
    toast.success(next ? '已开启推送通知' : '已关闭推送通知')
  }

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch { /* logout may fail silently */ }
    await getTokenStorage().clearAuth()
    await clearDesktopAuth()
    storeLogout()
    localStorage.removeItem('user_info')
    toast.success('已退出登录')
    onClose()
    window.location.reload()
  }

  const handleNavigate = (path: string) => {
    onClose()
    navigate(path)
  }

  const menuItems = [
    { icon: icons.User, label: '个人信息', action: () => handleNavigate('/settings?tab=profile') },
    { icon: icons.HelpCircle, label: '帮助中心', action: () => handleNavigate('/knowledge-base') },
  ]

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="absolute right-0 top-0 bottom-0 w-80 bg-background shadow-2xl flex flex-col animate-in slide-in-from-right duration-200"
      >
        {/* Header — 用户信息+角色+认证状态 */}
        <div className="p-6 bg-primary text-primary-foreground">
          <div className="flex items-start justify-between mb-4">
            <div className="w-16 h-16 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center overflow-hidden">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt={user.name} className="w-full h-full object-cover" />
              ) : (
                <icons.User className={iconSize.xl} />
              )}
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-white/20 rounded-full transition-colors"
            >
              <icons.X className={iconSize.md} />
            </button>
          </div>
          <h3 className={`${heading.section} text-primary-foreground text-lg mb-1`}>{user?.name || '未登录'}</h3>
          <p className={`${heading.muted} text-primary-foreground/80 text-sm`}>{user?.email || '请登录后查看'}</p>

          {/* 角色和用户类型标签 */}
          <div className="flex flex-wrap gap-1.5 mt-3">
            {user?.role && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-white/20">
                <RoleIcon role={user.role} className="w-3 h-3" />
                {getRoleDisplayName(user.role)}
              </span>
            )}
            {user?.user_type && user.user_type !== 'internal' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-white/15">
                {getUserTypeDisplayName(user.user_type)}
              </span>
            )}
          </div>

          {/* 认证状态提示 */}
          {user && (
            <div className="mt-3">
              {getVerificationBanner(user, handleNavigate)}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* 功能列表：个人信息、帮助中心、后台管理、深色模式、推送通知 */}
          <div className="space-y-1 mb-4">
            {menuItems.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.label}
                  onClick={item.action}
                  className={`w-full flex items-center gap-3 p-3 ${buttonStyle.ghost} text-left`}
                >
                  <Icon className={`${iconSize.md} text-muted-foreground`} />
                  <span className={heading.card}>{item.label}</span>
                  <icons.ChevronRight className={`${iconSize.sm} text-muted-foreground ml-auto`} />
                </button>
              )
            })}

            {isAdmin && (
              <button
                onClick={() => handleNavigate('/admin')}
                className={`w-full flex items-center gap-3 p-3 ${buttonStyle.ghost} text-left`}
              >
                <icons.Shield className={`${iconSize.md} text-primary`} />
                <span className={`${heading.card} text-primary`}>后台管理</span>
                <icons.ChevronRight className={`${iconSize.sm} text-primary/60 ml-auto`} />
              </button>
            )}

            {/* 深色模式 */}
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                {isDark ? (
                  <icons.Moon className={`${iconSize.md} text-muted-foreground`} />
                ) : (
                  <icons.Sun className={`${iconSize.md} text-muted-foreground`} />
                )}
                <span className={heading.card}>深色模式</span>
              </div>
              <button
                onClick={toggleDarkMode}
                className={`w-11 h-6 rounded-full transition-colors ${
                  isDark ? 'bg-primary' : 'bg-border'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-background rounded-full my-0.5 shadow-sm transition-transform ${
                    isDark ? 'translate-x-[22px]' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>

            {/* 推送通知 */}
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <icons.Bell className={`${iconSize.md} text-muted-foreground`} />
                <span className={heading.card}>推送通知</span>
              </div>
              <button
                onClick={toggleNotifications}
                className={`w-11 h-6 rounded-full transition-colors ${
                  notifications ? 'bg-primary' : 'bg-border'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-background rounded-full my-0.5 shadow-sm transition-transform ${
                    notifications ? 'translate-x-[22px]' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>

            {/* 导航栏显示文字 */}
            {onToggleHeaderActionLabels && (
              <div className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-3">
                  {headerActionLabels ? (
                    <icons.List className={`${iconSize.md} text-muted-foreground`} />
                  ) : (
                    <icons.Grid3x3 className={`${iconSize.md} text-muted-foreground`} />
                  )}
                  <span className={heading.card}>导航栏显示文字</span>
                </div>
                <button
                  onClick={onToggleHeaderActionLabels}
                  className={`w-11 h-6 rounded-full transition-colors ${
                    headerActionLabels ? 'bg-primary' : 'bg-border'
                  }`}
                >
                  <div
                    className={`w-5 h-5 bg-background rounded-full my-0.5 shadow-sm transition-transform ${
                      headerActionLabels ? 'translate-x-[22px]' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>
            )}
          </div>

          {/* AI 私有助手 + 数据隐私保护级别 */}
          <div className="space-y-3 pt-3 border-t border-border">
            {/* AI 私有助手 */}
            <div className="p-3 bg-muted/50 rounded-xl space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <icons.Cpu className={`${iconSize.md} ${
                    hardwareStatus === HWStatus.CONNECTED
                      ? 'text-success'
                      : !openClawInstalled
                        ? 'text-warning'
                        : 'text-muted-foreground'
                  }`} />
                  <div>
                    <span className={heading.card}>AI 私有助手</span>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      {!openClawInstalled
                        ? '未安装 · 点击配置'
                        : hardwareStatus === HWStatus.CONNECTED
                          ? `${hardwareName} · 算力 ${Math.round(secureComputeUsage)}%`
                          : '已安装 · 离线'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    if (!openClawInstalled) {
                      setShowHardwareSetup(true)
                    } else {
                      toggleHardwareConnection()
                      toast.success(
                        hardwareStatus === HWStatus.CONNECTED ? '已断开本地硬件' : '正在连接本地硬件…'
                      )
                    }
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    hardwareStatus === HWStatus.CONNECTED
                      ? 'bg-success/10 text-success hover:bg-success/20'
                      : !openClawInstalled
                        ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                >
                  {!openClawInstalled ? '配置' : hardwareStatus === HWStatus.CONNECTED ? '已连接' : '连接'}
                </button>
              </div>
              {hardwareStatus === HWStatus.CONNECTED && (
                <div className="h-1.5 bg-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-success rounded-full transition-all duration-500"
                    style={{ width: `${secureComputeUsage}%` }}
                  />
                </div>
              )}
            </div>

            {/* 数据隐私保护级别 */}
            <div className="p-3 bg-muted/50 rounded-xl space-y-2.5">
              <div className="flex items-center gap-3">
                <icons.ShieldCheck className={`${iconSize.md} text-muted-foreground`} />
                <span className={heading.card}>数据隐私保护级别</span>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {([
                  { mode: PrivacyMode.LOCAL, label: '绝密', icon: icons.Lock, disabled: hardwareStatus !== HWStatus.CONNECTED },
                  { mode: PrivacyMode.HYBRID, label: '混合', icon: icons.ShieldCheck, disabled: false },
                  { mode: PrivacyMode.CLOUD, label: '云端', icon: icons.Cloud, disabled: false },
                ] as const).map(({ mode, label, icon: ModeIcon, disabled }) => {
                  const isActive = privacyMode === mode
                  return (
                    <button
                      key={mode}
                      disabled={disabled}
                      onClick={() => {
                        setPrivacyMode(mode)
                        toast.success(`已切换到${label}模式`)
                      }}
                      className={`flex flex-col items-center gap-1 py-2 rounded-lg text-xs font-medium transition-all ${
                        isActive
                          ? 'bg-primary/10 text-primary ring-1 ring-primary/20'
                          : disabled
                            ? 'text-muted-foreground/40 cursor-not-allowed'
                            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      }`}
                    >
                      <ModeIcon className="w-4 h-4" />
                      <span>{label}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Version info */}
          <div className="mt-6 pt-4 border-t border-border text-center">
            <p className={heading.micro}>安心AI法务 v1.0.0</p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 bg-warning/10 text-warning border border-warning/20 hover:bg-warning/20 active:scale-[0.98] rounded-lg px-4 py-2 text-sm font-medium transition-all"
          >
            <icons.LogOut className={iconSize.md} />
            退出登录
          </button>
        </div>
      </div>

      {/* AI 私有助手安装引导弹窗 */}
      {showHardwareSetup && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={(e) => { if (e.target === e.currentTarget) setShowHardwareSetup(false) }}
        >
          <div className="bg-background rounded-2xl shadow-2xl border border-border w-full max-w-lg mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="bg-gradient-to-r from-primary/10 to-primary/5 px-6 py-5 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-xl">
                    <icons.Cpu className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-foreground">AI 私有助手</h3>
                    <p className="text-sm text-muted-foreground">
                      {privacyMode === PrivacyMode.CLOUD ? '云端私有助手服务' : '基于 OpenClaw 的本地私有化 AI 服务'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowHardwareSetup(false)}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  <icons.X className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="px-6 py-5 space-y-4">
              {privacyMode === PrivacyMode.CLOUD ? (
                <div className="text-center py-6 space-y-4">
                  <div className="mx-auto w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center">
                    <icons.Cloud className="w-8 h-8 text-primary" />
                  </div>
                  <div>
                    <h4 className="text-base font-medium text-foreground mb-1">云端私有助手</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      云端私有助手仍处于规划阶段。开放后将提供专属云端 AI 法务实例、数据隔离存储与独享算力资源。
                    </p>
                  </div>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-warning/10 text-warning rounded-full text-xs font-medium border border-warning/20">
                    <icons.Clock className="w-3.5 h-3.5" />
                    当前尚未开放申请
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">
                    AI 私有助手基于 OpenClaw 开源框架，支持本地部署、数据完全自主可控。请按以下步骤完成安装：
                  </p>
                  <div className="space-y-3">
                    {[
                      { step: 1, title: '环境检测', desc: '检查系统是否满足最低硬件要求（8GB RAM、20GB 磁盘空间）' },
                      { step: 2, title: '下载 OpenClaw', desc: '从官方仓库拉取 OpenClaw 运行时和法律领域模型包' },
                      { step: 3, title: '配置服务', desc: '设置本地推理引擎、隐私策略和数据存储路径' },
                      { step: 4, title: '验证连接', desc: '启动本地服务并验证与安心法务平台的通信' },
                    ].map((item) => (
                      <div key={item.step} className="flex gap-3">
                        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                          {item.step}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{item.title}</p>
                          <p className="text-xs text-muted-foreground">{item.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
            <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
              <button
                onClick={() => setShowHardwareSetup(false)}
                className={`${buttonStyle.sm} px-4 py-2 text-muted-foreground hover:bg-muted`}
              >
                {privacyMode === PrivacyMode.CLOUD ? '知道了' : '稍后安装'}
              </button>
              {privacyMode === PrivacyMode.CLOUD && (
                <button
                  onClick={() => {
                    setShowHardwareSetup(false)
                    navigate('/pricing')
                  }}
                  className={`${buttonStyle.sm} px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm`}
                >
                  查看企业方案
                </button>
              )}
              {privacyMode !== PrivacyMode.CLOUD && (
                <>
                  <button
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(OPENCLAW_SETUP_GUIDE)
                        toast.success('安装说明已复制')
                      } catch {
                        toast.info('请根据弹窗中的步骤手动完成部署')
                      }
                    }}
                    className={`${buttonStyle.sm} px-4 py-2 text-muted-foreground hover:bg-muted`}
                  >
                    复制安装说明
                  </button>
                  <button
                    onClick={() => {
                      setOpenClawInstalled(true)
                      setShowHardwareSetup(false)
                      toggleHardwareConnection()
                      toast.success('已标记为本地部署完成')
                    }}
                    className={`${buttonStyle.sm} px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm`}
                  >
                    我已完成部署
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
