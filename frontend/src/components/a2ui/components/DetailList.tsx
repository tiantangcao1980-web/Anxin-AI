/**
 * 详情列表组件
 * Key-Value 格式展示信息
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import type { DetailListComponent, A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

interface Props {
 component: DetailListComponent;
 onEvent: A2UIEventHandler;
}

export const DetailList = memo(function DetailList({ component, onEvent }: Props) {
 const { data } = component;

 return (
 <div className={cn(
'a2ui-detail-list bg-background rounded-2xl border border-border/50',
 component.className,
 )}>
 {data.title && (
 <div className="px-4 pt-4 pb-2">
 <h4 className="text-sm font-semibold text-foreground">{data.title}</h4>
 </div>
 )}
 <div className="px-4 pb-2">
 {data.items.map((item, i) => (
 <div
 key={i}
 className={cn(
'flex items-start justify-between py-3',
 data.divider !== false && i < data.items.length - 1 &&'border-b border-border/50',
 )}
 >
 <span className="text-xs text-muted-foreground flex-shrink-0">
 {item.label}
 </span>
 <div className="flex items-center gap-1 ml-4">
 {item.valueType ==='badge' ? (
 <span className={cn(
'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium',
 item.color ==='green' &&'bg-success/10 text-success',
 item.color ==='red' &&'bg-destructive/10 text-destructive',
 item.color ==='orange' &&'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
 !item.color &&'bg-muted text-muted-foreground',
 )}>
 {item.value}
 </span>
 ) : item.valueType ==='link' ? (
 <a href={item.href} className="text-xs text-primary dark:text-primary hover:underline">
 {item.value}
 </a>
 ) : item.valueType ==='highlight' ? (
 <span className="text-xs font-semibold text-foreground">
 {item.value}
 </span>
 ) : (
 <span className="text-xs text-foreground text-right">
 {item.value}
 </span>
 )}
 {item.editable && (
 <button
 onClick={() => item.editActionId && onEvent({
 type:'action',
 actionId: item.editActionId,
 componentId: component.id,
 payload: { field: item.label },
 })}
 className="text-primary"
 >
 <icons.ChevronRight className="w-3.5 h-3.5" />
 </button>
 )}
 </div>
 </div>
 ))}
 </div>
 </div>
 );
});
