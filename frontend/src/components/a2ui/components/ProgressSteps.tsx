/**
 * 步骤进度组件
 * 用于展示工作流进度
 */

import { memo } from 'react';
import { icons } from '@/lib/icons';
import type { ProgressStepsComponent, A2UIEventHandler } from '../types';
import { cn } from '@/lib/utils';

interface Props {
  component: ProgressStepsComponent;
  onEvent: A2UIEventHandler;
}

const stepStatusConfig = {
  pending: { icon: icons.Circle, color: 'text-muted-foreground/70', bg: 'bg-muted', line: 'bg-border' },
  active: { icon: icons.Circle, color: 'text-primary', bg: 'bg-primary/10 dark:bg-primary/20', line: 'bg-primary/20 dark:bg-primary/30' },
  completed: { icon: icons.Check, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/30', line: 'bg-emerald-500 dark:bg-emerald-600' },
  error: { icon: icons.AlertCircle, color: 'text-red-500', bg: 'bg-red-100 dark:bg-red-900/30', line: 'bg-red-200 dark:bg-red-800' },
  skipped: { icon: icons.SkipForward, color: 'text-muted-foreground/70', bg: 'bg-muted', line: 'bg-border' },
};

export const ProgressSteps = memo(function ProgressSteps({ component, onEvent }: Props) {
  const { data } = component;
  const isVertical = data.direction === 'vertical';

  return (
    <div className={cn(
      'a2ui-progress-steps bg-background rounded-2xl border border-border/50 p-4',
      component.className,
    )}>
      {data.title && (
        <h4 className="text-sm font-semibold text-foreground mb-4">{data.title}</h4>
      )}

      <div className={cn(
        isVertical ? 'flex flex-col' : 'flex items-start',
      )}>
        {data.steps.map((step, i) => {
          const config = stepStatusConfig[step.status];
          const Icon = config.icon;
          const isLast = i === data.steps.length - 1;

          if (isVertical) {
            return (
              <div key={step.id} className="flex gap-3">
                {/* 图标 + 连接线 */}
                <div className="flex flex-col items-center">
                  <div className={cn('w-7 h-7 rounded-full flex items-center justify-center', config.bg)}>
                    <Icon className={cn('w-4 h-4', config.color)} />
                  </div>
                  {!isLast && (
                    <div className={cn('w-0.5 flex-1 min-h-[24px] my-1', config.line)} />
                  )}
                </div>
                {/* 内容 */}
                <div className="pb-4">
                  <p className={cn(
                    'text-sm font-medium',
                    step.status === 'active' ? 'text-primary dark:text-primary' : 'text-foreground',
                  )}>
                    {step.label}
                  </p>
                  {step.description && (
                    <p className="text-xs text-muted-foreground/70 mt-0.5">{step.description}</p>
                  )}
                  {step.timestamp && (
                    <p className="text-[10px] text-muted-foreground/70 mt-0.5">{step.timestamp}</p>
                  )}
                </div>
              </div>
            );
          }

          // 水平方向
          return (
            <div key={step.id} className="flex-1 flex flex-col items-center">
              <div className="flex items-center w-full">
                {i > 0 && <div className={cn('flex-1 h-0.5', stepStatusConfig[data.steps[i - 1].status].line)} />}
                <div className={cn('w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0', config.bg)}>
                  <Icon className={cn('w-4 h-4', config.color)} />
                </div>
                {!isLast && <div className={cn('flex-1 h-0.5', config.line)} />}
              </div>
              <p className={cn(
                'text-[11px] mt-2 text-center',
                step.status === 'active' ? 'text-primary font-medium dark:text-primary' : 'text-muted-foreground',
              )}>
                {step.label}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
});
