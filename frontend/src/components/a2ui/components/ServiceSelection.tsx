/**
 * 服务选择组件
 * 展示可选的法律服务类型，如合同审查、法律咨询、委托代理等
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import type { ServiceSelectionComponent, A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

interface Props {
 component: ServiceSelectionComponent;
 onEvent: A2UIEventHandler;
}

export const ServiceSelection = memo(function ServiceSelection({ component, onEvent }: Props) {
 const { data } = component;

 return (
 <div className={cn('a2ui-service-selection', component.className)}>
 {data.title && (
 <h4 className="text-sm font-semibold text-foreground mb-1">{data.title}</h4>
 )}
 {data.subtitle && (
 <p className="text-xs text-muted-foreground mb-3">{data.subtitle}</p>
 )}

 <div className="grid grid-cols-1 gap-3">
 {data.services.map((service) => (
 <button
 key={service.id}
 onClick={() => onEvent({
 type:'action',
 actionId: service.actionId,
 componentId: component.id,
 payload: { serviceId: service.id },
 })}
 className={cn(
'relative text-left p-4 rounded-2xl border-2 transition-all hover:shadow-md active:scale-[0.98]',
 service.popular
 ?'border-primary bg-primary/5 dark:bg-primary/10'
 :'border-border bg-background hover:border-border',
 )}
 >
 {/* 热门标记 */}
 {service.popular && (
 <div className="absolute -top-2.5 left-4 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary text-white text-[10px] font-semibold">
 <icons.Star className="w-2.5 h-2.5 fill-current" />
 推荐
 </div>
 )}

 <div className="flex items-start justify-between">
 <div className="flex-1">
 <h5 className="text-sm font-semibold text-foreground">
 {service.name}
 </h5>
 <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
 {service.description}
 </p>

 {/* 功能列表 */}
 {service.features.length > 0 && (
 <ul className="mt-2 space-y-1">
 {service.features.map((feature, i) => (
 <li key={i} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
 <icons.Check className="w-3 h-3 text-success flex-shrink-0" />
 {feature}
 </li>
 ))}
 </ul>
 )}
 </div>

 {/* 价格 */}
 {service.price && (
 <div className="text-right ml-4 flex-shrink-0">
 <span className="text-lg font-bold text-foreground">
 ¥{service.price.amount}
 </span>
 {service.price.unit && (
 <span className="text-xs text-muted-foreground/70">/{service.price.unit}</span>
 )}
 {service.price.label && (
 <p className="text-[10px] text-muted-foreground/70 mt-0.5">{service.price.label}</p>
 )}
 </div>
 )}
 </div>
 </button>
 ))}
 </div>
 </div>
 );
});
