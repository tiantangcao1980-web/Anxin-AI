/**
 * RagDashboardPage — RAG 数据看板入口（V3 P13-D）
 *
 * 路由：/v3/rag
 *
 * 内容：
 *   - 顶部介绍 + 数据概览（文档总数 / segments 总数 / KG 实体数 / 跨模态边占比）
 *   - 4 个模块卡片：上传 / 文档库 / 知识图谱 / 多模态查询
 */

import { useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Database, FilePlus2, Library, Network, Search } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import { useRagStore } from '@/lib/store/ragStore'
import type { Modality } from '@/lib/api/rag'
import { MODALITIES, modalityVisual } from '@/components/v3/rag/modalityStyle'

interface ModuleCard {
  title: string
  description: string
  icon: typeof FilePlus2
  to: string
  cta: string
}

const MODULE_CARDS: ModuleCard[] = [
  {
    title: '多模态上传',
    description: '拖拽 PDF / 扫描件 / Word，自动识别文本、图像、表格、公式、印章 5 种模态',
    icon: FilePlus2,
    to: '/v3/rag/ingest',
    cta: '上传文档',
  },
  {
    title: '文档库',
    description: '浏览已 ingest 的文档，查看章/条/款/项 layout 树和 segments 预览',
    icon: Library,
    to: '/v3/rag/library',
    cta: '查看文档',
  },
  {
    title: '跨模态知识图谱',
    description: '可视化 entities 与 relations，跨模态边用虚线 + 渐变特殊样式标识',
    icon: Network,
    to: '/v3/rag/kg',
    cta: '打开图谱',
  },
  {
    title: '多模态 VLM 查询',
    description: '调节 5 模态权重 → 检索 → 答案 + visual grounding 高亮 + 引文跳转',
    icon: Search,
    to: '/v3/rag/query',
    cta: '开始查询',
  },
]

export default function RagDashboardPage() {
  const navigate = useNavigate()

  const documents = useRagStore((s) => s.documents)
  const loadDocuments = useRagStore((s) => s.loadDocuments)
  const currentKG = useRagStore((s) => s.currentKG)
  const loadAggregateKG = useRagStore((s) => s.loadAggregateKG)

  useEffect(() => {
    if (documents.length === 0) void loadDocuments()
  }, [documents.length, loadDocuments])

  useEffect(() => {
    if (!currentKG) void loadAggregateKG()
  }, [currentKG, loadAggregateKG])

  // 概览统计
  const stats = useMemo(() => {
    const totalSegments = documents.reduce((acc, d) => acc + d.segments_count, 0)
    const modalityTotals: Record<Modality, number> = {
      text: 0,
      image: 0,
      table: 0,
      formula: 0,
      seal: 0,
    }
    documents.forEach((d) => {
      MODALITIES.forEach((m) => {
        modalityTotals[m] += d.modality_breakdown[m] ?? 0
      })
    })
    const totalEntities = currentKG?.entities.length ?? 0
    const crossModalRatio = currentKG?.cross_modal_ratio ?? 0
    return { totalSegments, modalityTotals, totalEntities, crossModalRatio }
  }, [documents, currentKG])

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      {/* 顶部 */}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Database className="size-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight text-foreground">RAG 数据看板</h1>
              <Badge variant="secondary" className="rounded-full px-2 py-0 text-[10px] uppercase tracking-wide">
                Beta
              </Badge>
            </div>
            <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
              多模态文档解析 + 跨模态知识图谱 + VLM 检索的统一入口。前端仍在 mock 模式 —
              P13-A/B/C 真接口 ready 后切 <code className="rounded bg-muted px-1 py-0.5 text-[11px]">VITE_RAG_MOCK=false</code>。
            </p>
          </div>
        </div>
      </header>

      {/* 概览统计 */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="p-4">
          <p className="text-[11px] text-muted-foreground">文档总数</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">
            {documents.length}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] text-muted-foreground">Segments 总数</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">
            {stats.totalSegments}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] text-muted-foreground">KG 实体数</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">
            {stats.totalEntities}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] text-muted-foreground">跨模态边占比</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">
            {(stats.crossModalRatio * 100).toFixed(0)}%
          </p>
        </Card>
      </section>

      {/* 模态分布条 */}
      <Card className="p-4">
        <p className="mb-2 text-xs font-medium text-foreground">模态分布</p>
        <div className="flex flex-wrap items-center gap-3">
          {MODALITIES.map((m) => {
            const v = modalityVisual(m)
            const n = stats.modalityTotals[m]
            return (
              <div
                key={m}
                className={`flex items-center gap-2 rounded-full border ${v.border} ${v.bg} px-3 py-1.5`}
              >
                <span aria-hidden>{v.emoji}</span>
                <span className={`text-xs font-medium ${v.text}`}>{v.label}</span>
                <span className={`text-xs font-semibold tabular-nums ${v.text}`}>{n}</span>
              </div>
            )
          })}
        </div>
      </Card>

      {/* 4 模块卡片 */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {MODULE_CARDS.map((mod) => {
          const Icon = mod.icon
          return (
            <Card
              key={mod.to}
              className="group cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-card"
              onClick={() => navigate(mod.to)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Icon className="size-5" />
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-base">{mod.title}</CardTitle>
                    <CardDescription className="mt-0.5 text-xs">
                      {mod.description}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-auto flex"
                  iconRight={<ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />}
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(mod.to)
                  }}
                >
                  {mod.cta}
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </section>
    </div>
  )
}
