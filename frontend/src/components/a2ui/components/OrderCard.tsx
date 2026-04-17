/**
 * 订单/委托确认卡片
 * 类似千问的订单确认卡片：商品信息 + 配送详情 + 费用明细 + 操作按钮
 * → 法务场景：委托确认、服务订单确认
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import type { OrderCardComponent, A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

interface Props {
 component: OrderCardComponent;
 onEvent: A2UIEventHandler;
}

export const OrderCard = memo(function OrderCard({ component, onEvent }: Props) {
 const { data } = component;

 const handleAction = (actionId: string, payload?: Record<string, any>) => {
 onEvent({
 type:'action',
 actionId,
 componentId: component.id,
 payload,
 });
 };

 return (
 <div className={cn(
'a2ui-order-card',
'bg-background rounded-2xl border border-border/50',
'shadow-sm overflow-hidden',
 component.className,
 )}>
 {/* 标题 */}
 {data.title && (
 <div className="px-4 pt-4 pb-2">
 <h4 className="text-sm font-semibold text-foreground">{data.title}</h4>
 </div>
 )}

 {/* 商品/服务信息 */}
 <div className="flex gap-3 px-4 py-3">
 {data.item.image && (
 <div className="w-16 h-16 rounded-xl overflow-hidden bg-muted flex-shrink-0">
 <img src={data.item.image} alt="" className="w-full h-full object-cover" />
 </div>
 )}
 <div className="flex-1 min-w-0">
 <h5 className="font-semibold text-sm text-foreground line-clamp-1">
 {data.item.title}
 </h5>
 {data.item.subtitle && (
 <p className="text-xs text-muted-foreground mt-0.5">{data.item.subtitle}</p>
 )}
 {data.item.specs && (
 <p className="text-xs text-muted-foreground/70 mt-1 flex items-center gap-1">
 {data.item.specs}
 <icons.Edit3 className="w-3 h-3 text-primary" />
 </p>
 )}
 </div>
 <div className="text-right flex-shrink-0">
 {data.item.price && (
 <span className="text-sm font-bold text-foreground">
 ¥{data.item.price.amount}
 </span>
 )}
 {data.item.quantity && (
 <p className="text-xs text-muted-foreground/70 mt-0.5">x{data.item.quantity}</p>
 )}
 </div>
 </div>

 {/* 详情列表 */}
 {data.details.length > 0 && (
 <div className="mx-4 border-t border-border/50">
 {data.details.map((detail, i) => (
 <div key={i} className="flex items-start justify-between py-2.5 border-b border-border/30 last:border-0">
 <span className="text-xs text-muted-foreground flex-shrink-0 w-16">{detail.label}</span>
 <div className="flex items-center gap-1 flex-1 justify-end">
 <span className="text-xs text-foreground text-right">
 {detail.value}
 </span>
 {detail.editable && (
 <button
 onClick={() => detail.editActionId && handleAction(detail.editActionId)}
 className="text-primary hover:text-primary/80"
 >
 <icons.ChevronRight className="w-3.5 h-3.5" />
 </button>
 )}
 </div>
 </div>
 ))}
 </div>
 )}

 {/* 费用明细 */}
 {data.pricing && (
 <div className="mx-4 pt-2 pb-3 border-t border-border/50">
 {data.pricing.items.map((item, i) => (
 <div key={i} className="flex items-center justify-between py-1">
 <span className="text-xs text-muted-foreground">{item.label}</span>
 <div className="flex items-baseline gap-1">
 {item.original && (
 <span className="text-xs text-muted-foreground/70 line-through">¥{item.original}</span>
 )}
 <span className={cn(
'text-xs font-medium',
 item.type ==='subtract' ?'text-success' :'text-foreground',
 )}>
 {item.type ==='subtract' ?'-' :''}¥{Math.abs(item.amount)}
 </span>
 </div>
 </div>
 ))}
 <div className="flex items-center justify-between pt-2 mt-1 border-t border-dashed border-border">
 <span className="text-sm font-medium text-foreground">
 {data.pricing.total.label}
 </span>
 <span className="text-lg font-bold text-foreground">
 ¥{data.pricing.total.amount}
 </span>
 </div>
 </div>
 )}

 {/* 备注 */}
 {data.note && (
 <p className="mx-4 mb-2 text-[10px] text-muted-foreground/70 leading-relaxed">{data.note}</p>
 )}

 {/* 操作按钮 */}
 {data.actions.length > 0 && (
 <div className={cn(
'flex gap-2 p-4 border-t border-border/50',
 data.actions.some((a) => a.fullWidth) ?'flex-col' :'flex-row',
 )}>
 {data.actions.map((action) => (
 <button
 key={action.actionId}
 onClick={() => handleAction(action.actionId, action.payload)}
 className={cn(
'flex-1 py-2.5 rounded-xl text-sm font-semibold transition-[colors,transform] active:scale-[0.98]',
 action.variant ==='primary' &&'bg-primary text-primary-foreground hover:bg-primary/90',
 action.variant ==='secondary' &&'bg-muted text-foreground hover:bg-accent',
 action.variant ==='outline' &&'border border-border text-foreground hover:bg-muted/50',
 action.variant ==='warning' &&'bg-warning text-warning-foreground hover:bg-warning/20',
 !action.variant &&'bg-muted text-foreground hover:bg-accent',
 action.fullWidth &&'w-full',
 )}
 >
 {action.label}
 </button>
 ))}
 </div>
 )}
 </div>
 );
});
