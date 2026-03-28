/**
 * 文本块组件
 * AI 生成的 Markdown 富文本内容
 */

import { memo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { icons } from '@/lib/icons';
import type { TextBlockComponent, A2UIEventHandler } from '../types';
import { cn } from '@/lib/utils';

interface Props {
  component: TextBlockComponent;
  onEvent: A2UIEventHandler;
}

export const TextBlock = memo(function TextBlock({ component, onEvent }: Props) {
  const { data } = component;
  const [expanded, setExpanded] = useState(!data.collapsible);

  const previewContent = data.collapsible && !expanded && data.previewLines
    ? data.content.split('\n').slice(0, data.previewLines).join('\n')
    : data.content;

  return (
    <div className={cn('a2ui-text-block', component.className)}>
      <div className={cn(
        'prose prose-sm dark:prose-invert max-w-none',
        'prose-headings:text-foreground',
        'prose-p:text-muted-foreground',
        'prose-a:text-primary dark:prose-a:text-primary',
        !expanded && data.collapsible && 'line-clamp-3',
      )}>
        {data.format === 'plain' ? (
          <p className="whitespace-pre-wrap text-sm text-muted-foreground leading-relaxed">
            {previewContent}
          </p>
        ) : (
          <ReactMarkdown>{previewContent}</ReactMarkdown>
        )}
      </div>

      {data.collapsible && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 mt-2 text-xs text-primary dark:text-primary hover:text-primary/80 transition"
        >
          {expanded ? (
            <>收起 <icons.ChevronUp className="w-3.5 h-3.5" /></>
          ) : (
            <>展开全部 <icons.ChevronDown className="w-3.5 h-3.5" /></>
          )}
        </button>
      )}
    </div>
  );
});
