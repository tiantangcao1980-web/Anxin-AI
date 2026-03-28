/**
 * AI 行内建议组件
 * 
 * 在 Canvas 编辑器中显示 AI 的修改建议，支持接受/拒绝
 */

import { memo } from 'react';
import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import type { CanvasSuggestion } from '@/lib/store';

interface InlineSuggestionProps {
  suggestion: CanvasSuggestion;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
}

export const InlineSuggestion = memo(function InlineSuggestion({
  suggestion,
  onAccept,
  onReject,
}: InlineSuggestionProps) {
  if (suggestion.status !== 'pending') return null;

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      className="border-l-2 border-amber-400 bg-amber-50/50 rounded-r-lg p-3 my-1"
    >
      {/* 原文 */}
      <div className="text-xs">
        <span className="text-muted-foreground font-medium">原文：</span>
        <span className="text-red-600 line-through ml-1">{suggestion.original}</span>
      </div>

      {/* 建议 */}
      <div className="text-xs mt-1">
        <span className="text-muted-foreground font-medium">建议：</span>
        <span className="text-emerald-600 font-medium ml-1">{suggestion.suggested}</span>
      </div>

      {/* 理由 */}
      {suggestion.reason && (
        <div className="flex items-start gap-1 mt-1.5 text-[10px] text-muted-foreground">
          <icons.MessageSquare className="w-3 h-3 mt-0.5 flex-shrink-0" />
          <span>{suggestion.reason}</span>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex items-center gap-1.5 mt-2">
        <button
          onClick={() => onAccept(suggestion.id)}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 rounded hover:bg-emerald-100 dark:hover:bg-emerald-950/50 transition-colors"
        >
          <icons.Check className="w-3 h-3" />
          接受
        </button>
        <button
          onClick={() => onReject(suggestion.id)}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-muted-foreground bg-muted rounded hover:bg-muted/80 transition-colors"
        >
          <icons.X className="w-3 h-3" />
          忽略
        </button>
      </div>
    </motion.div>
  );
});
