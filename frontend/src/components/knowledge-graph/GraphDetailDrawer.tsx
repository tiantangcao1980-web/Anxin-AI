/**
 * GraphDetailDrawer - 知识图谱实体详情侧边抽屉
 * 从右侧滑入，显示实体属性、关系、操作按钮
 */

import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { heading, buttonStyle, cardStyle, iconSize, statusBadge } from '@/lib/design-tokens'

interface EntityDetail {
  name: string
  type: string
  properties: Record<string, string>
  outEdges: { target: string; label: string }[]
  inEdges: { source: string; label: string }[]
  documents?: { id: string; title: string }[]
}

interface Props {
  detail: EntityDetail | null
  loading: boolean
  onClose: () => void
  onClickRelation: (name: string) => void
  onExpandInGraph: () => void
  onEditEntity?: () => void
  onDeleteEntity?: () => void
  /** 联动智能调查 — 点击后跳转到尽调页面 */
  onInvestigate?: (entityName: string) => void
}

const TYPE_COLORS: Record<string, string> = {
  '法规': '#22c55e', '案例': '#3b82f6', '当事人': '#f59e0b', '机构': '#8b5cf6',
  '律师': '#ec4899', '其他': '#6b7280',
  law: '#22c55e', entity: '#3b82f6', document: '#f97316', query: '#64748b', conclusion: '#a855f7',
}

const TYPE_LABELS: Record<string, string> = {
  '法规': '法规', '案例': '案例', '当事人': '当事人', '机构': '机构', '律师': '律师', '其他': '其他',
  law: '法规', entity: '实体', document: '文档', query: '查询', conclusion: '结论',
}

export function GraphDetailDrawer({ detail, loading, onClose, onClickRelation, onExpandInGraph, onEditEntity, onDeleteEntity, onInvestigate }: Props) {
  const visible = loading || !!detail

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ x: 320, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 320, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 320, damping: 30 }}
          className="absolute top-0 right-0 w-80 h-full z-20 border-l border-border bg-background shadow-2xl flex flex-col"
        >
          {/* 头部 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
            <h4 className={heading.card}>实体详情</h4>
            <button onClick={onClose} className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
              <icons.X className={iconSize.sm} />
            </button>
          </div>

          {/* 内容 */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => <div key={i} className="h-8 bg-muted animate-pulse rounded-lg" />)}
              </div>
            ) : detail ? (
              <>
                {/* 实体卡片 */}
                <div
                  className="text-center p-5 rounded-xl"
                  style={{
                    background: `linear-gradient(135deg, ${TYPE_COLORS[detail.type] || '#6b7280'}15, ${TYPE_COLORS[detail.type] || '#6b7280'}05)`,
                    border: `1px solid ${TYPE_COLORS[detail.type] || '#6b7280'}30`,
                  }}
                >
                  <div
                    className="w-12 h-12 rounded-full mx-auto mb-2 flex items-center justify-center text-white font-bold text-lg"
                    style={{ backgroundColor: TYPE_COLORS[detail.type] || '#6b7280' }}
                  >
                    {detail.name.charAt(0)}
                  </div>
                  <div className="font-bold text-sm text-foreground">{detail.name}</div>
                  <span
                    className="inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full"
                    style={{
                      backgroundColor: (TYPE_COLORS[detail.type] || '#6b7280') + '20',
                      color: TYPE_COLORS[detail.type] || '#6b7280',
                    }}
                  >
                    {TYPE_LABELS[detail.type] || detail.type}
                  </span>
                </div>

                {/* 属性 */}
                {Object.keys(detail.properties).length > 0 && (
                  <div>
                    <h5 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">属性</h5>
                    <div className="space-y-1">
                      {Object.entries(detail.properties).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-xs py-1 border-b border-border/50">
                          <span className="text-muted-foreground">{k}</span>
                          <span className="text-foreground font-medium truncate ml-2 max-w-[160px]">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 出关系 */}
                {detail.outEdges.length > 0 && (
                  <div>
                    <h5 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                      出关系 ({detail.outEdges.length})
                    </h5>
                    <div className="space-y-1 max-h-36 overflow-y-auto">
                      {detail.outEdges.map((e, i) => (
                        <button
                          key={i}
                          onClick={() => onClickRelation(e.target)}
                          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs hover:bg-muted transition-colors text-left"
                        >
                          <icons.ArrowRight className="w-3 h-3 text-primary shrink-0" />
                          <span className="text-muted-foreground">{e.label}</span>
                          <span className="text-foreground font-medium truncate">→ {e.target}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* 入关系 */}
                {detail.inEdges.length > 0 && (
                  <div>
                    <h5 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                      入关系 ({detail.inEdges.length})
                    </h5>
                    <div className="space-y-1 max-h-36 overflow-y-auto">
                      {detail.inEdges.map((e, i) => (
                        <button
                          key={i}
                          onClick={() => onClickRelation(e.source)}
                          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs hover:bg-muted transition-colors text-left"
                        >
                          <icons.ArrowLeft className="w-3 h-3 text-muted-foreground shrink-0" />
                          <span className="text-foreground font-medium truncate">{e.source}</span>
                          <span className="text-muted-foreground">→ {e.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* 关联文档 */}
                {detail.documents && detail.documents.length > 0 && (
                  <div>
                    <h5 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                      关联文档 ({detail.documents.length})
                    </h5>
                    <div className="space-y-1">
                      {detail.documents.map(doc => (
                        <div key={doc.id} className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs bg-muted/50">
                          <icons.FileText className="w-3 h-3 text-muted-foreground shrink-0" />
                          <span className="text-foreground truncate">{doc.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : null}
          </div>

          {/* 底部操作栏 */}
          {detail && (
            <div className="px-4 py-3 border-t border-border space-y-2 shrink-0">
              <button onClick={onExpandInGraph} className={`${buttonStyle.primary} w-full justify-center flex items-center gap-1.5`}>
                <icons.Share2 className={iconSize.sm} />
                在图谱中展开
              </button>
              {onInvestigate && (detail.type === '机构' || detail.type === '当事人' || detail.type === 'entity') && (
                <button
                  onClick={() => onInvestigate(detail.name)}
                  className="w-full justify-center flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                >
                  <icons.Search className={iconSize.sm} />
                  发起尽职调查
                </button>
              )}
              <div className="flex gap-2">
                {onEditEntity && (
                  <button onClick={onEditEntity} className={`${buttonStyle.ghost} flex-1 justify-center flex items-center gap-1`}>
                    <icons.Edit className="w-3.5 h-3.5" />
                    编辑
                  </button>
                )}
                {onDeleteEntity && (
                  <button onClick={onDeleteEntity} className="flex-1 justify-center flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors">
                    <icons.Trash2 className="w-3.5 h-3.5" />
                    删除
                  </button>
                )}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
