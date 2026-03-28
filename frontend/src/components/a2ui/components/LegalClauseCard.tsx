/**
 * LegalClauseCard - 法律条款分析卡片
 *
 * 在对话流中展示法律条款的解析结果：
 * - 条款编号徽章 + 风险等级徽章
 * - 引用样式的条款原文
 * - AI 解读说明
 * - 修改建议（可选，带灯泡图标）
 */

import { memo } from 'react';
import { icons } from '@/lib/icons';
import { cardStyle, heading, statusBadge } from '@/lib/design-tokens';
import { cn } from '@/lib/utils';

export interface LegalClauseCardProps {
  clause: string;
  article: string;
  interpretation: string;
  risk?: 'low' | 'medium' | 'high';
  suggestion?: string;
}

const RISK_CONFIG = {
  low: {
    label: '低风险',
    badge: statusBadge.success,
    icon: icons.CheckCircle2,
  },
  medium: {
    label: '中风险',
    badge: statusBadge.warning,
    icon: icons.AlertTriangle,
  },
  high: {
    label: '高风险',
    badge: statusBadge.error,
    icon: icons.AlertTriangle,
  },
} as const;

export const LegalClauseCard = memo(function LegalClauseCard({
  clause,
  article,
  interpretation,
  risk = 'low',
  suggestion,
}: LegalClauseCardProps) {
  const riskConfig = RISK_CONFIG[risk];
  const RiskIcon = riskConfig.icon;

  return (
    <div className={cn(cardStyle.base, 'overflow-hidden')}>
      {/* 头部：条款编号 + 风险等级 */}
      <div className="flex items-center justify-between mb-3">
        <span className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold',
          statusBadge.info,
        )}>
          <icons.FileText className="w-3.5 h-3.5" />
          {article}
        </span>
        <span className={cn(
          'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold',
          riskConfig.badge,
        )}>
          <RiskIcon className="w-3.5 h-3.5" />
          {riskConfig.label}
        </span>
      </div>

      {/* 条款原文（引用样式） */}
      <div className="border-l-2 border-primary/30 pl-3 py-2 mb-3 bg-muted/30 rounded-r-lg">
        <p className="text-sm text-foreground/80 leading-relaxed italic">
          {clause}
        </p>
      </div>

      {/* AI 解读 */}
      <div className="mb-3">
        <h5 className={cn(heading.card, 'mb-1.5 flex items-center gap-1.5')}>
          <icons.Brain className="w-4 h-4 text-primary" />
          AI 解读
        </h5>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {interpretation}
        </p>
      </div>

      {/* 修改建议 */}
      {suggestion && (
        <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <icons.Lightbulb className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-xs font-semibold text-amber-700 dark:text-amber-400">
                修改建议
              </span>
              <p className="text-xs text-amber-600 dark:text-amber-400 leading-relaxed mt-1">
                {suggestion}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
