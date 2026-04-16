/**
 * OfflineResourceManager — 离线资源管理组件（V2 架构）
 *
 * 在设置页中嵌入，让本地模式用户可以下载法律智库、模板等资源包。
 * 下载后即使切到本地模式也能使用。
 *
 * 技术方案：
 * - 在混合/云端模式下显示可下载资源列表
 * - 资源分类：法律法规库、合同模板、知识图谱数据
 * - 下载状态持久化到 localStorage
 * - 实际下载逻辑由 Tauri 原生或 IndexedDB 实现
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { usePrivacy, PrivacyMode } from '@/context/PrivacyContext'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface ResourcePack {
  id: string
  name: string
  description: string
  category: 'laws' | 'templates' | 'knowledge_graph' | 'cases'
  sizeLabel: string
  version: string
  lastUpdated: string
}

// 可下载的资源包定义
const RESOURCE_PACKS: ResourcePack[] = [
  {
    id: 'laws_civil',
    name: '民事法律法规',
    description: '民法典、民事诉讼法及相关司法解释',
    category: 'laws',
    sizeLabel: '约 120MB',
    version: '2026.04',
    lastUpdated: '2026-04-01',
  },
  {
    id: 'laws_commercial',
    name: '商事法律法规',
    description: '公司法、合伙企业法、证券法等',
    category: 'laws',
    sizeLabel: '约 95MB',
    version: '2026.04',
    lastUpdated: '2026-04-01',
  },
  {
    id: 'laws_labor',
    name: '劳动法律法规',
    description: '劳动法、劳动合同法、社会保险法等',
    category: 'laws',
    sizeLabel: '约 65MB',
    version: '2026.04',
    lastUpdated: '2026-04-01',
  },
  {
    id: 'templates_contracts',
    name: '合同模板库',
    description: '50+ 常用合同模板（买卖、服务、租赁、劳动等）',
    category: 'templates',
    sizeLabel: '约 15MB',
    version: '2026.04',
    lastUpdated: '2026-04-01',
  },
  {
    id: 'templates_documents',
    name: '法律文书模板',
    description: '律师函、起诉状、答辩状、法律意见书等',
    category: 'templates',
    sizeLabel: '约 8MB',
    version: '2026.04',
    lastUpdated: '2026-04-01',
  },
  {
    id: 'knowledge_graph_core',
    name: '知识图谱核心数据',
    description: '法律概念关系图谱、常用法条索引',
    category: 'knowledge_graph',
    sizeLabel: '约 200MB',
    version: '2026.04',
    lastUpdated: '2026-04-01',
  },
  {
    id: 'cases_typical',
    name: '典型案例库',
    description: '各领域精选典型案例及裁判要旨',
    category: 'cases',
    sizeLabel: '约 350MB',
    version: '2026.04',
    lastUpdated: '2026-04-01',
  },
]

const CATEGORY_LABELS: Record<string, string> = {
  laws: '法律法规',
  templates: '文档模板',
  knowledge_graph: '知识图谱',
  cases: '案例库',
}

type DownloadStatus = 'not_downloaded' | 'downloading' | 'downloaded' | 'update_available'

function getStoredStatus(id: string): DownloadStatus {
  return (localStorage.getItem(`offline_resource_${id}`) as DownloadStatus) || 'not_downloaded'
}

function setStoredStatus(id: string, status: DownloadStatus) {
  localStorage.setItem(`offline_resource_${id}`, status)
}

export function OfflineResourceManager() {
  const { mode } = usePrivacy()
  const [statuses, setStatuses] = useState<Record<string, DownloadStatus>>({})
  const [downloading, setDownloading] = useState<string | null>(null)

  // 初始化状态
  useEffect(() => {
    const s: Record<string, DownloadStatus> = {}
    for (const pack of RESOURCE_PACKS) {
      s[pack.id] = getStoredStatus(pack.id)
    }
    setStatuses(s)
  }, [])

  const isLocalOnly = mode === PrivacyMode.LOCAL

  const handleDownload = async (packId: string) => {
    if (isLocalOnly) return
    setDownloading(packId)
    // 模拟下载（实际由 Tauri/IndexedDB 实现）
    setStatuses(prev => ({ ...prev, [packId]: 'downloading' }))
    await new Promise(resolve => setTimeout(resolve, 2000))
    setStoredStatus(packId, 'downloaded')
    setStatuses(prev => ({ ...prev, [packId]: 'downloaded' }))
    setDownloading(null)
  }

  // 按分类分组
  const categories = Object.entries(CATEGORY_LABELS)

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-semibold text-foreground mb-1">离线资源管理</h3>
        <p className="text-sm text-muted-foreground">
          下载法律数据包后，即使在本地模式下也能使用法律智库和模板功能。
        </p>
        {isLocalOnly && (
          <div className="mt-2 flex items-center gap-2 text-xs text-warning bg-warning/10 border border-warning/20 rounded-lg px-3 py-2">
            <icons.AlertCircle className="w-4 h-4 shrink-0" />
            请先切换到混合或云端模式再下载资源包
          </div>
        )}
      </div>

      {categories.map(([catKey, catLabel]) => {
        const packs = RESOURCE_PACKS.filter(p => p.category === catKey)
        if (packs.length === 0) return null

        const downloadedCount = packs.filter(p => statuses[p.id] === 'downloaded').length

        return (
          <Card key={catKey}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center justify-between">
                {catLabel}
                <Badge variant="secondary" className="text-[10px]">
                  {downloadedCount}/{packs.length} 已下载
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="divide-y divide-border">
                {packs.map(pack => {
                  const status = statuses[pack.id] || 'not_downloaded'
                  const isCurrentlyDownloading = downloading === pack.id

                  return (
                    <div key={pack.id} className="flex items-center justify-between py-3 gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground">{pack.name}</span>
                          <span className="text-[10px] text-muted-foreground">{pack.sizeLabel}</span>
                          {status === 'downloaded' && (
                            <Badge variant="outline" className="text-[10px] text-success border-success/30">
                              v{pack.version}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">{pack.description}</p>
                      </div>
                      <div className="shrink-0">
                        {status === 'downloaded' ? (
                          <div className="flex items-center gap-1.5 text-success">
                            <icons.CheckCircle className="w-4 h-4" />
                            <span className="text-xs font-medium">已下载</span>
                          </div>
                        ) : isCurrentlyDownloading ? (
                          <div className="flex items-center gap-1.5 text-primary">
                            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                              <icons.Loader2 className="w-4 h-4" />
                            </motion.div>
                            <span className="text-xs">下载中...</span>
                          </div>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDownload(pack.id)}
                            disabled={isLocalOnly}
                            className="text-xs h-8"
                          >
                            <icons.Download className="w-3.5 h-3.5 mr-1" />
                            下载
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
