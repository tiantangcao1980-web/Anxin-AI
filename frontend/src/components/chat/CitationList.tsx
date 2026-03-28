/**
 * CitationList - RAG 引用来源列表
 *
 * 可折叠的引用列表组件，显示"引用来源 (N)"标题，
 * 点击可展开/收起所有 CitationCard。
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { heading, iconSize } from '@/lib/design-tokens';
import { CitationCard, type CitationSourceData } from './CitationCard';

interface CitationListProps {
  sources: CitationSourceData[];
  /** 默认是否展开，默认 false */
  defaultExpanded?: boolean;
}

export function CitationList({ sources, defaultExpanded = false }: CitationListProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-2">
      {/* 折叠标题 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 py-1 px-0.5 text-left hover:opacity-80 transition-opacity"
      >
        <icons.BookOpen className={`${iconSize.sm} text-primary`} />
        <span className={`${heading.card} text-primary`}>
          引用来源 ({sources.length})
        </span>
        <icons.ChevronDown
          className={`${iconSize.sm} text-muted-foreground transition-transform ${
            expanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* 引用卡片列表 */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="flex flex-col gap-2 mt-1.5">
              {sources.map((source) => (
                <CitationCard key={source.id} citation={source} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
