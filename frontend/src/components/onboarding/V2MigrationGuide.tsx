/**
 * V2MigrationGuide — 老用户升级引导组件
 *
 * 首次登录 V2 时弹出：
 * - 律师用户 → "我们为您准备了律师专属工作台 →"
 * - 企业用户 → "升级到 V2，体验智能法务新功能"
 * - 个人用户 → "3 天免费体验云端 AI 法务"
 *
 * 只显示一次，通过 localStorage 标记。
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { useAuthStore } from '@/lib/store'
import { Button } from '@/components/ui/button'

const STORAGE_KEY = 'v2_migration_dismissed'

interface GuideConfig {
  title: string
  description: string
  primaryAction: string
  primaryPath: string
  secondaryAction: string
}

const GUIDE_MAP: Record<string, GuideConfig> = {
  platform_lawyer: {
    title: '欢迎来到安心法务 Pro',
    description: '我们为律师打造了专属工作台：案源市场、客户管理、智能文档、账单追踪，一站搞定。',
    primaryAction: '进入律师工作台',
    primaryPath: '/pro/dashboard',
    secondaryAction: '稍后再说',
  },
  institution: {
    title: '律所管理全面升级',
    description: '新增案源市场、利益冲突检查、团队分级权限，让律所管理更高效。',
    primaryAction: '进入律所管理台',
    primaryPath: '/pro/dashboard',
    secondaryAction: '稍后再说',
  },
  enterprise: {
    title: '企业法务智能升级',
    description: 'V2 新增三态运行模式：敏感数据可纯本地处理，AI 能力按需使用。',
    primaryAction: '开始体验',
    primaryPath: '/chat',
    secondaryAction: '了解订阅方案',
  },
  individual: {
    title: '欢迎体验安心法务 V2',
    description: '免费获得 3 天云端体验：AI 法律咨询、合同审查、文书生成、找律师。',
    primaryAction: '开始免费体验',
    primaryPath: '/chat',
    secondaryAction: '了解更多',
  },
}

export function V2MigrationGuide() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!user) return
    const dismissed = localStorage.getItem(STORAGE_KEY)
    if (!dismissed) {
      setVisible(true)
    }
  }, [user?.id])

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, 'true')
    setVisible(false)
  }

  if (!visible || !user) return null

  const userType = user.user_type || 'individual'
  const config = GUIDE_MAP[userType] || GUIDE_MAP.individual

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-card border border-border rounded-2xl shadow-xl max-w-md w-full p-8 text-center"
          >
            {/* Logo */}
            <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-primary/10 flex items-center justify-center">
              <icons.Sparkles className="w-8 h-8 text-primary" />
            </div>

            <h2 className="text-xl font-bold text-foreground mb-2">{config.title}</h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              {config.description}
            </p>

            {/* 新功能亮点 */}
            <div className="text-left space-y-2 mb-6">
              {[
                { icon: icons.Shield, text: '三态运行模式：本地/混合/云端自由切换' },
                { icon: icons.Users, text: '双端分离：需求方与服务方独立体验' },
                { icon: icons.BarChart3, text: '智能需求发掘：苏格拉底式精准追问' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <item.icon className="w-4 h-4 text-primary shrink-0" />
                  <span className="text-xs text-foreground">{item.text}</span>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-2">
              <Button
                onClick={() => { dismiss(); navigate(config.primaryPath) }}
                className="w-full"
              >
                {config.primaryAction}
              </Button>
              <Button
                variant="ghost"
                onClick={dismiss}
                className="w-full text-muted-foreground"
              >
                {config.secondaryAction}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
