/**
 * 状态卡片
 * 类似千问的"付款成功"弹窗
 * → 法务场景：委托成功、合同签署完成、风险检测通过等
 */

import { memo } from 'react';
import { icons } from '@/lib/icons';
import type { StatusCardComponent, A2UIEventHandler } from '../types';
import { cn } from '@/lib/utils';

interface Props {
  component: StatusCardComponent;
  onEvent: A2UIEventHandler;
}

const statusConfig = {
  success: {
    icon: icons.CheckCircle2,
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    iconColor: 'text-emerald-600',
    border: 'border-emerald-100 dark:border-emerald-800',
  },
  error: {
    icon: icons.XCircle,
    bg: 'bg-red-50 dark:bg-red-900/20',
    iconColor: 'text-red-500',
    border: 'border-red-100 dark:border-red-800',
  },
  pending: {
    icon: icons.Clock,
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    iconColor: 'text-amber-500',
    border: 'border-amber-100 dark:border-amber-800',
  },
  info: {
    icon: icons.Info,
    bg: 'bg-primary/5 dark:bg-primary/10',
    iconColor: 'text-primary',
    border: 'border-primary/10 dark:border-primary/20',
  },
  warning: {
    icon: icons.AlertTriangle,
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    iconColor: 'text-orange-500',
    border: 'border-orange-100 dark:border-orange-800',
  },
};

export const StatusCard = memo(function StatusCard({ component, onEvent }: Props) {
  const { data } = component;
  const config = statusConfig[data.status];
  const Icon = config.icon;

  return (
    <div className={cn(
      'a2ui-status-card rounded-2xl border p-6 text-center',
      config.bg, config.border,
      component.className,
    )}>
      <div className="flex justify-center mb-3">
        <div className={cn('w-12 h-12 rounded-full flex items-center justify-center', config.bg)}>
          <Icon className={cn('w-7 h-7', config.iconColor)} />
        </div>
      </div>

      <h4 className="text-base font-semibold text-foreground">
        {data.title}
      </h4>

      {data.description && (
        <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
          {data.description}
        </p>
      )}

      {/* 操作按钮 */}
      {(data.action || data.secondaryAction) && (
        <div className="flex items-center justify-center gap-3 mt-4">
          {data.secondaryAction && (
            <button
              onClick={() => onEvent({
                type: 'action',
                actionId: data.secondaryAction!.actionId,
                componentId: component.id,
              })}
              className="px-5 py-2 rounded-full text-sm font-medium text-muted-foreground hover:bg-muted transition"
            >
              {data.secondaryAction.label}
            </button>
          )}
          {data.action && (
            <button
              onClick={() => onEvent({
                type: 'action',
                actionId: data.action!.actionId,
                componentId: component.id,
              })}
              className="px-6 py-2 rounded-full text-sm font-semibold bg-primary text-white hover:bg-primary/90 transition active:scale-95"
            >
              {data.action.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
});
