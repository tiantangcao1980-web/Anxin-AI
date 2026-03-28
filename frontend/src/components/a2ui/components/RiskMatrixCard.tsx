/**
 * RiskMatrixCard - 风险矩阵卡片
 *
 * 在对话流中展示结构化风险评估矩阵：
 * - 标题 + 综合评分徽章
 * - 风险项列表（分类、等级、描述、缓解建议）
 * - 缓解建议可折叠展开
 */

import { memo, useState, useCallback } from 'react';
import { icons } from '@/lib/icons';
import { cardStyle, heading, statusBadge } from '@/lib/design-tokens';
import { cn } from '@/lib/utils';

export interface RiskItem {
  category: string;
  level: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  mitigation: string;
}

export interface RiskMatrixCardProps {
  title: string;
  risks: RiskItem[];
  overallScore: number;
}

const LEVEL_CONFIG = {
  low: {
    label: '低',
    badge: statusBadge.success,
    dot: 'bg-emerald-500',
    icon: icons.CheckCircle2,
  },
  medium: {
    label: '中',
    badge: statusBadge.warning,
    dot: 'bg-amber-500',
    icon: icons.AlertTriangle,
  },
  high: {
    label: '高',
    badge: statusBadge.error,
    dot: 'bg-red-500',
    icon: icons.AlertTriangle,
  },
  critical: {
    label: '严重',
    badge: 'text-red-700 bg-red-100 border border-red-300 dark:text-red-300 dark:bg-red-950/40 dark:border-red-700',
    dot: 'bg-red-600',
    icon: icons.XCircle,
  },
} as const;

const getScoreBadge = (score: number) => {
  if (score >= 80) return { badge: statusBadge.error, label: '高风险' };
  if (score >= 50) return { badge: statusBadge.warning, label: '中风险' };
  return { badge: statusBadge.success, label: '低风险' };
};

/** 单个风险项（支持折叠缓解建议） */
const RiskItemRow = memo(function RiskItemRow({ item }: { item: RiskItem }) {
  const [expanded, setExpanded] = useState(false);
  const config = LEVEL_CONFIG[item.level];

  const toggle = useCallback(() => setExpanded(prev => !prev), []);

  return (
    <div className="border border-border/50 rounded-lg overflow-hidden">
      {/* 风险项头部 */}
      <div className="px-3 py-2.5">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <span className={cn('w-2 h-2 rounded-full flex-shrink-0', config.dot)} />
            {item.category}
          </span>
          <span className={cn(
            'inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold',
            config.badge,
          )}>
            {config.label}
          </span>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {item.description}
        </p>
      </div>

      {/* 缓解建议（可折叠） */}
      {item.mitigation && (
        <>
          <button
            onClick={toggle}
            className="w-full flex items-center gap-1.5 px-3 py-1.5 border-t border-border/50 bg-muted/30 hover:bg-muted/50 transition-colors text-left"
          >
            <icons.Shield className="w-3 h-3 text-primary" />
            <span className="text-[10px] font-medium text-primary flex-1">
              缓解建议
            </span>
            <icons.ChevronDown
              className={cn(
                'w-3 h-3 text-muted-foreground transition-transform duration-200',
                expanded && 'rotate-180',
              )}
            />
          </button>
          {expanded && (
            <div className="px-3 py-2 border-t border-border/50 bg-primary/5">
              <p className="text-[11px] text-primary/80 leading-relaxed">
                {item.mitigation}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
});

export const RiskMatrixCard = memo(function RiskMatrixCard({
  title,
  risks,
  overallScore,
}: RiskMatrixCardProps) {
  const scoreBadge = getScoreBadge(overallScore);

  return (
    <div className={cn(cardStyle.base, 'overflow-hidden')}>
      {/* 头部：标题 + 综合评分 */}
      <div className="flex items-center justify-between mb-4">
        <h4 className={cn(heading.section, 'flex items-center gap-2')}>
          <icons.Shield className="w-5 h-5 text-primary" />
          {title}
        </h4>
        <div className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold',
          scoreBadge.badge,
        )}>
          <span>{overallScore}分</span>
          <span className="text-[10px] font-normal">({scoreBadge.label})</span>
        </div>
      </div>

      {/* 风险项列表 */}
      <div className="space-y-2">
        {risks.map((item, i) => (
          <RiskItemRow key={i} item={item} />
        ))}
      </div>

      {/* 底部统计 */}
      {risks.length > 0 && (
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border/50">
          {(['critical', 'high', 'medium', 'low'] as const)
            .map(level => {
              const count = risks.filter(r => r.level === level).length;
              if (count === 0) return null;
              return (
                <span key={level} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <span className={cn('w-1.5 h-1.5 rounded-full', LEVEL_CONFIG[level].dot)} />
                  {LEVEL_CONFIG[level].label} {count}
                </span>
              );
            })
            .filter(Boolean)
          }
        </div>
      )}
    </div>
  );
});
