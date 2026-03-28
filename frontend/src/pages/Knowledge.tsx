/**
 * @deprecated 此页面已废弃。
 * 知识库功能已拆分为独立路由：
 *   /search          → Search.tsx（智慧搜索）
 *   /knowledge-base  → KnowledgeBase.tsx（司法智库）
 *   /knowledge-graph → KnowledgeGraph.tsx（知识图谱）
 *   /academy         → Academy.tsx（司法学院）
 *
 * 路由 /knowledge 已重定向至 /knowledge-base。
 * 保留此文件仅作历史参考，不再在主路由中使用。
 *
 * 原设计：知识中心 - 左侧边栏 + 内容区布局
 * 导航项：智慧搜索 | 知识库 | 知识图谱 | 经验 | 进化
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'

import { SmartSearch } from '@/components/knowledge-center/SmartSearch'
import { KnowledgeBaseManager } from '@/components/knowledge-center/KnowledgeBaseManager'
import { KnowledgeGraphExplorer } from '@/components/knowledge-center/KnowledgeGraphExplorer'
import { ExperienceMemory, EvolutionEngine } from '@/components/knowledge-center/ExperienceCenter'

const NAV_ITEMS = [
  {
    id: 'search',
    label: '智慧搜索',
    icon: icons.Search,
    accent: '#6366f1',        // indigo
    bgActive: 'bg-primary/5',
    textActive: 'text-primary',
    iconActive: 'text-primary',
    dotColor: 'bg-primary',
  },
  {
    id: 'bases',
    label: '知识库',
    icon: icons.Database,
    accent: '#0ea5e9',        // sky
    bgActive: 'bg-sky-50 dark:bg-sky-950/30',
    textActive: 'text-sky-700 dark:text-sky-400',
    iconActive: 'text-sky-600 dark:text-sky-400',
    dotColor: 'bg-sky-500',
  },
  {
    id: 'graph',
    label: '知识图谱',
    icon: icons.Network,
    accent: '#8b5cf6',        // violet
    bgActive: 'bg-violet-50 dark:bg-violet-950/30',
    textActive: 'text-violet-700 dark:text-violet-400',
    iconActive: 'text-violet-600 dark:text-violet-400',
    dotColor: 'bg-violet-500',
  },
  {
    id: 'experience',
    label: '经验',
    icon: icons.Brain,
    accent: '#f59e0b',        // amber
    bgActive: 'bg-amber-50 dark:bg-amber-950/30',
    textActive: 'text-amber-700 dark:text-amber-400',
    iconActive: 'text-amber-600 dark:text-amber-400',
    dotColor: 'bg-amber-500',
  },
  {
    id: 'evolution',
    label: '进化',
    icon: icons.Zap,
    accent: '#10b981',        // emerald
    bgActive: 'bg-emerald-50 dark:bg-emerald-950/30',
    textActive: 'text-emerald-700 dark:text-emerald-400',
    iconActive: 'text-emerald-600 dark:text-emerald-400',
    dotColor: 'bg-emerald-500',
  },
] as const

type NavId = typeof NAV_ITEMS[number]['id']

export default function Knowledge() {
  const [activeNav, setActiveNav] = useState<NavId>('search')

  return (
    <div className="h-full flex bg-background">
      {/* ====== 左侧边栏 ====== */}
      <aside className="w-48 flex-shrink-0 border-r border-border flex flex-col bg-muted/30">
        {/* 头部标识 */}
        <div className="px-4 pt-5 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-sm">
              <icons.BookOpen className={`${iconSize.sm} text-white`} />
            </div>
            <div>
              <h2 className={`${heading.card} leading-tight`}>知识中心</h2>
              <p className={`${heading.micro} leading-tight`}>Knowledge Hub</p>
            </div>
          </div>
        </div>

        {/* 导航列表 */}
        <nav className="flex-1 px-2.5 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const isActive = activeNav === item.id
            return (
              <button
                key={item.id}
                onClick={() => setActiveNav(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all relative group ${
                  isActive
                    ? `${item.bgActive} ${item.textActive}`
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/80'
                }`}
              >
                {/* 左侧激活指示条 */}
                {isActive && (
                  <motion.div
                    layoutId="knowledge-nav-indicator"
                    className={`absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full ${item.dotColor}`}
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <item.icon className={`${iconSize.sm} flex-shrink-0 ${isActive ? item.iconActive : 'text-muted-foreground group-hover:text-foreground/70'}`} />
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        {/* 底部装饰 */}
        <div className="px-4 py-4">
          <div className="text-[10px] text-muted-foreground/40 leading-relaxed">
            RAG · Neo4j · RLHF-Lite
          </div>
        </div>
      </aside>

      {/* ====== 主内容区 ====== */}
      <main className="flex-1 overflow-hidden bg-background">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeNav}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            transition={{ duration: 0.12, ease: 'easeOut' }}
            className="h-full"
          >
            {activeNav === 'search' && <SmartSearch />}
            {activeNav === 'bases' && <KnowledgeBaseManager />}
            {activeNav === 'graph' && <KnowledgeGraphExplorer />}
            {activeNav === 'experience' && <ExperienceMemory />}
            {activeNav === 'evolution' && <EvolutionEngine />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
