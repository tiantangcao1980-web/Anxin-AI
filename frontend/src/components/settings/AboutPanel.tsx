/**
 * AboutPanel — 设置 → 关于
 *
 * 提供：
 *   - 产品 / 版本信息
 *   - 文档与权威链接
 *   - "重新查看新手引导"按钮（清 localStorage onboarding 状态 + 刷新）
 *   - 实例 / 环境一目了然信息
 *
 * 关联：docs/plans/2026-05-22-desktop-bootstrap.md §5.4
 */

import { useCallback, useState } from 'react'
import { icons } from '@/lib/icons'
import { ONBOARDING_KEY } from '@/components/onboarding'
import { toast } from 'sonner'

const APP_VERSION = (import.meta.env.VITE_APP_VERSION as string | undefined) ?? '0.3.0'
const BUILD_TAG = (import.meta.env.VITE_BUILD_TAG as string | undefined) ?? 'dev'

const RESOURCE_LINKS = [
  {
    title: '产品蓝图',
    href: 'https://github.com/tiantangcao1980-web/Anxin-AI/blob/main/docs/plans/2026-05-22-product-blueprint.md',
    desc: '当前权威产品方向（飞书风桌面+移动+云服务）',
  },
  {
    title: '设计规范',
    href: 'https://github.com/tiantangcao1980-web/Anxin-AI/blob/main/DESIGN.md',
    desc: '色彩 / 排版 / 组件规范（§10 飞书对标）',
  },
  {
    title: '云服务契约',
    href: 'https://github.com/tiantangcao1980-web/Anxin-AI/blob/main/docs/openspec/03-cloud-services-contract.md',
    desc: 'Auth / Sync / IM 三个核心域接口',
  },
  {
    title: '安全与隐私',
    href: 'https://github.com/tiantangcao1980-web/Anxin-AI/blob/main/SECURITY.md',
    desc: '漏洞报告与安全政策',
  },
]

export function AboutPanel() {
  const [resetting, setResetting] = useState(false)

  const handleReplayOnboarding = useCallback(() => {
    setResetting(true)
    try {
      localStorage.removeItem(ONBOARDING_KEY)
      localStorage.removeItem('anxin.onboarding.completedAt')
      // banner dismiss 也清掉，确保新引导期能完整看到
      localStorage.removeItem('anxin.llm-banner.dismissedAt')
      toast.success('已重置引导记录，即将刷新页面')
      setTimeout(() => {
        window.location.href = '/chat'
        window.location.reload()
      }, 500)
    } catch {
      toast.error('localStorage 不可用，无法重置')
      setResetting(false)
    }
  }, [])

  return (
    <div className="space-y-4">
      {/* 产品信息卡 */}
      <section className="rounded-xl border border-border bg-surface-1 p-5 shadow-card">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center shadow-sm shrink-0">
            <icons.Sparkles className="w-6 h-6 text-primary-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-medium text-foreground">安心智能助手</h3>
            <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
              一个 App 搞定法务 / 财务 / 税务 / 合规 / 经营管理 / 内容产出 / 出海跨境。
              对标飞书 / 企业微信的桌面 + 移动客户端形态。
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
              <div>
                <dt className="text-muted-foreground">版本</dt>
                <dd className="text-foreground font-mono mt-0.5">{APP_VERSION}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">构建</dt>
                <dd className="text-foreground font-mono mt-0.5">{BUILD_TAG}</dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      {/* 新手引导卡 */}
      <section className="rounded-xl border border-border bg-surface-1 p-5 shadow-card">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
            <icons.BookOpen className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-foreground">新手引导</h3>
            <p className="text-xs text-muted-foreground mt-1">
              4 步快速了解：欢迎 → 隐私模式 → AI 模型配置 → 入口推荐。
              重置后会在下次进入主界面时自动弹出。
            </p>
            <button
              type="button"
              onClick={handleReplayOnboarding}
              disabled={resetting}
              className="mt-3 px-3 h-9 rounded-md border border-border bg-surface-1 hover:bg-surface-2 text-sm font-medium text-foreground transition-colors disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
            >
              <icons.RefreshCw className="w-4 h-4" />
              {resetting ? '重置中...' : '重新查看新手引导'}
            </button>
          </div>
        </div>
      </section>

      {/* 文档与资源 */}
      <section className="rounded-xl border border-border bg-surface-1 p-5 shadow-card">
        <h3 className="text-sm font-medium text-foreground">文档与资源</h3>
        <p className="text-xs text-muted-foreground mt-1">
          产品方向 / 设计规范 / 接口契约 / 安全政策（链接到 GitHub 仓库）
        </p>
        <ul className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2">
          {RESOURCE_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-md border border-border bg-surface-2 hover:border-primary hover:bg-primary/5 p-3 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-foreground truncate">{link.title}</span>
                  <icons.ArrowRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                </div>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{link.desc}</p>
              </a>
            </li>
          ))}
        </ul>
      </section>

      {/* 反馈 / 支持 */}
      <section className="rounded-xl border border-border bg-surface-1 p-5 shadow-card">
        <h3 className="text-sm font-medium text-foreground">反馈与支持</h3>
        <p className="text-xs text-muted-foreground mt-1">
          遇到问题、希望的功能或者发现安全漏洞，请通过仓库 issue 或 SECURITY.md 流程联系我们。
        </p>
      </section>
    </div>
  )
}

export default AboutPanel
