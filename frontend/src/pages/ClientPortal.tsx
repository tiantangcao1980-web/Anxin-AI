/**
 * ClientPortal — 客户自助门户（早期接入版）
 *
 * 当前版本优先保证用户不会看到伪造业务数据：
 * - 展示门户能力说明和空状态
 * - 提供跳转到真实消息中心的入口
 * - 待后端客户门户 API 接入后再补真实案件/文档/账单数据
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { cardStyle, heading, buttonStyle, statusBadge, inputStyle } from '@/lib/design-tokens'
import { PageContainer } from '@/components/ui/PageContainer'
import { toast } from 'sonner'

type PortalTab = 'cases' | 'documents' | 'billing' | 'messages'

export default function ClientPortal() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<PortalTab>('cases')
  const [expandedCase, setExpandedCase] = useState<string | null>(null)

  const tabs: { id: PortalTab; label: string; icon: any }[] = [
    { id: 'cases', label: '案件进度', icon: icons.Scale },
    { id: 'documents', label: '共享文档', icon: icons.FileText },
    { id: 'billing', label: '费用账单', icon: icons.DollarSign },
    { id: 'messages', label: '在线沟通', icon: icons.MessageSquare },
  ]

  const EmptyState = ({
    icon: Icon,
    title,
    description,
    actionLabel,
    onAction,
  }: {
    icon: typeof icons.MessageSquare
    title: string
    description: string
    actionLabel?: string
    onAction?: () => void
  }) => (
    <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16 text-center`}>
      <Icon className="w-12 h-12 mb-3 text-muted-foreground/30" />
      <p className={heading.section}>{title}</p>
      <p className="text-sm text-muted-foreground mt-2 max-w-md">{description}</p>
      {actionLabel && onAction && (
        <button onClick={onAction} className={`${buttonStyle.primary} mt-5`}>
          {actionLabel}
        </button>
      )}
    </div>
  )

  return (
    <PageContainer title="客户门户" description="查看案件进度、文档、账单">
      <div className={`${cardStyle.base} mb-6 border-primary/20 bg-primary/5`}>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary text-primary-foreground flex items-center justify-center shrink-0">
            <icons.ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <p className={heading.card}>客户门户已进入早期接入阶段</p>
            <p className="text-sm text-muted-foreground mt-1">
              当前版本优先提供真实入口，不再展示伪造案件、文档和账单数据。客户可先通过消息中心与律师沟通，后续会接入共享案件与账单能力。
            </p>
          </div>
        </div>
      </div>

      {/* Tab 导航 */}
      <div className="flex items-center gap-1 mb-6 overflow-x-auto scrollbar-hide">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* 案件进度 */}
      {activeTab === 'cases' && (
        <EmptyState
          icon={icons.Scale}
          title="暂无可查看的委托案件"
          description="律师共享案件进度后，您可以在这里查看处理状态、关键节点和最近更新。"
          actionLabel="前往消息中心"
          onAction={() => navigate('/messages')}
        />
      )}

      {/* 共享文档 */}
      {activeTab === 'documents' && (
        <EmptyState
          icon={icons.FileText}
          title="暂无共享文档"
          description="当律师向您共享委托合同、证据材料或法律意见书后，您可以在这里直接查看和下载。"
        />
      )}

      {/* 费用账单 */}
      {activeTab === 'billing' && (
        <EmptyState
          icon={icons.DollarSign}
          title="暂无账单记录"
          description="律师生成费用清单并发起支付后，您可以在这里查看账单明细、支付状态和历史记录。"
        />
      )}

      {/* 在线沟通 */}
      {activeTab === 'messages' && (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <icons.MessageSquare className="w-12 h-12 mb-3 opacity-20" />
          <p className="text-sm">在线沟通已接入消息中心</p>
          <p className="text-xs mt-1 opacity-60">当前请通过消息中心与委托律师实时沟通，后续会在客户门户内提供更轻量的会话视图。</p>
          <button onClick={() => navigate('/messages')} className={`${buttonStyle.primary} mt-4`}>
            前往消息中心
          </button>
        </div>
      )}
    </PageContainer>
  )
}
