/**
 * ThinkingIndicator — 内联 Agent 状态指示器
 * 
 * 在消息流中紧凑展示 Agent 工作状态，不打开右侧面板。
 * - 单 Agent：显示名称 + 动画脉冲
 * - 多 Agent：显示步骤进度 (1/3 完成)
 */

import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { iconSize, cardStyle, radius, heading } from '@/lib/design-tokens';

export interface ThinkingStatus {
  agent: string;
  message: string;
  step?: number;
  totalSteps?: number;
}

interface ThinkingIndicatorProps {
  status: ThinkingStatus | null;
}

export function ThinkingIndicator({ status }: ThinkingIndicatorProps) {
  if (!status) return null;

  const hasProgress = status.step != null && status.totalSteps != null && status.totalSteps > 1;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className={`flex items-center gap-2 px-3 py-2 ${radius.card} bg-primary/5 border border-primary/10 max-w-fit`}
    >
      {/* 脉冲动画圆点 */}
      <div className="relative flex-shrink-0">
        <icons.Bot className={`${iconSize.sm} text-primary`} />
        <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary/40 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
        </span>
      </div>

      {/* Agent 名称和消息 */}
      <div className="flex items-center gap-1.5 min-w-0">
        <span className={`${heading.micro} font-semibold text-primary truncate`}>
          {status.agent}
        </span>
        <span className={`${heading.micro} text-primary/70 truncate`}>
          {status.message}
        </span>
      </div>

      {/* 进度指示 */}
      {hasProgress && (
        <span className={`flex-shrink-0 text-[10px] font-medium text-primary/60 bg-primary/10 px-1.5 py-0.5 ${radius.badge}`}>
          {status.step}/{status.totalSteps}
        </span>
      )}

      {/* 旋转加载器 */}
      <icons.Loader2 className={`${iconSize.xs} animate-spin text-primary/60 flex-shrink-0`} />
    </motion.div>
  );
}
