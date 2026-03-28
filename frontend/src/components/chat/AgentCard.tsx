/**
 * Agent 中间结果卡片组件
 * 
 * 展示单个 Agent 完成的工作结果，带时间线连接
 */

import { useState, memo } from 'react';
import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { cardStyle, heading, iconSize, shadow, radius } from '@/lib/design-tokens';
import ReactMarkdown from 'react-markdown';
import type { AgentResult } from '@/lib/store';

const agentIcons: Record<string, { icon: React.ElementType; color: string }> = {
  '法律顾问Agent': { icon: icons.Scale, color: 'bg-primary/5 text-primary' },
  '合同审查Agent': { icon: icons.FileSearch, color: 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400' },
  '尽职调查Agent': { icon: icons.Search, color: 'bg-cyan-50 text-cyan-600' },
  '法律研究Agent': { icon: icons.BookOpen, color: 'bg-primary/5 text-primary' },
  '文书起草Agent': { icon: icons.FileText, color: 'bg-violet-50 dark:bg-violet-950/30 text-violet-600 dark:text-violet-400' },
  '合规审查Agent': { icon: icons.Shield, color: 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400' },
  '风险评估Agent': { icon: icons.AlertTriangle, color: 'bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400' },
  '诉讼策略Agent': { icon: icons.Gavel, color: 'bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400' },
  '知识产权Agent': { icon: icons.Landmark, color: 'bg-pink-50 text-pink-600' },
  '监管监测Agent': { icon: icons.Eye, color: 'bg-orange-50 text-orange-600' },
  '税务合规Agent': { icon: icons.Building, color: 'bg-teal-50 text-teal-600' },
  '劳动合规Agent': { icon: icons.Briefcase, color: 'bg-sky-50 text-sky-600' },
  '协调调度Agent': { icon: icons.Brain, color: 'bg-primary/5 text-primary' },
};

interface AgentCardProps {
  result: AgentResult;
  index: number;
  isLast: boolean;
}

export const AgentCard = memo(function AgentCard({ result, index, isLast }: AgentCardProps) {
  const [expanded, setExpanded] = useState(false);
  const iconConfig = agentIcons[result.agent] || { icon: icons.Brain, color: 'bg-muted text-muted-foreground' };
  const Icon = iconConfig.icon;

  const preview = result.content.slice(0, 150);
  const hasMore = result.content.length > 150;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08 }}
      className="flex gap-3"
    >
      {/* 时间线 */}
      <div className="flex flex-col items-center flex-shrink-0">
        <div className={`${iconSize.xl} rounded-full ${iconConfig.color} flex items-center justify-center`}>
          <Icon className={iconSize.sm} />
        </div>
        {!isLast && <div className="w-px flex-1 bg-border mt-1" />}
      </div>

      {/* 内容 */}
      <div className="flex-1 min-w-0 pb-4">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className={heading.card}>{result.agent}</span>
            <icons.CheckCircle className={`${iconSize.sm} text-emerald-600 dark:text-emerald-400`} />
          </div>
          {result.elapsed !== undefined && (
            <div className={`flex items-center gap-1 ${heading.micro}`}>
              <icons.Clock className={iconSize.xs} />
              {result.elapsed}s
            </div>
          )}
        </div>

        <div className={`${cardStyle.compact}`}>
          <div className="prose prose-xs max-w-none text-muted-foreground leading-relaxed">
            <ReactMarkdown>{expanded ? result.content : preview + (hasMore ? '...' : '')}</ReactMarkdown>
          </div>

          {hasMore && (
            <button
              onClick={() => setExpanded(!expanded)}
              className={`flex items-center gap-1 ${heading.micro} text-primary hover:text-primary/80 mt-2 font-medium`}
            >
              {expanded ? (
                <>
                  <icons.ChevronUp className={iconSize.xs} />
                  收起
                </>
              ) : (
                <>
                  <icons.ChevronDown className={iconSize.xs} />
                  展开完整结果
                </>
              )}
            </button>
          )}
        </div>

        <div className={`flex items-center gap-2 mt-1.5 ${heading.micro}`}>
          <span>步骤 {result.step}/{result.totalSteps}</span>
        </div>
      </div>
    </motion.div>
  );
});
