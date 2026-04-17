/**
 * 状态卡片
 * 类似千问的"付款成功"弹窗
 * → 法务场景：委托成功、合同签署完成、风险检测通过等
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import type { StatusCardComponent, A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';
import { A2UICardShell } from'./A2UICardShell';

interface Props {
 component: StatusCardComponent;
 onEvent: A2UIEventHandler;
}

const statusConfig = {
 success: {
 icon: icons.CheckCircle2,
 bg:'bg-success/10',
 iconColor:'text-success',
 border:'border-success/20',
 },
 error: {
 icon: icons.XCircle,
 bg:'bg-destructive/10',
 iconColor:'text-destructive',
 border:'border-destructive/20',
 },
 pending: {
 icon: icons.Clock,
 bg:'bg-warning/10',
 iconColor:'text-warning',
 border:'border-warning/20',
 },
 info: {
 icon: icons.Info,
 bg:'bg-primary/5 dark:bg-primary/10',
 iconColor:'text-primary',
 border:'border-primary/10 dark:border-primary/20',
 },
 warning: {
 icon: icons.AlertTriangle,
 bg:'bg-orange-50 dark:bg-orange-900/20',
 iconColor:'text-orange-500',
 border:'border-orange-100 dark:border-orange-800',
 },
};

export const StatusCard = memo(function StatusCard({ component, onEvent }: Props) {
 const { data } = component;
 const config = statusConfig[data.status];
 const Icon = config.icon;

 return (
 <A2UICardShell
 title={data.title}
 subtitle={data.description}
 className={cn('a2ui-status-card text-center', config.bg, config.border, component.className)}
 bodyClassName="px-6 py-6"
 actions={(data.action || data.secondaryAction) ? (
 <>
 {data.secondaryAction ? (
 <button
 onClick={() => onEvent({
 type:'action',
 actionId: data.secondaryAction!.actionId,
 componentId: component.id,
 })}
 className="rounded-xl px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-surface-2"
 >
 {data.secondaryAction.label}
 </button>
 ) : null}
 {data.action ? (
 <button
 onClick={() => onEvent({
 type:'action',
 actionId: data.action!.actionId,
 componentId: component.id,
 })}
 className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-600"
 >
 {data.action.label}
 </button>
 ) : null}
 </>
 ) : null}
 >
 <div className="mb-3 flex justify-center">
 <div className={cn('w-12 h-12 rounded-full flex items-center justify-center', config.bg)}>
 <Icon className={cn('w-7 h-7', config.iconColor)} />
 </div>
 </div>
 </A2UICardShell>
 );
});
