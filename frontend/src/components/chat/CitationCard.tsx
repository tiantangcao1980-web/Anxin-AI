/**
 * CitationCard - RAG 引用来源卡片
 *
 * 紧凑卡片，展示引用来源的类型图标、标题、来源文本和相关度徽章。
 * 点击可展开显示内容片段 (content_snippet)。
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { cardStyle, heading, statusBadge, iconSize } from '@/lib/design-tokens';

export interface CitationSourceData {
  id: string;
  type: string; // "law_article" | "case" | "knowledge" | "regulation"
  title: string;
  content_snippet: string;
  source: string;
  relevance_score: number;
  url?: string | null;
}

interface CitationCardProps {
  citation: CitationSourceData;
}

/** 根据引用类型返回对应图标 */
function getTypeIcon(type: string) {
  switch (type) {
    case 'law_article':
      return icons.Scale;
    case 'case':
      return icons.Briefcase;
    case 'regulation':
      return icons.ShieldCheck;
    case 'knowledge':
    default:
      return icons.BookOpen;
  }
}

/** 根据引用类型返回中文标签 */
function getTypeLabel(type: string): string {
  switch (type) {
    case 'law_article':
      return '法条';
    case 'case':
      return '案例';
    case 'regulation':
      return '法规';
    case 'knowledge':
      return '知识库';
    default:
      return '参考';
  }
}

/** 根据相关度返回徽章样式 */
function getRelevanceBadge(score: number): { label: string; className: string } {
  if (score >= 0.8) return { label: '高度相关', className: statusBadge.success };
  if (score >= 0.5) return { label: '相关', className: statusBadge.info };
  return { label: '参考', className: statusBadge.neutral };
}

export function CitationCard({ citation }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  const TypeIcon = getTypeIcon(citation.type);
  const typeLabel = getTypeLabel(citation.type);
  const badge = getRelevanceBadge(citation.relevance_score);

  return (
    <div
      className={`${cardStyle.compact} cursor-pointer hover:border-primary/20 hover:shadow-sm transition-all`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-2.5">
        {/* 类型图标 */}
        <div className="flex-shrink-0 p-1.5 rounded-lg bg-primary/5">
          <TypeIcon className={`${iconSize.sm} text-primary`} />
        </div>

        {/* 内容区域 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`${heading.micro} font-medium text-primary`}>{typeLabel}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-md ${badge.className}`}>
              {badge.label}
            </span>
          </div>
          <p className={`${heading.card} truncate`}>{citation.title}</p>
          <p className={`${heading.micro} mt-0.5 truncate`}>{citation.source}</p>
        </div>

        {/* 展开/收起箭头 */}
        <icons.ChevronDown
          className={`${iconSize.sm} text-muted-foreground flex-shrink-0 transition-transform ${
            expanded ? 'rotate-180' : ''
          }`}
        />
      </div>

      {/* 展开区域 */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2.5 pt-2.5 border-t border-border">
              <p className="text-xs text-foreground/80 leading-relaxed">
                {citation.content_snippet}
              </p>
              {citation.url && (
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-2 text-xs text-primary hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  <icons.ExternalLink className={iconSize.xs} />
                  查看原文
                </a>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
