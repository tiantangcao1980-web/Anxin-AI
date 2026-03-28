import { icons } from '@/lib/icons'
import { heading, buttonStyle, iconSize } from '@/lib/design-tokens'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi, User as ApiUser } from '../lib/api'
import { useAuthStore, useUIStore } from '../lib/store'
import { toast } from 'sonner'

interface UserProfileProps {
  onClose: () => void
}

export function UserProfile({ onClose }: UserProfileProps) {
  const navigate = useNavigate()
  const { theme, setTheme } = useUIStore()
  const { user: storeUser, logout: storeLogout } = useAuthStore()
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
          </div>

          {/* 后台管理入口 — 根据权限显示 */}
          {isAdmin && (
            <div className="mb-4 pt-3 border-t border-border">
              <button
                onClick={() => handleNavigate('/admin')}
                className={`w-full flex items-center gap-3 p-3 ${buttonStyle.ghost} text-left`}
              >
                <icons.Shield className={`${iconSize.md} text-primary`} />
                <span className={`${heading.card} text-primary`}>后台管理</span>
                <icons.ChevronRight className={`${iconSize.sm} text-primary/60 ml-auto`} />
              </button>
            </div>
          )}

          {/* Settings */}
          <div className="space-y-3 pt-3 border-t border-border">
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-xl">
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
                className={`w-12 h-7 rounded-full transition-colors ${
                  isDark ? 'bg-primary' : 'bg-border'
                }`}
              >
                <div
                  className={`w-6 h-6 bg-background rounded-full my-0.5 shadow-sm transition-transform ${
                    isDark ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-xl">
              <div className="flex items-center gap-3">
                <icons.Bell className={`${iconSize.md} text-muted-foreground`} />
                <span className={heading.card}>推送通知</span>
              </div>
              <button
                onClick={toggleNotifications}
                className={`w-12 h-7 rounded-full transition-colors ${
                  notifications ? 'bg-primary' : 'bg-border'
                }`}
              >
                <div
                  className={`w-6 h-6 bg-background rounded-full my-0.5 shadow-sm transition-transform ${
                    notifications ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
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
    </div>
  )
}
