/**
 * 需求分析卡片 v2 — 参考截图样式
 * 
 * 结构（自上而下）：
 * 1. 头部：「需求分析」标题 + 「需求完整/待补充」状态 + 复杂度标签
 * 2. 需求摘要：大字号深色文本
 * 3. 法律领域标签（带图标）
 * 4. 预期结果（带箭头）
 * 5. 缺失要素提示
 * 6. 建议智能体 pill 列表
 * 7. 完整度进度条
 */

import { memo } from 'react';
import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import type { RequirementAnalysis } from '@/lib/store';

interface RequirementCardProps {
  analysis: RequirementAnalysis;
}

const complexityColors: Record<string, string> = {
  simple: 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800',
  moderate: 'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800',
  complex: 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800',
};

const complexityLabels: Record<string, string> = {
  simple: '简单',
  moderate: '中等',
  complex: '复杂',
};

/** 智能体英文 ID → 中文显示名称 */
const AGENT_DISPLAY_NAMES: Record<string, string> = {
  legal_advisor: '法律顾问',
  contract_reviewer: '合同审查',
  due_diligence: '尽职调查',
  legal_researcher: '法律研究',
  document_drafter: '文书起草',
  compliance_officer: '合规审查',
  risk_assessor: '风险评估',
  litigation_strategist: '诉讼策略',
  ip_specialist: '知识产权',
  regulatory_monitor: '监管监测',
  tax_compliance: '税务合规',
  labor_compliance: '劳动合规',
  labor_law_specialist: '劳动法',
  evidence_analyst: '证据分析',
  evidence_organizer: '证据整理',
  contract_steward: '合同管家',
  consensus_manager: '共识管理',
  requirement_analyst: '需求分析',
};

export const RequirementCard = memo(function RequirementCard({ analysis }: RequirementCardProps) {
  const complColor = complexityColors[analysis.complexity] || complexityColors.simple;
  const complLabel = complexityLabels[analysis.complexity] || '简单';
  const scorePercent = Math.round((analysis.completeness_score || 0) * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-background rounded-xl border border-primary/20 shadow-sm overflow-hidden"
    >
      {/* 头部 — 左侧标题图标 + 右侧状态标签 */}
      <div className="px-4 py-3 bg-primary/10 border-b border-primary/20 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
            <icons.Target className="w-3.5 h-3.5 text-primary" />
          </div>
          <span className="text-sm font-bold text-foreground">需求分析</span>
        </div>
        <div className="flex items-center gap-2">
          {analysis.is_complete ? (
            <span className="flex items-center gap-1 text-xs text-emerald-600 font-semibold">
              <icons.CheckCircle className="w-3.5 h-3.5" />
              需求完整
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-amber-600 font-semibold">
              <icons.AlertCircle className="w-3.5 h-3.5" />
              待补充
            </span>
          )}
          <span className={`text-[11px] px-2.5 py-0.5 rounded-full border font-semibold ${complColor}`}>
            {complLabel}
          </span>
        </div>
      </div>

      {/* 正文区 */}
      <div className="p-4 space-y-3">
        {/* 需求摘要 — 较大字号，深色 */}
        <p className="text-[15px] font-medium text-foreground leading-relaxed">
          {analysis.summary}
        </p>

        {/* 法律领域标签 + 预期结果 */}
        {analysis.elements && (
          <div className="space-y-2">
            {analysis.elements.legal_area && (
              <div className="flex items-center gap-2">
                <icons.Tag className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                <span className="text-sm text-primary">{analysis.elements.legal_area}</span>
              </div>
            )}
            {analysis.elements.expected_outcome && (
              <div className="flex items-center gap-2">
                <icons.ArrowRight className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                <span className="text-sm text-primary">{analysis.elements.expected_outcome}</span>
              </div>
            )}
          </div>
        )}

        {/* 缺失要素 */}
        {analysis.missing_elements && analysis.missing_elements.length > 0 && (
          <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
            <p className="text-xs font-semibold text-amber-700 mb-1.5">待补充信息：</p>
            <ul className="space-y-1">
              {analysis.missing_elements.map((item, i) => (
                <li key={i} className="text-xs text-amber-600 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 分隔线 */}
        <div className="border-t border-border" />

        {/* 建议智能体 */}
        {analysis.suggested_agents && analysis.suggested_agents.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground flex-shrink-0">建议智能体：</span>
            {analysis.suggested_agents.map((a, i) => (
              <span key={i} className="px-2.5 py-1 bg-primary/10 border border-primary/30 rounded-lg text-xs text-primary font-medium">
                {AGENT_DISPLAY_NAMES[a] || a}
              </span>
            ))}
          </div>
        )}

        {/* 完整度进度条 */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-muted-foreground">完整度</span>
            <span className={`font-semibold ${
              scorePercent >= 70 ? 'text-emerald-600' : 'text-amber-600'
            }`}>{scorePercent}%</span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <motion.div
              className={`h-2 rounded-full ${
                scorePercent >= 70
                  ? 'bg-gradient-to-r from-green-400 to-green-500'
                  : 'bg-gradient-to-r from-amber-400 to-amber-500'
              }`}
              initial={{ width: 0 }}
              animate={{ width: `${scorePercent}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
});
