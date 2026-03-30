import { icons } from '@/lib/icons'
import { heading, buttonStyle, iconSize } from '@/lib/design-tokens'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi, User as ApiUser } from '../lib/api'
import { useAuthStore, useUIStore } from '../lib/store'
import { usePrivacy, PrivacyMode, HardwareStatus as HWStatus } from '../context/PrivacyContext'
import { toast } from 'sonner'

interface UserProfileProps {
  onClose: () => void
}

export function UserProfile({ onClose }: UserProfileProps) {
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
    } catch {
      // 即使后端不可用也执行本地登出
    }
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
    { icon: icons.HelpCircle, label: '帮助中心', action: () => toast.info('帮助文档即将上线') },
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
        {/* Header */}
        <div className="p-6 bg-primary text-primary-foreground">
          <div className="flex items-start justify-between mb-6">
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
          <p className={`${heading.muted} text-primary-foreground/80`}>{user?.email || '请登录后查看'}</p>
          {user?.role && (
            <span className="inline-block mt-2 px-2 py-0.5 rounded text-xs bg-white/20">{user.role}</span>
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
          </div>

          {/* AI 私有助手 + 数据隐私保护级别 */}
          <div className="space-y-3 pt-3 border-t border-border">
            {/* AI 私有助手 */}
            <div className="p-3 bg-muted/50 rounded-xl space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <icons.Cpu className={`${iconSize.md} ${
                    hardwareStatus === HWStatus.CONNECTED
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : !openClawInstalled
                        ? 'text-amber-600 dark:text-amber-400'
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
                      ? 'bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-900/50'
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
                    className="h-full bg-emerald-500 rounded-full transition-all duration-500"
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
            className="w-full flex items-center justify-center gap-2 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 dark:hover:bg-amber-950/50 active:scale-[0.98] rounded-lg px-4 py-2 text-sm font-medium transition-all"
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
                    <h3 className="text-lg font-bold text-foreground">AI 私有助手</h3>
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
                    <h4 className="text-base font-semibold text-foreground mb-1">云端私有助手</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      云端私有助手正在开发中，将为您提供专属的云端 AI 法务服务实例，
                      数据隔离存储，独享算力资源。
                    </p>
                  </div>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 rounded-full text-xs font-medium border border-amber-200 dark:border-amber-800">
                    <icons.Clock className="w-3.5 h-3.5" />
                    预计后续版本迭代开放
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
              {privacyMode !== PrivacyMode.CLOUD && (
                <button
                  onClick={() => {
                    setOpenClawInstalled(true)
                    setShowHardwareSetup(false)
                    toggleHardwareConnection()
                    toast.success('AI 私有助手配置完成')
                  }}
                  className={`${buttonStyle.sm} px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm`}
                >
                  开始安装
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
