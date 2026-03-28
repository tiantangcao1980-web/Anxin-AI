/**
 * 流式消息渲染组件 — v3 豆包风格
 * 
 * Token-by-token 流式渲染 + Markdown 支持 + 闪烁光标
 * 匹配新版消息气泡样式（无大头像、紧凑布局）
 */

import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import { icons } from '@/lib/icons';
import { cardStyle, heading, buttonStyle, iconSize, chatBubble, proseStyle } from '@/lib/design-tokens';

interface StreamingMessageProps {
  content: string;
  agent: string;
  isStreaming: boolean;
}

export const StreamingMessage = memo(function StreamingMessage({
  content,
  agent,
  isStreaming,
}: StreamingMessageProps) {
  return (
    <div className="group">
      <div className="max-w-[85%]">
        {/* Agent 标签 */}
        {agent && (
          <div className={`flex items-center gap-1.5 ${heading.micro} font-medium mb-1.5 ml-0.5`}>
            <icons.Bot className={iconSize.xs} />
            {agent}
            {isStreaming && (
              <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-primary/5 text-primary rounded-full font-medium animate-pulse">
                生成中
              </span>
            )}
          </div>
        )}
        
        {/* 消息气泡 */}
        <div className={`${chatBubble.ai} shadow-sm leading-relaxed text-sm`}>
          <div className={proseStyle.chat}>
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
          {isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-primary animate-pulse ml-0.5 align-text-bottom rounded-full" />
          )}
        </div>
      </div>
    </div>
  );
});
