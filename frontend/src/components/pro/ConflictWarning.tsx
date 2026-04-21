/**
 * ConflictWarning — 律师投标时的利益冲突警告弹窗（V2 架构）
 *
 * 服务方端投标 API 返回 conflict_warning 时触发。
 * 展示：潜在冲突案件列表 + 冲突方 + 严重程度。
 * 律师需显式确认"我已知悉并继续"或"撤回投标"。
 */

import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { Button } from '@/components/ui/button'

export interface ConflictInfo {
  case_id: string
  case_title: string
  historical_party: string
  historical_role: string
  new_party: string
  conflict_type: string
  created_at?: string
}

export interface ConflictWarningData {
  has_conflict: boolean
  warning_level: 'none' | 'low' | 'medium' | 'high'
  conflict_count: number
  conflicts: ConflictInfo[]
}

interface ConflictWarningProps {
  warning: ConflictWarningData | null
  onConfirmAnyway: () => void
  onWithdraw: () => void
  onClose: () => void
}

const LEVEL_CONFIG = {
  low: { label: '轻微', color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/20' },
  medium: { label: '中等', color: 'text-warning', bg: 'bg-warning/15', border: 'border-warning/30' },
  high: { label: '严重', color: 'text-destructive', bg: 'bg-destructive/10', border: 'border-destructive/30' },
  none: { label: '无', color: 'text-muted-foreground', bg: 'bg-muted', border: 'border-border' },
}

export function ConflictWarning({ warning, onConfirmAnyway, onWithdraw, onClose }: ConflictWarningProps) {
  if (!warning || !warning.has_conflict) return null

  const level = warning.warning_level || 'low'
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.low

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className={`max-w-lg w-full bg-card border ${config.border} rounded-2xl shadow-xl p-6`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* 头部 */}
          <div className="flex items-start gap-3 mb-4">
            <div className={`w-10 h-10 rounded-full ${config.bg} flex items-center justify-center flex-shrink-0`}>
              <icons.AlertTriangle className={`w-5 h-5 ${config.color}`} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-foreground">
                利益冲突检测：{config.label}级别
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                系统在您的历史案件中发现了 <span className={`font-semibold ${config.color}`}>{warning.conflict_count}</span> 项潜在利益冲突
              </p>
            </div>
          </div>

          {/* 冲突列表 */}
          <div className="max-h-64 overflow-y-auto space-y-2 mb-4">
            {warning.conflicts.map((conflict, i) => (
              <div
                key={conflict.case_id + i}
                className="border border-border rounded-lg p-3 bg-muted/30"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <icons.FileText className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium text-foreground">
                    {conflict.case_title || '历史案件'}
                  </span>
                </div>
                <div className="text-xs space-y-1">
                  <div className="flex items-start gap-1">
                    <span className="text-muted-foreground shrink-0">• 历史当事人：</span>
                    <span className="text-foreground font-medium">{conflict.historical_party}</span>
                    <span className="text-[10px] text-muted-foreground">({conflict.historical_role})</span>
                  </div>
                  <div className="flex items-start gap-1">
                    <span className="text-muted-foreground shrink-0">• 新案件涉及：</span>
                    <span className={`font-medium ${config.color}`}>{conflict.new_party}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 合规提醒 */}
          <div className="bg-info/10 border border-info/20 rounded-lg p-3 mb-4">
            <p className="text-xs text-foreground leading-relaxed">
              💡 <span className="font-medium">合规提示</span>：根据《律师法》第三十九条，律师不得在同一案件中为双方当事人担任代理人，
              也不得代理与本人或其近亲属有利益冲突的法律事务。请审慎评估是否继续接此案。
            </p>
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-2">
            <Button
              variant="destructive"
              onClick={onWithdraw}
              className="flex-1"
            >
              <icons.X className="w-4 h-4 mr-1.5" />
              撤回投标（推荐）
            </Button>
            <Button
              variant="outline"
              onClick={onConfirmAnyway}
              className="flex-1"
            >
              <icons.CheckCircle className="w-4 h-4 mr-1.5" />
              已确认无冲突，继续
            </Button>
          </div>

          <p className="text-[10px] text-muted-foreground text-center mt-3">
            选择"已确认"将记录到审计日志，作为您知情同意的证据
          </p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
