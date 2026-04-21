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
import type { CitationSource } from './types';

/**
 * CitationCard 接受的引用数据。
 * 直接复用全站唯一 CitationSource 定义，避免类型漂移。
 */
export type CitationSourceData = CitationSource;

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

/** 根据相关度返回徽章样式；未知分值归为「参考」 */
function getRelevanceBadge(score?: number): { label: string; className: string } {
  const s = typeof score === 'number' ? score : 0;
  if (s >= 0.8) return { label: '高度相关', className: statusBadge.success };
  if (s >= 0.5) return { label: '相关', className: statusBadge.info };
  return { label: '参考', className: statusBadge.neutral };
}

export function CitationCard({ citation }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  const TypeIcon = getTypeIcon(citation.type);
  const typeLabel = getTypeLabel(citation.type);
  const badge = getRelevanceBadge(citation.relevance_score);
  const snippet = citation.content_snippet ?? '';
  const sourceText = citation.source ?? '';

  return (
    <button
      type="button"
      className={`${cardStyle.compact} text-left w-full cursor-pointer rounded-dd_lg shadow-elev-1 hover:shadow-elev-2 hover:border-ai-citation/30 transition-[border-color,box-shadow,transform] duration-fast ease-standard active:scale-[0.99]`}
      onClick={() => setExpanded(!expanded)}
      aria-expanded={expanded}
    >
      <div className="flex items-start gap-2.5">
        {/* 类型图标 */}
        <div className="flex-shrink-0 p-1.5 rounded-dd bg-ai-citation-surface">
          <TypeIcon className={`${iconSize.sm} text-ai-citation`} />
        </div>

        {/* 内容区域 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`${heading.micro} font-medium text-ai-citation`}>{typeLabel}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-pill ${badge.className}`}>
              {badge.label}
            </span>
          </div>
          <p className={`${heading.card} truncate`}>{citation.title}</p>
          <p className={`${heading.micro} mt-0.5 truncate`}>{sourceText}</p>
        </div>

        {/* 展开/收起箭头 */}
        <icons.ChevronDown
          className={`${iconSize.sm} text-muted-foreground flex-shrink-0 transition-transform duration-fast ease-standard ${
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
            <div className="mt-2.5 pt-2.5 border-t border-border-subtle">
              <p className="text-xs text-foreground/80 leading-relaxed font-serif">
                {snippet}
              </p>
              {citation.url && (
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-2 text-xs text-ai-citation hover:underline"
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
    </button>
  );
}
