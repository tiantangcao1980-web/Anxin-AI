/**
 * ClientPortal · 客户自助门户（Editorial Luxury 改造 · Phase 2.1）
 *
 * 旧版：cardStyle.base + bg-primary/5 提示卡 + 药丸 Tab + 色块按钮。
 * 新版：EditorialPageHeader + 左侧 hairline tracker 提示 + Editorial 下划线 Tab。
 *
 * 当前版本优先保证用户不会看到伪造业务数据：
 * 展示门户能力说明 + 空状态 + 跳转至消息中心入口。
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ShieldCheck, Scale, FileText, DollarSign, MessageSquare,
} from 'lucide-react'

import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import { cn } from '@/components/ui/utils'

type PortalTab = 'cases' | 'documents' | 'billing' | 'messages'

const TABS: { id: PortalTab; label: string; labelEn: string; icon: typeof Scale }[] = [
  { id: 'cases',     labelEn: 'Cases',     label: '案件进度', icon: Scale },
  { id: 'documents', labelEn: 'Docs',      label: '共享文档', icon: FileText },
  { id: 'billing',   labelEn: 'Billing',   label: '费用账单', icon: DollarSign },
  { id: 'messages',  labelEn: 'Messages',  label: '在线沟通', icon: MessageSquare },
]

export default function ClientPortal() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<PortalTab>('cases')

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-10">
        <EditorialPageHeader
          tracker={['Network', '客户门户']}
          title="客户门户"
          description="案件进度 · 共享文档 · 费用账单 · 在线沟通 — 一键查阅与互动。"
        />

        {/* 早期接入提示 */}
        <aside className="border-l-2 border-primary/40 pl-4 py-2 mb-10">
          <div className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-primary mb-1">
            <ShieldCheck className="w-3 h-3 stroke-[1.5]" />
            <span>Early Access</span>
          </div>
          <p className="font-serif text-[16px] text-foreground">客户门户已进入早期接入阶段</p>
          <p className="text-[13px] text-muted-foreground leading-relaxed mt-1 max-w-2xl">
            当前版本优先提供真实入口，不再展示伪造案件、文档和账单数据。
            客户可先通过消息中心与律师沟通，后续会接入共享案件与账单能力。
          </p>
        </aside>

        {/* Editorial 下划线 Tab */}
        <nav className="flex items-end gap-8 border-b border-border mb-10 overflow-x-auto" role="tablist" aria-label="门户导航">
          {TABS.map((tab) => {
            const active = activeTab === tab.id
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'relative py-3 inline-flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.16em] transition-colors whitespace-nowrap',
                  active
                    ? 'text-foreground after:absolute after:left-0 after:right-0 after:bottom-0 after:h-px after:bg-primary'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="w-3.5 h-3.5 stroke-[1.5]" />
                <span>{tab.labelEn}</span>
                <span className="text-foreground/30" aria-hidden>·</span>
                <span className="normal-case tracking-normal">{tab.label}</span>
              </button>
            )
          })}
        </nav>

        {activeTab === 'cases' && (
          <EmptyState
            tracker="Cases · 空状态"
            icon={Scale}
            title="暂无可查看的委托案件"
            description="律师共享案件进度后，您可以在这里查看处理状态、关键节点和最近更新。"
            actionLabel="前往消息中心"
            onAction={() => navigate('/messages')}
          />
        )}
        {activeTab === 'documents' && (
          <EmptyState
            tracker="Documents · 空状态"
            icon={FileText}
            title="暂无共享文档"
            description="当律师向您共享委托合同、证据材料或法律意见书后，您可以在这里直接查看和下载。"
          />
        )}
        {activeTab === 'billing' && (
          <EmptyState
            tracker="Billing · 空状态"
            icon={DollarSign}
            title="暂无账单记录"
            description="律师生成费用清单并发起支付后，您可以在这里查看账单明细、支付状态和历史记录。"
          />
        )}
        {activeTab === 'messages' && (
          <EmptyState
            tracker="Messages · 空状态"
            icon={MessageSquare}
            title="在线沟通已接入消息中心"
            description="当前请通过消息中心与委托律师实时沟通，后续会在客户门户内提供更轻量的会话视图。"
            actionLabel="前往消息中心"
            onAction={() => navigate('/messages')}
          />
        )}
      </div>
    </div>
  )
}

function EmptyState({
  tracker, icon: Icon, title, description, actionLabel, onAction,
}: {
  tracker: string
  icon: typeof Scale
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
}) {
  return (
    <div className="text-center py-20">
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
        {tracker}
      </div>
      <Icon className="w-12 h-12 stroke-[1] text-foreground/20 mx-auto mb-5" />
      <h3 className="font-serif text-[22px] text-foreground mb-2">{title}</h3>
      <p className="text-[13px] text-muted-foreground max-w-md mx-auto leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-6 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
